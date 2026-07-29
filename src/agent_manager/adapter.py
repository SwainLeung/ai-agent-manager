from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from .entropy import audit
from .decision import DecisionMatrix
from .executor import ProposalExecutor
from .promotion import PromotionLedger
from .registry_apply import RegistryApplier
from .execution import ExecutionContext, GraphScheduler, RetryPolicy
from .feedback import FeedbackStore
from .graph import GraphDefinition
from .lifecycle import propose
from .models import FeedbackEvent, RouteDecision
from .recorder import ExecutionRecorder
from .registry import SkillRegistry
from .router import RouteSignals, Router


@dataclass(frozen=True)
class AdapterPlan:
    task: str
    decisions: tuple[RouteDecision, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "decisions": [asdict(decision) for decision in self.decisions],
        }


@dataclass(frozen=True)
class AdapterRun:
    plan: AdapterPlan
    context: ExecutionContext
    trace_path: Path
    checkpoint_path: Path

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan": self.plan.to_dict(),
            "context": self.context.to_dict(),
            "trace": str(self.trace_path),
            "checkpoint": str(self.checkpoint_path),
        }


class LocalAgentAdapter:
    """Bridge a local agent task into routing, graph execution, and feedback."""

    def __init__(
        self,
        registry_path: str | Path,
        graph_path: str | Path,
        *,
        state_dir: str | Path = ".agent-manager",
    ):
        self.registry_path = Path(registry_path)
        self.graph_path = Path(graph_path)
        self.state_dir = Path(state_dir)
        self.registry = SkillRegistry.load(self.registry_path)
        self.router = Router(self.registry)
        self.decision_matrix = DecisionMatrix()
        self.proposal_executor = ProposalExecutor(matrix=self.decision_matrix)

    @classmethod
    def for_project(cls, root: str | Path, *, state_dir: str | Path = ".agent-manager") -> "LocalAgentAdapter":
        project_root = Path(root)
        state = Path(state_dir)
        if not state.is_absolute():
            state = project_root / state
        return cls(
            project_root / "config" / "skill-registry.json",
            project_root / "config" / "example-graph.json",
            state_dir=state,
        )

    @property
    def feedback_path(self) -> Path:
        return self.state_dir / "feedback.json"

    @property
    def promotion_path(self) -> Path:
        return self.state_dir / "promotion-ledger.json"

    def prepare(
        self,
        task: str,
        signals: RouteSignals | None = None,
        *,
        top_k: int = 3,
    ) -> AdapterPlan:
        return AdapterPlan(task, self.router.decide(task, signals, top_k))

    def decide_entity(self, entity: Mapping[str, Any]) -> dict[str, Any]:
        return self.decision_matrix.decide(entity).to_dict()

    def decide_entities(self, entities: list[Mapping[str, Any]]) -> dict[str, Any]:
        return self.decision_matrix.decide_many(entities)

    def execute_entities(
        self,
        entities: list[Mapping[str, Any]],
        *,
        checkpoint: str | Path | None = None,
        max_items: int | None = None,
    ) -> dict[str, Any]:
        return self.proposal_executor.execute_entities(entities, checkpoint=checkpoint, max_items=max_items)

    def propose_promotions(
        self,
        records: list[Mapping[str, Any]],
        *,
        min_successes: int = 3,
        min_success_rate: float = 0.9,
    ) -> dict[str, Any]:
        ledger = PromotionLedger.load(self.promotion_path)
        candidates = ledger.propose(records, min_successes=min_successes, min_success_rate=min_success_rate)
        ledger.save(self.promotion_path)
        return {"candidates": [item.to_dict() for item in candidates], "ledger": str(self.promotion_path), "registry_mutated": False}

    def review_promotion(self, operation: str, decision: str, note: str) -> dict[str, Any]:
        ledger = PromotionLedger.load(self.promotion_path)
        candidate = ledger.review(operation, decision, note)
        ledger.save(self.promotion_path)
        return {"candidate": candidate.to_dict(), "ledger": str(self.promotion_path), "registry_mutated": False}

    def create_promotion_manifest(self, operation: str, *, registry_path: str | Path | None = None, manifest_path: str | Path) -> dict[str, Any]:
        target = Path(registry_path) if registry_path else self.registry_path
        patch = RegistryApplier(target, self.promotion_path).create_manifest(operation, manifest_path)
        return patch.to_dict()

    def approve_promotion_manifest(self, *, registry_path: str | Path | None = None, manifest_path: str | Path, note: str) -> dict[str, Any]:
        target = Path(registry_path) if registry_path else self.registry_path
        manifest = RegistryApplier(target, self.promotion_path).approve_manifest(manifest_path, note)
        return {"manifest": manifest.to_dict(), "registry_mutated": False}

    def apply_promotion(self, operation: str | None = None, *, registry_path: str | Path | None = None, write: bool = False, manifest_path: str | Path | None = None) -> dict[str, Any]:
        target = Path(registry_path) if registry_path else self.registry_path
        applier = RegistryApplier(target, self.promotion_path)
        if manifest_path is not None:
            patch = applier.apply_manifest(manifest_path, write=write)
        elif operation:
            patch = applier.apply(operation, write=write)
        else:
            raise ValueError("operation or manifest_path is required")
        return patch.to_dict()

    def rollback_promotion(self, *, registry_path: str | Path | None = None, manifest_path: str | Path, write: bool = False) -> dict[str, Any]:
        target = Path(registry_path) if registry_path else self.registry_path
        patch = RegistryApplier(target, self.promotion_path).rollback(manifest_path, write=write)
        return patch.to_dict()

    def run(
        self,
        task: str,
        inputs: Mapping[str, Any] | None = None,
        signals: RouteSignals | None = None,
        *,
        graph_path: str | Path | None = None,
        checkpoint: str | Path | None = None,
        trace: str | Path | None = None,
        max_attempts: int = 1,
        backoff_seconds: float = 0.0,
        max_steps: int = 100,
    ) -> AdapterRun:
        plan = self.prepare(task, signals)
        graph = GraphDefinition.load(graph_path or self.graph_path)
        recorder = ExecutionRecorder(graph_id=graph.graph_id)
        checkpoint_path = Path(checkpoint) if checkpoint else self.state_dir / "checkpoints" / f"{recorder.run_id}.json"
        resume = checkpoint_path if checkpoint_path.exists() else None
        scheduler = GraphScheduler(
            graph,
            recorder=recorder,
            retry_policy=RetryPolicy(max_attempts, backoff_seconds),
            checkpoint_path=checkpoint_path,
            max_steps=max_steps,
        )
        context = scheduler.run(inputs or {}, checkpoint=resume)
        trace_path = Path(trace) if trace else self.state_dir / "traces" / f"{context.run_id}.json"
        recorder.save(trace_path)
        return AdapterRun(plan, context, trace_path, checkpoint_path)

    def record_feedback(
        self,
        event_type: str,
        scope: str,
        subject: str,
        note: str,
        confidence: float = 0.5,
    ) -> FeedbackEvent:
        event = FeedbackEvent(event_type, scope, subject, note, confidence)
        store = FeedbackStore.load(self.feedback_path)
        store.record(event)
        self.feedback_path.parent.mkdir(parents=True, exist_ok=True)
        store.save(self.feedback_path)
        return event

    def report(self) -> dict[str, Any]:
        store = FeedbackStore.load(self.feedback_path)
        return {
            "feedback_candidates": store.candidates(),
            "entropy_findings": [asdict(item) for item in audit(list(self.registry.skills))],
            "lifecycle_proposals": [asdict(propose(skill)) for skill in self.registry.skills],
            "state_dir": str(self.state_dir),
        }

    def save_report(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(self.report(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
