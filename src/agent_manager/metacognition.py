from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Iterable

from .feedback import FeedbackStore
from .models import FeedbackEvent


@dataclass(frozen=True)
class ReflectionHypothesis:
    scope: str
    subject: str
    signal: str
    evidence_count: int
    confidence: float
    hypothesis: str
    status: str = "candidate"


@dataclass(frozen=True)
class RuleCandidate:
    rule_id: str
    scope: str
    subject: str
    signal: str
    action: str
    evidence_count: int
    confidence: float
    status: str = "candidate"
    registry_mutated: bool = False
    injection: str = "disabled"


class FeedbackInterceptor:
    """Validated host-side capture layer for reversible feedback events."""

    def __init__(self, store: FeedbackStore):
        self.store = store

    def capture(
        self,
        event_type: str,
        scope: str,
        subject: str,
        note: str,
        confidence: float = 0.5,
    ) -> FeedbackEvent:
        event = FeedbackEvent(event_type, scope, subject, note, confidence)
        self.store.record(event)
        return event


class Reflector:
    """Deterministically turns repeated feedback signals into hypotheses."""

    _HYPOTHESES = {
        "correction": "Prefer the corrected behavior when this subject recurs.",
        "undo": "Restore the prior behavior when this subject recurs.",
        "redo": "Reapply the previously accepted behavior when this subject recurs.",
        "pitfall": "Avoid the recorded pitfall when this subject recurs.",
        "fallback": "Prefer a safe fallback when this subject recurs.",
        "approval": "Preserve the approved behavior when this subject recurs.",
    }

    def reflect(
        self,
        events: Iterable[FeedbackEvent],
        *,
        minimum_confidence: float = 0.75,
    ) -> list[ReflectionHypothesis]:
        grouped: dict[tuple[str, str, str], list[FeedbackEvent]] = {}
        for event in events:
            if event.confidence >= minimum_confidence:
                grouped.setdefault((event.scope, event.subject, event.event_type), []).append(event)
        result = []
        for (scope, subject, signal), evidence in sorted(grouped.items()):
            result.append(
                ReflectionHypothesis(
                    scope=scope,
                    subject=subject,
                    signal=signal,
                    evidence_count=len(evidence),
                    confidence=round(sum(item.confidence for item in evidence) / len(evidence), 3),
                    hypothesis=self._HYPOTHESES[signal],
                )
            )
        return result


class RuleDistiller:
    """Creates reversible rule candidates without injecting or mutating registry."""

    _ACTIONS = {
        "correction": "adapt-response",
        "undo": "restore-prior-behavior",
        "redo": "reapply-accepted-behavior",
        "pitfall": "avoid-pitfall",
        "fallback": "prefer-safe-fallback",
        "approval": "preserve-approved-behavior",
    }

    def distill(self, hypotheses: Iterable[ReflectionHypothesis]) -> list[RuleCandidate]:
        result = []
        for hypothesis in hypotheses:
            identity = re.sub(r"[^a-z0-9]+", "-", f"{hypothesis.scope}-{hypothesis.signal}-{hypothesis.subject.lower()}").strip("-")
            result.append(
                RuleCandidate(
                    rule_id=identity,
                    scope=hypothesis.scope,
                    subject=hypothesis.subject,
                    signal=hypothesis.signal,
                    action=self._ACTIONS[hypothesis.signal],
                    evidence_count=hypothesis.evidence_count,
                    confidence=hypothesis.confidence,
                )
            )
        return result


class MetaCognitionEngine:
    def __init__(self, *, minimum_confidence: float = 0.75):
        self.minimum_confidence = minimum_confidence
        self.reflector = Reflector()
        self.distiller = RuleDistiller()

    def analyze(self, store: FeedbackStore) -> dict[str, object]:
        hypotheses = self.reflector.reflect(store.events, minimum_confidence=self.minimum_confidence)
        rules = self.distiller.distill(hypotheses)
        return {
            "hypotheses": [asdict(item) for item in hypotheses],
            "rule_candidates": [asdict(item) for item in rules],
            "registry_mutated": False,
            "injection": "disabled",
        }
