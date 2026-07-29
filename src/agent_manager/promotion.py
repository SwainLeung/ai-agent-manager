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

    def __init__(
        self,
        candidates: Iterable[PromotionCandidate] | None = None,
        evidence: Mapping[str, Mapping[str, str]] | None = None,
    ):
        self.candidates = {candidate.operation: candidate for candidate in candidates or ()}
        self.evidence = {
            str(operation): {str(key): str(status) for key, status in values.items()}
            for operation, values in (evidence or {}).items()
        }

    @classmethod
    def load(cls, path: str | Path) -> "PromotionLedger":
        source = Path(path)
        if not source.exists():
            return cls()
        payload = json.loads(source.read_text(encoding="utf-8"))
        return cls(
            (PromotionCandidate(**item) for item in payload.get("candidates", [])),
            payload.get("evidence", {}),
        )

    def save(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps({
            "schema_version": 2,
            "candidates": [item.to_dict() for item in self.candidates.values()],
            "evidence": self.evidence,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

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
        touched: set[str] = set()
        for index, record in enumerate(records):
            if record.get("kind") != "script":
                continue
            operation = str(record.get("operation", ""))
            status = str(record.get("status", ""))
            if not operation or status not in {"completed", "failed"}:
                continue
            subject = str(record.get("subject_id", "unknown"))
            explicit_key = record.get("evidence_key")
            source_run = record.get("source_run_id")
            evidence_key = str(explicit_key or (f"{source_run}:{subject}" if source_run else subject or f"record-{index}"))
            self.evidence.setdefault(operation, {})[evidence_key] = status
            touched.add(operation)
        proposed: list[PromotionCandidate] = []
        for operation in sorted(touched):
            bucket = self.evidence[operation]
            success_count = sum(status == "completed" for status in bucket.values())
            failure_count = sum(status == "failed" for status in bucket.values())
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
