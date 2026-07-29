from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import time
from typing import Any, Callable, Mapping

from .graph import GraphDefinition
from .recorder import ExecutionRecorder


@dataclass(frozen=True)
class NodeResult:
    success: bool = True
    signal: str = "success"
    output: Any = None
    error: str | None = None

    @classmethod
    def failure(cls, error: str, signal: str = "error") -> "NodeResult":
        return cls(success=False, signal=signal, error=error)


@dataclass
class ExecutionContext:
    run_id: str
    graph_id: str
    inputs: dict[str, Any] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)
    next_node: str | None = None
    current_node: str | None = None
    status: str = "running"
    error: str | None = None
    steps: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExecutionContext":
        return cls(
            run_id=str(value["run_id"]),
            graph_id=str(value["graph_id"]),
            inputs=dict(value.get("inputs", {})),
            data=dict(value.get("data", {})),
            next_node=value.get("next_node"),
            current_node=value.get("current_node"),
            status=str(value.get("status", "running")),
            error=value.get("error"),
            steps=int(value.get("steps", 0)),
        )


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 1
    backoff_seconds: float = 0.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.backoff_seconds < 0:
            raise ValueError("backoff_seconds cannot be negative")


NodeHandler = Callable[[dict[str, Any], ExecutionContext], NodeResult | dict[str, Any] | Any]


class GraphExecutionError(ValueError):
    pass


class GraphScheduler:
    """Execute a validated graph with retry, fallback, and checkpoints."""

    def __init__(
        self,
        graph: GraphDefinition,
        handlers: Mapping[str, NodeHandler] | None = None,
        *,
        recorder: ExecutionRecorder | None = None,
        retry_policy: RetryPolicy | None = None,
        checkpoint_path: str | Path | None = None,
        max_steps: int = 100,
    ):
        graph.assert_valid()
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1")
        self.graph = graph
        self.handlers = dict(handlers or {})
        self.recorder = recorder or ExecutionRecorder(graph_id=graph.graph_id)
        self.retry_policy = retry_policy or RetryPolicy()
        self.checkpoint_path = Path(checkpoint_path) if checkpoint_path else None
        self.max_steps = max_steps
        self._nodes = {str(node["id"]): node for node in graph.nodes}

    def run(
        self,
        inputs: Mapping[str, Any] | None = None,
        *,
        checkpoint: str | Path | Mapping[str, Any] | None = None,
    ) -> ExecutionContext:
        context = self._load_context(inputs, checkpoint)
        self.recorder.bind(context.run_id, self.graph.graph_id)
        self.recorder.emit(
            "run_resumed" if checkpoint is not None else "run_started",
            status=context.status,
            data={"next_node": context.next_node},
        )

        while context.next_node is not None:
            if context.steps >= self.max_steps:
                return self._finish(context, "failed", "maximum graph steps exceeded")
            node_id = context.next_node
            node = self._nodes[node_id]
            context.current_node = node_id
            result = self._execute_node(node, context)
            if not result.success:
                fallback = self._choose_next(node_id, "error")
                if fallback is None:
                    return self._finish(context, "failed", result.error or "node failed")
                context.data.setdefault("errors", {})[node_id] = result.error or "node failed"
                context.next_node = fallback
                self._save_checkpoint(context)
                continue

            context.steps += 1
            context.data[node_id] = result.output
            context.next_node = self._choose_next(node_id, result.signal)
            self._save_checkpoint(context)

        return self._finish(context, "completed", None)

    def _load_context(
        self,
        inputs: Mapping[str, Any] | None,
        checkpoint: str | Path | Mapping[str, Any] | None,
    ) -> ExecutionContext:
        if checkpoint is None:
            return ExecutionContext(
                run_id=self.recorder.run_id,
                graph_id=self.graph.graph_id,
                inputs=dict(inputs or {}),
                next_node=self.graph.start,
            )
        if isinstance(checkpoint, Mapping):
            payload = checkpoint
        else:
            payload = json.loads(Path(checkpoint).read_text(encoding="utf-8"))
        context = ExecutionContext.from_dict(payload)
        if context.graph_id != self.graph.graph_id:
            raise GraphExecutionError("checkpoint belongs to a different graph")
        if context.status in {"completed", "failed"}:
            raise GraphExecutionError(f"cannot resume a {context.status} checkpoint")
        return context

    def _execute_node(self, node: dict[str, Any], context: ExecutionContext) -> NodeResult:
        node_id = str(node["id"])
        handler = self.handlers.get(node_id, self._default_handler)
        last_result = NodeResult.failure("node did not execute")
        for attempt in range(1, self.retry_policy.max_attempts + 1):
            started = time.perf_counter()
            self.recorder.emit("node_started", node_id=node_id, attempt=attempt, status="running")
            try:
                last_result = self._normalize(handler(node, context))
            except Exception as exc:  # noqa: BLE001 - scheduler must capture handler failures
                last_result = NodeResult.failure(f"{type(exc).__name__}: {exc}")
            duration_ms = round((time.perf_counter() - started) * 1000, 3)
            if last_result.success:
                self.recorder.emit(
                    "node_finished",
                    node_id=node_id,
                    attempt=attempt,
                    status="success",
                    duration_ms=duration_ms,
                    data={"signal": last_result.signal},
                )
                return last_result
            self.recorder.emit(
                "node_failed",
                node_id=node_id,
                attempt=attempt,
                status="failed",
                duration_ms=duration_ms,
                data={"error": last_result.error},
            )
            if attempt < self.retry_policy.max_attempts and self.retry_policy.backoff_seconds:
                time.sleep(self.retry_policy.backoff_seconds)
        return last_result

    def _normalize(self, value: NodeResult | dict[str, Any] | Any) -> NodeResult:
        if isinstance(value, NodeResult):
            return value
        if isinstance(value, dict):
            return NodeResult(
                success=bool(value.get("success", True)),
                signal=str(value.get("signal", "success")),
                output=value.get("output", value),
                error=value.get("error"),
            )
        return NodeResult(output=value)

    def _choose_next(self, node_id: str, signal: str) -> str | None:
        edges = [edge for edge in self.graph.edges if edge.get("from") == node_id]
        for edge in edges:
            if edge.get("when") == signal:
                return str(edge["to"])
        if signal != "success":
            for edge in edges:
                if edge.get("when") == "default":
                    return str(edge["to"])
        for edge in edges:
            if edge.get("when") == "success":
                return str(edge["to"])
        return None

    def _save_checkpoint(self, context: ExecutionContext) -> None:
        if not self.checkpoint_path:
            return
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        self.checkpoint_path.write_text(json.dumps(context.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.recorder.emit("checkpoint_saved", status=context.status, data={"next_node": context.next_node})

    def _finish(self, context: ExecutionContext, status: str, error: str | None) -> ExecutionContext:
        context.status = status
        context.error = error
        context.next_node = None
        self._save_checkpoint(context)
        self.recorder.emit("run_finished", status=status, data={"error": error, "steps": context.steps})
        return context

    @staticmethod
    def _default_handler(node: dict[str, Any], context: ExecutionContext) -> NodeResult:
        kind = str(node.get("kind", "script"))
        if kind == "decision":
            signal = "structured" if context.inputs.get("structured") else "ambiguous"
            return NodeResult(signal=signal, output={"signal": signal})
        return NodeResult(output={"node": node.get("id"), "kind": kind})
