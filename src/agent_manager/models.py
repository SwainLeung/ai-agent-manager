from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Skill:
    id: str
    layer: str
    kind: str
    frequency: str
    version: str
    status: str
    triggers: tuple[str, ...] = field(default_factory=tuple)
    description: str = ""
    calls: int = 0
    successes: int = 0
    last_used: str | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Skill":
        return cls(
            id=str(value["id"]),
            layer=str(value.get("layer", "domain")),
            kind=str(value.get("kind", "skill")),
            frequency=str(value.get("frequency", "cold")),
            version=str(value.get("version", "0.1.0")),
            status=str(value.get("status", "experimental")),
            triggers=tuple(str(item).lower() for item in value.get("triggers", [])),
            description=str(value.get("description", "")),
            calls=int(value.get("calls", 0)),
            successes=int(value.get("successes", 0)),
            last_used=value.get("last_used"),
        )

    @property
    def success_rate(self) -> float:
        return self.successes / self.calls if self.calls else 0.0


@dataclass(frozen=True)
class RouteDecision:
    skill_id: str
    kind: str
    score: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class FeedbackEvent:
    event_type: str
    scope: str
    subject: str
    note: str
    confidence: float = 0.5
