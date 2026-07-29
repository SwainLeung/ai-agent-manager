from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
import uuid


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


@dataclass(frozen=True)
class TraceEvent:
    run_id: str
    graph_id: str
    event: str
    timestamp: str
    node_id: str | None = None
    attempt: int | None = None
    status: str | None = None
    duration_ms: float | None = None
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ExecutionRecorder:
    """In-memory execution trace recorder with JSON persistence."""

    def __init__(self, run_id: str | None = None, graph_id: str = ""):
        self.run_id = run_id or uuid.uuid4().hex
        self.graph_id = graph_id
        self.events: list[TraceEvent] = []

    def bind(self, run_id: str, graph_id: str) -> None:
        self.run_id = run_id
        self.graph_id = graph_id

    def emit(
        self,
        event: str,
        *,
        node_id: str | None = None,
        attempt: int | None = None,
        status: str | None = None,
        duration_ms: float | None = None,
        data: dict[str, Any] | None = None,
    ) -> TraceEvent:
        item = TraceEvent(
            run_id=self.run_id,
            graph_id=self.graph_id,
            event=event,
            timestamp=utc_now(),
            node_id=node_id,
            attempt=attempt,
            status=status,
            duration_ms=duration_ms,
            data=dict(data or {}),
        )
        self.events.append(item)
        return item

    def save(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "run_id": self.run_id,
            "graph_id": self.graph_id,
            "events": [event.to_dict() for event in self.events],
        }
        destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "ExecutionRecorder":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        recorder = cls(str(payload["run_id"]), str(payload.get("graph_id", "")))
        recorder.events = [TraceEvent(**item) for item in payload.get("events", [])]
        return recorder

    def summary(self) -> dict[str, Any]:
        completed = [event for event in self.events if event.event == "run_finished"]
        node_events = [event for event in self.events if event.event == "node_finished"]
        return {
            "run_id": self.run_id,
            "graph_id": self.graph_id,
            "event_count": len(self.events),
            "node_count": len(node_events),
            "status": completed[-1].status if completed else "running",
        }
