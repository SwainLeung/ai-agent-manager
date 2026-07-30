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


def propose_fixes(skills: list) -> list[dict]:
    """Generate RegistryChangeProposal candidates for degraded skills.

    Parameters
    ----------
    skills : list[Skill or dict]
        List of Skill objects or dicts from registry.

    Returns
    -------
    list of dict, each a candidate proposal:
        skill_id, current_status, proposed_status, reason, action
    """
    candidates = []
    for skill in skills:
        sid = skill.id if hasattr(skill, "id") else skill.get("id", "")
        status = skill.status if hasattr(skill, "status") else skill.get("status", "")
        calls = skill.calls if hasattr(skill, "calls") else skill.get("calls", 0)
        success_rate = skill.success_rate if hasattr(skill, "success_rate") else skill.get("success_rate", 0.0)
        proposal = propose(skill) if hasattr(skill, "status") else _propose_from_dict(skill)
        if proposal.proposed_status != status and proposal.proposed_status in {"needs-review", "deprecated"}:
            candidates.append({
                "skill_id": sid,
                "current_status": status,
                "proposed_status": proposal.proposed_status,
                "reason": "; ".join(proposal.reasons) if proposal.reasons else "lifecycle-degradation",
                "action": f"set status to {proposal.proposed_status}",
            })
        if calls >= 20 and status in {"experimental", "needs-review"}:
            candidates.append({
                "skill_id": sid,
                "current_status": status,
                "proposed_status": "deprecated",
                "reason": "lifecycle-stall (high calls, low improvement)",
                "action": "archive skill",
            })
    return candidates


def _propose_from_dict(skill: dict) -> "LifecycleProposal":
    """Create a LifecycleProposal from a dict without importing Skill."""
    sid = skill.get("id", "")
    status = skill.get("status", "")
    freq = skill.get("frequency", "cold")
    calls = skill.get("calls", 0)
    rate = skill.get("success_rate", 0.0)
    reasons = []
    if calls >= 10 and rate >= 0.85:
        p_status = "stable"
        reasons.append("repeated-success")
    elif calls >= 3 and rate < 0.5:
        p_status = "needs-review"
        reasons.append("low-success-rate")
    else:
        p_status = status
    if calls >= 50:
        p_freq = "hot"
    elif calls >= 10:
        p_freq = "warm"
    else:
        p_freq = "cold"
    if p_freq != freq:
        reasons.append("usage-tier-recalculation")
    return LifecycleProposal(sid, status, p_status, freq, p_freq, tuple(reasons))
