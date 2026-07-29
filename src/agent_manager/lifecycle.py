from __future__ import annotations

from dataclasses import dataclass

from .models import Skill


@dataclass(frozen=True)
class LifecycleProposal:
    skill_id: str
    current_status: str
    proposed_status: str
    current_frequency: str
    proposed_frequency: str
    reasons: tuple[str, ...]


def propose(skill: Skill) -> LifecycleProposal:
    reasons: list[str] = []
    rate = skill.success_rate
    if skill.calls >= 10 and rate >= 0.85:
        status = "stable"
        reasons.append("repeated-success")
    elif skill.calls >= 3 and rate < 0.5:
        status = "needs-review"
        reasons.append("low-success-rate")
    else:
        status = skill.status

    if skill.calls >= 50:
        frequency = "hot"
    elif skill.calls >= 10:
        frequency = "warm"
    else:
        frequency = "cold"
    if frequency != skill.frequency:
        reasons.append("usage-tier-recalculation")
    return LifecycleProposal(skill.id, skill.status, status, skill.frequency, frequency, tuple(reasons))
