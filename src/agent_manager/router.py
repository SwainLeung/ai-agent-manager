from __future__ import annotations

from dataclasses import dataclass

from .models import RouteDecision, Skill
from .registry import SkillRegistry


@dataclass(frozen=True)
class RouteSignals:
    structured: bool = False
    deterministic: bool = False
    low_latency: bool = False
    creative: bool = False


class Router:
    def __init__(self, registry: SkillRegistry):
        self.registry = registry

    def decide(self, task: str, signals: RouteSignals | None = None, top_k: int = 3) -> tuple[RouteDecision, ...]:
        signals = signals or RouteSignals()
        results: list[RouteDecision] = []
        for skill, trigger_score in self.registry.matching(task):
            score = float(trigger_score * 3)
            reasons = [f"trigger-match:{trigger_score}"]
            if signals.structured or signals.deterministic or signals.low_latency:
                if skill.kind == "script":
                    score += 4
                    reasons.append("deterministic-work-favors-script")
                else:
                    score -= 1
            if signals.creative and skill.kind == "skill":
                score += 3
                reasons.append("creative-work-favors-skill")
            if skill.frequency == "hot":
                score += 1
                reasons.append("hot-tier")
            if skill.layer == "system":
                score += 0.5
            results.append(RouteDecision(skill.id, skill.kind, score, tuple(reasons)))
        return tuple(sorted(results, key=lambda item: (-item.score, item.skill_id))[:top_k])
