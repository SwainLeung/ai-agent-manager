from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping


SCRIPT_OPERATIONS = {
    "snapshot_hash",
    "frontmatter_validate",
    "link_extract",
    "duplicate_key",
    "category_count",
    "idempotency_check",
}
SKILL_OPERATIONS = {
    "ontology_classify",
    "relation_discovery",
    "summarize",
}
REVIEW_OPERATIONS = {
    "duplicate_merge",
    "candidate_writeback",
    "schema_approval",
}


@dataclass(frozen=True)
class ExecutionProposal:
    subject_id: str
    operation: str
    kind: str
    score: float
    confidence: float
    reasons: tuple[str, ...]
    gate: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DecisionMatrix:
    """Choose script, skill, or human review for one structured entity operation."""

    def __init__(self, *, review_confidence: float = 0.75):
        if not 0 <= review_confidence <= 1:
            raise ValueError("review_confidence must be between 0 and 1")
        self.review_confidence = review_confidence

    def decide(self, entity: Mapping[str, Any]) -> ExecutionProposal:
        subject_id = str(entity.get("entity_id") or entity.get("source_id") or "unknown")
        operation = str(entity.get("operation") or "ontology_classify")
        confidence = float(entity.get("confidence", 0.0))
        safety_status = str(entity.get("safety_status", "clear"))
        sensitive = bool(entity.get("safety_sensitive", False)) or safety_status in {"blocked", "sensitive"}
        requires_review = bool(entity.get("requires_human_review", False))
        semantic_ambiguity = bool(entity.get("semantic_ambiguity", operation in SKILL_OPERATIONS | REVIEW_OPERATIONS))
        schema_known = bool(entity.get("schema_known", operation in SCRIPT_OPERATIONS))
        repeatable = bool(entity.get("repeatable", operation in SCRIPT_OPERATIONS))
        deterministic = bool(entity.get("deterministic", operation in SCRIPT_OPERATIONS))
        reasons: list[str] = []

        if sensitive:
            reasons.append("safety-sensitive-content")
        if requires_review:
            reasons.append("explicit-human-review-gate")
        if confidence < self.review_confidence:
            reasons.append("confidence-below-review-threshold")
        if operation in REVIEW_OPERATIONS:
            reasons.append("operation-requires-human-decision")

        if sensitive or requires_review or operation in REVIEW_OPERATIONS or confidence < self.review_confidence:
            return ExecutionProposal(subject_id, operation, "human_review", 10.0, confidence, tuple(reasons), "human")

        if deterministic and repeatable and schema_known and not semantic_ambiguity:
            reasons.extend(["deterministic", "repeatable", "schema-known", "no-semantic-ambiguity"])
            return ExecutionProposal(subject_id, operation, "script", 9.0, confidence, tuple(reasons), "automatic")

        reasons.append("semantic-or-open-ended-interpretation")
        return ExecutionProposal(subject_id, operation, "skill", 6.0, confidence, tuple(reasons), "host-agent")

    def infer_operations(self, entity: Mapping[str, Any]) -> tuple[str, ...]:
        """Infer the standard entity pipeline without provider-specific code."""
        operations = ["snapshot_hash", "frontmatter_validate", "duplicate_key"]
        if entity.get("linked_source_ids"):
            operations.append("link_extract")
        operations.extend(["ontology_classify", "relation_discovery"])
        if entity.get("duplicate_key"):
            operations.append("duplicate_merge")
        if entity.get("writeback_status") or entity.get("source_url"):
            operations.append("candidate_writeback")
        return tuple(operations)

    def decide_many(self, entities: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
        proposals: list[ExecutionProposal] = []
        entity_count = 0
        for entity in entities:
            entity_count += 1
            if entity.get("operation"):
                proposals.append(self.decide(entity))
            else:
                for operation in self.infer_operations(entity):
                    proposals.append(self.decide({**entity, "operation": operation}))
        counts = {kind: sum(1 for item in proposals if item.kind == kind) for kind in ("script", "skill", "human_review")}
        return {
            "entity_count": entity_count,
            "proposal_count": len(proposals),
            "proposals": [item.to_dict() for item in proposals],
            "counts": counts,
            "human_gate_required": counts["human_review"] > 0,
        }
