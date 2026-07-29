from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class PromotionCandidate:
    operation: str
    kind: str
    evidence_count: int
    success_count: int
    failure_count: int
    success_rate: float
    status: str
    reasons: tuple[str, ...]
    review_note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PromotionLedger:
    """Persist reversible Script promotion candidates without mutating registry."""

    def __init__(self, candidates: Iterable[PromotionCandidate] | None = None):
        self.candidates = {candidate.operation: candidate for candidate in candidates or ()}

    @classmethod
    def load(cls, path: str | Path) -> "PromotionLedger":
        source = Path(path)
        if not source.exists():
            return cls()
        payload = json.loads(source.read_text(encoding="utf-8"))
        return cls(PromotionCandidate(**item) for item in payload.get("candidates", []))

    def save(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps({"schema_version": 1, "candidates": [item.to_dict() for item in self.candidates.values()]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def propose(
        self,
        records: Iterable[Mapping[str, Any]],
        *,
        min_successes: int = 3,
        min_success_rate: float = 0.9,
    ) -> list[PromotionCandidate]:
        if min_successes < 1:
            raise ValueError("min_successes must be at least 1")
        if not 0 <= min_success_rate <= 1:
            raise ValueError("min_success_rate must be between 0 and 1")
        grouped: dict[str, dict[str, set[str]]] = {}
        for record in records:
            if record.get("kind") != "script":
                continue
            operation = str(record.get("operation", ""))
            subject = str(record.get("subject_id", "unknown"))
            status = str(record.get("status", ""))
            if not operation:
                continue
            bucket = grouped.setdefault(operation, {"completed": set(), "failed": set()})
            if status in bucket:
                bucket[status].add(subject)
        proposed: list[PromotionCandidate] = []
        for operation, bucket in sorted(grouped.items()):
            success_count = len(bucket["completed"])
            failure_count = len(bucket["failed"])
            evidence_count = success_count + failure_count
            success_rate = success_count / evidence_count if evidence_count else 0.0
            if success_count < min_successes or success_rate < min_success_rate:
                continue
            previous = self.candidates.get(operation)
            status = previous.status if previous and previous.status in {"approved", "rejected"} else "candidate"
            candidate = PromotionCandidate(
                operation=operation,
                kind="script",
                evidence_count=evidence_count,
                success_count=success_count,
                failure_count=failure_count,
                success_rate=round(success_rate, 3),
                status=status,
                reasons=("minimum-successes-met", "success-rate-threshold-met", "human-review-required"),
                review_note=previous.review_note if previous else None,
            )
            self.candidates[operation] = candidate
            proposed.append(candidate)
        return proposed

    def review(self, operation: str, decision: str, note: str) -> PromotionCandidate:
        if decision not in {"approve", "reject"}:
            raise ValueError("decision must be approve or reject")
        candidate = self.candidates.get(operation)
        if candidate is None:
            raise KeyError(operation)
        reviewed = PromotionCandidate(**{**candidate.to_dict(), "status": "approved" if decision == "approve" else "rejected", "review_note": note})
        self.candidates[operation] = reviewed
        return reviewed

    def report(self) -> list[dict[str, Any]]:
        return [item.to_dict() for item in sorted(self.candidates.values(), key=lambda item: item.operation)]
