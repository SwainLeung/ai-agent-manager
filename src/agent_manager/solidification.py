from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any, Iterable, Mapping

from .models import Skill


class SolidificationError(ValueError):
    pass


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _next_minor_version(version: str) -> str:
    parts = version.split(".")
    if len(parts) == 3 and all(part.isdigit() for part in parts):
        return f"{parts[0]}.{int(parts[1]) + 1}.0"
    return "0.1.0"


@dataclass(frozen=True)
class ScriptCandidate:
    id: str
    source_skill_id: str
    source_skill_version: str
    operation: str
    layer: str
    kind: str
    frequency: str
    version: str
    status: str
    triggers: tuple[str, ...]
    description: str
    calls: int
    successes: int
    last_used: str | None
    evidence_count: int
    success_rate: float
    reasons: tuple[str, ...]
    registry_mutated: bool = False
    review_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SolidificationReport:
    source_skill_id: str
    operation: str
    eligible: bool
    evidence_count: int
    success_count: int
    failure_count: int
    success_rate: float
    reasons: tuple[str, ...]
    candidate: ScriptCandidate | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["candidate"] = self.candidate.to_dict() if self.candidate else None
        return payload


class SkillScriptCompiler:
    """Compile repeated execution evidence into a reviewed Script candidate."""

    def __init__(self, *, min_successes: int = 3, min_success_rate: float = 0.9):
        if min_successes < 1:
            raise ValueError("min_successes must be at least 1")
        if not 0 <= min_success_rate <= 1:
            raise ValueError("min_success_rate must be between 0 and 1")
        self.min_successes = min_successes
        self.min_success_rate = min_success_rate

    def compile(
        self,
        skill: Skill | Mapping[str, Any],
        records: Iterable[Mapping[str, Any]],
        *,
        operation: str,
    ) -> SolidificationReport:
        source = skill if isinstance(skill, Skill) else Skill.from_dict(dict(skill))
        operation = operation.strip()
        if not operation:
            raise SolidificationError("operation is required")
        if source.kind != "skill":
            raise SolidificationError(f"source capability is not a Skill: {source.id}")

        evidence = [
            record
            for record in records
            if str(record.get("operation", "")) == operation
            and str(record.get("status", "")) in {"completed", "failed"}
            and str(record.get("kind", "")) != "human_review"
        ]
        success_count = sum(str(record.get("status")) == "completed" for record in evidence)
        failure_count = sum(str(record.get("status")) == "failed" for record in evidence)
        evidence_count = success_count + failure_count
        success_rate = success_count / evidence_count if evidence_count else 0.0
        reasons: list[str] = []
        if success_count < self.min_successes:
            reasons.append("minimum-successes-not-met")
        if success_rate < self.min_success_rate:
            reasons.append("success-rate-threshold-not-met")
        if not evidence:
            reasons.append("no-matching-execution-evidence")
        if reasons:
            return SolidificationReport(
                source_skill_id=source.id,
                operation=operation,
                eligible=False,
                evidence_count=evidence_count,
                success_count=success_count,
                failure_count=failure_count,
                success_rate=round(success_rate, 3),
                reasons=tuple(reasons),
            )

        operation_slug = _slug(operation)
        candidate_id = f"{source.id}.script.{operation_slug}"
        triggers = tuple(dict.fromkeys((*source.triggers, operation, *operation.lower().split("_"))))
        candidate = ScriptCandidate(
            id=candidate_id,
            source_skill_id=source.id,
            source_skill_version=source.version,
            operation=operation,
            layer=source.layer,
            kind="script",
            frequency=source.frequency,
            version=_next_minor_version(source.version),
            status="candidate",
            triggers=triggers,
            description=f"Deterministic Script candidate distilled from {source.id} for {operation}.",
            calls=evidence_count,
            successes=success_count,
            last_used=source.last_used,
            evidence_count=evidence_count,
            success_rate=round(success_rate, 3),
            reasons=("minimum-successes-met", "success-rate-threshold-met", "human-review-required"),
        )
        return SolidificationReport(
            source_skill_id=source.id,
            operation=operation,
            eligible=True,
            evidence_count=evidence_count,
            success_count=success_count,
            failure_count=failure_count,
            success_rate=round(success_rate, 3),
            reasons=candidate.reasons,
            candidate=candidate,
        )
