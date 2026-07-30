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
from .metrics import UsageLedger
from .metacognition import FeedbackInterceptor, MetaCognitionEngine
from .recorder import ExecutionRecorder
from .registry import SkillRegistry
from .registry_proposal import RegistryChangeWorkflow
from .rules import RuleStore
from .router import RouteSignals, Router
from .sandbox import ScriptSandbox
from .solidification import SkillScriptCompiler


@dataclass(frozen=True)
class AdapterPlan:
    task: str
    decisions: tuple[RouteDecision, ...]
    active_rules: tuple[dict[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "decisions": [asdict(decision) for decision in self.decisions],
            "active_rules": list(self.active_rules),
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

    @property
    def usage_path(self) -> Path:
        return self.state_dir / "usage.json"

    @property
    def rules_path(self) -> Path:
        return self.state_dir / "rules.json"

    def prepare(
        self,
        task: str,
        signals: RouteSignals | None = None,
        *,
        top_k: int = 3,
    ) -> AdapterPlan:
        active_rules = tuple(rule.to_dict() for rule in RuleStore.load(self.rules_path).active())
        return AdapterPlan(task, tuple(self.router.decide(task, signals, top_k)), active_rules)

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
        checkpoint_every: int = 100,
    ) -> dict[str, Any]:
        return self.proposal_executor.execute_entities(entities, checkpoint=checkpoint, max_items=max_items, checkpoint_every=checkpoint_every)

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
        ledger = UsageLedger.load(self.usage_path)
        selected_skill_ids = [decision.skill_id for decision in plan.decisions[:1]]
        ledger.record_run(context.run_id, selected_skill_ids, context.status)
        ledger.save(self.usage_path)
        return AdapterRun(plan, context, trace_path, checkpoint_path)

    def record_feedback(
        self,
        event_type: str,
        scope: str,
        subject: str,
        note: str,
        confidence: float = 0.5,
    ) -> FeedbackEvent:
        store = FeedbackStore.load(self.feedback_path)
        event = FeedbackInterceptor(store).capture(event_type, scope, subject, note, confidence)
        self.feedback_path.parent.mkdir(parents=True, exist_ok=True)
        store.save(self.feedback_path)
        return event

    def sync_rules(self) -> dict[str, Any]:
        """Persist metacognition candidates without enabling or applying them."""

        store = FeedbackStore.load(self.feedback_path)
        analysis = MetaCognitionEngine().analyze(store)
        rules = RuleStore.load(self.rules_path)
        rules.upsert_candidates(analysis["rule_candidates"])
        rules.save(self.rules_path)
        return {
            "rules": rules.to_dict(),
            "active_rules": [rule.to_dict() for rule in rules.active()],
            "registry_mutated": False,
            "injection": "explicit-review-required",
            "storage": str(self.rules_path),
        }

    def review_rule(self, rule_id: str, decision: str, note: str) -> dict[str, Any]:
        self.sync_rules()
        rules = RuleStore.load(self.rules_path)
        rule = rules.review(rule_id, decision, note)
        rules.save(self.rules_path)
        return {
            "rule": rule.to_dict(),
            "active_rules": [item.to_dict() for item in rules.active()],
            "registry_mutated": False,
            "storage": str(self.rules_path),
        }

    def revoke_rule(self, rule_id: str, note: str) -> dict[str, Any]:
        rules = RuleStore.load(self.rules_path)
        rule = rules.revoke(rule_id, note)
        rules.save(self.rules_path)
        return {
            "rule": rule.to_dict(),
            "active_rules": [item.to_dict() for item in rules.active()],
            "registry_mutated": False,
            "storage": str(self.rules_path),
        }

    def rules_report(self) -> dict[str, Any]:
        rules = RuleStore.load(self.rules_path)
        return {
            "rules": rules.to_dict(),
            "active_rules": [rule.to_dict() for rule in rules.active()],
            "registry_mutated": False,
            "injection": "active-rules-exposed-to-plan",
            "storage": str(self.rules_path),
        }

    def solidify_skill(
        self,
        skill_id: str,
        records: list[Mapping[str, Any]],
        *,
        operation: str,
        min_successes: int = 3,
        min_success_rate: float = 0.9,
    ) -> dict[str, Any]:
        source = self.registry.get(skill_id)
        report = SkillScriptCompiler(
            min_successes=min_successes,
            min_success_rate=min_success_rate,
        ).compile(source, records, operation=operation)
        return report.to_dict()

    def sandbox_script(
        self,
        candidate: Mapping[str, Any],
        entities: list[Mapping[str, Any]],
        *,
        drift_tolerance: float = 0.05,
    ) -> dict[str, Any]:
        return ScriptSandbox().replay(candidate, entities, drift_tolerance=drift_tolerance).to_dict()

    def propose_registry_change(self, candidate_file: str | Path, proposal_file: str | Path, *, preview_file: str | Path | None = None, registry_path: str | Path | None = None) -> dict[str, Any]:
        candidate = json.loads(Path(candidate_file).read_text(encoding="utf-8-sig"))
        target = Path(registry_path) if registry_path else self.registry_path
        proposal = RegistryChangeWorkflow(target).propose(candidate, proposal_file, preview_path=preview_file)
        return {"proposal": proposal.to_dict(), "registry_mutated": False}

    def approve_registry_change(self, proposal_file: str | Path, note: str, *, registry_path: str | Path | None = None) -> dict[str, Any]:
        target = Path(registry_path) if registry_path else self.registry_path
        proposal = RegistryChangeWorkflow(target).approve(proposal_file, note)
        return {"proposal": proposal.to_dict(), "registry_mutated": False}

    def apply_registry_change(self, proposal_file: str | Path, *, write: bool = False, registry_path: str | Path | None = None) -> dict[str, Any]:
        target = Path(registry_path) if registry_path else self.registry_path
        return RegistryChangeWorkflow(target).apply(proposal_file, write=write)

    def rollback_registry_change(self, proposal_file: str | Path, *, write: bool = False, registry_path: str | Path | None = None) -> dict[str, Any]:
        target = Path(registry_path) if registry_path else self.registry_path
        return RegistryChangeWorkflow(target).rollback(proposal_file, write=write)



    def pitfall_summary(self) -> list[dict]:
        store = FeedbackStore.load(self.feedback_path)
        return store.pitfall_summary()

    def pitfall_detail(self, pitfall_id: str) -> list[dict]:
        store = FeedbackStore.load(self.feedback_path)
        return store.pitfall_detail(pitfall_id)

    def slim_report(self) -> dict:
        from .entropy import slim_report as _slim
        from .registry import SkillRegistry
        registry = SkillRegistry.load(self.registry_path)
        findings = audit(registry)
        return _slim(findings)

    def print_slim_report(self) -> str:
        from .entropy import print_slim_report as _print_slim
        report = self.slim_report()
        return _print_slim(report)

    def report(self) -> dict[str, Any]:
        store = FeedbackStore.load(self.feedback_path)
        ledger = UsageLedger.load(self.usage_path)
        projected_skills = ledger.project(self.registry.skills)
        metrics = ledger.report(self.registry.skills)
        metrics["usage_path"] = str(self.usage_path)
        metacognition = MetaCognitionEngine().analyze(store)
        return {
            "feedback_candidates": store.candidates(),
            "entropy_findings": [asdict(item) for item in audit(list(projected_skills))],
            "lifecycle_proposals": [asdict(propose(skill)) for skill in projected_skills],
            "metrics": metrics,
            "metacognition": metacognition,
            "rules": self.rules_report(),
            "state_dir": str(self.state_dir),
        }

    def save_report(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(self.report(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
