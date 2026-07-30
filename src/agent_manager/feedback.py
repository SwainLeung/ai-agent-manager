from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import json

from .models import FeedbackEvent


ALLOWED_EVENTS = {"undo", "redo", "pitfall", "fallback", "correction", "approval"}


class FeedbackStore:
    def __init__(self, events: list[FeedbackEvent] | None = None):
        self.events = list(events or [])

    def record(self, event: FeedbackEvent) -> None:
        if event.event_type not in ALLOWED_EVENTS:
            raise ValueError(f"unsupported feedback type: {event.event_type}")
        if event.scope not in {"profile", "project"}:
            raise ValueError(f"unsupported feedback scope: {event.scope}")
        if not 0 <= event.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        self.events.append(event)

    

    def pitfall_summary(self) -> list[dict]:
        """Return pitfall events grouped and ranked by frequency."""
        pitfall_events = [e for e in self.events if e.event_type == "pitfall"]
        grouped: dict[tuple[str, str, str], dict] = {}
        for ev in pitfall_events:
            key = (ev.scope, ev.subject, ev.event_type)
            if key not in grouped:
                grouped[key] = {
                    "id": f"pitfall-{len(grouped) + 1}",
                    "scope": ev.scope,
                    "subject": ev.subject,
                    "signal": ev.event_type,
                    "count": 0,
                    "latest_note": "",
                    "latest_confidence": 0.0,
                    "first_seen": "",
                    "last_seen": "",
                }
            g = grouped[key]
            g["count"] += 1
            g["latest_note"] = ev.note or ""
            g["latest_confidence"] = ev.confidence
            if not g["first_seen"]:
                g["first_seen"] = ""
            g["last_seen"] = ""
        result = sorted(grouped.values(), key=lambda x: x["count"], reverse=True)
        for i, item in enumerate(result):
            item["id"] = f"pitfall-{i + 1}"
        return result

    def pitfall_detail(self, pitfall_id: str) -> list[dict]:
        """Return raw pitfall events matching a pitfall summary entry."""
        summary = self.pitfall_summary()
        target = next((s for s in summary if s["id"] == pitfall_id), None)
        if not target:
            return []
        return [
            {"note": e.note, "confidence": e.confidence}
            for e in self.events
            if e.event_type == "pitfall"
            and e.scope == target["scope"]
            and e.subject == target["subject"]
        ]

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

    @classmethod
    def load(cls, path: str | Path) -> "FeedbackStore":
        source = Path(path)
        if not source.exists():
            return cls()
        payload = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("feedback store must contain a list")
        return cls([FeedbackEvent(**item) for item in payload])
