from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import json

from .models import FeedbackEvent


ALLOWED_EVENTS = {"undo", "redo", "pitfall", "fallback", "correction", "approval"}


class FeedbackStore:
    def __init__(self, events: list[FeedbackEvent] | None = None):
        self.events = events or []

    def record(self, event: FeedbackEvent) -> None:
        if event.event_type not in ALLOWED_EVENTS:
            raise ValueError(f"unsupported feedback type: {event.event_type}")
        if event.scope not in {"profile", "project"}:
            raise ValueError(f"unsupported feedback scope: {event.scope}")
        if not 0 <= event.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        self.events.append(event)

    def candidates(self, minimum_confidence: float = 0.75) -> list[dict]:
        grouped: dict[tuple[str, str, str], list[FeedbackEvent]] = {}
        for event in self.events:
            if event.confidence >= minimum_confidence:
                grouped.setdefault((event.scope, event.subject, event.event_type), []).append(event)
        return [
            {
                "scope": scope,
                "subject": subject,
                "signal": event_type,
                "evidence_count": len(events),
                "confidence": round(sum(item.confidence for item in events) / len(events), 3),
                "status": "candidate",
            }
            for (scope, subject, event_type), events in sorted(grouped.items())
        ]

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps([asdict(item) for item in self.events], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
