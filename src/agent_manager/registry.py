from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .models import Skill
from dataclasses import dataclass




@dataclass(frozen=True)
class TTLConfig:
    cold_ttl_days: int = 90
    warm_ttl_days: int = 180
    hot_ttl_days: int = 365


DEFAULT_TTL = TTLConfig()


def evict_expired(skills: tuple, ttl: TTLConfig | None = None, now: str | None = None) -> tuple[str, ...]:
    """Return IDs of skills whose last_used exceeds frequency TTL.

    Parameters
    ----------
    skills : tuple of Skill objects
    ttl : TTLConfig, optional
    now : str, optional ISO date

    Returns
    -------
    tuple of (skill_id, frequency, days_since_last_use)
    """
    from datetime import datetime, timezone
    from dateutil import parser as dateparser
    cfg = ttl or DEFAULT_TTL
    ref = datetime.fromisoformat(now) if now else datetime.now(timezone.utc)
    expired = []
    for skill in skills:
        if not skill.last_used:
            continue
        try:
            last = dateparser.parse(skill.last_used) if "T" in skill.last_used else datetime.fromisoformat(skill.last_used)
        except (ValueError, TypeError):
            continue
        days = (ref - last).days if last.tzinfo else (ref.replace(tzinfo=None) - last).days
        if days < 0:
            days = 0
        tier_days = {"cold": cfg.cold_ttl_days, "warm": cfg.warm_ttl_days, "hot": cfg.hot_ttl_days}
        limit = tier_days.get(skill.frequency, cfg.cold_ttl_days)
        if days > limit:
            expired.append((skill.id, skill.frequency, days, limit))
    return tuple(expired)


def format_ttl_status(expired: tuple) -> str:
    """Return human-readable TTL status."""
    if not expired:
        return "No expired skills."
    lines = ["Expired skills (ID | frequency | days since use / TTL):"]
    for sid, freq, days, limit in expired:
        lines.append(f"  {sid:<28} {freq:<8} {days:>4}d / {limit}d")
    return "\n".join(lines)


class RegistryError(ValueError):
    pass


class SkillRegistry:
    def __init__(self, skills: Iterable[Skill]):
        self.skills = tuple(skills)
        self._validate()

    @classmethod
    def load(cls, path: str | Path) -> "SkillRegistry":
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(value, dict) or not isinstance(value.get("skills"), list):
            raise RegistryError("registry must contain a skills list")
        return cls(Skill.from_dict(item) for item in value["skills"])

    def _validate(self) -> None:
        ids = [skill.id for skill in self.skills]
        if len(ids) != len(set(ids)):
            raise RegistryError("skill IDs must be unique")
        for skill in self.skills:
            if skill.kind not in {"skill", "script"}:
                raise RegistryError(f"unsupported kind: {skill.kind}")
            if skill.layer not in {"system", "domain", "project"}:
                raise RegistryError(f"unsupported layer: {skill.layer}")
            if skill.frequency not in {"hot", "warm", "cold"}:
                raise RegistryError(f"unsupported frequency: {skill.frequency}")

    def get(self, skill_id: str) -> Skill:
        for skill in self.skills:
            if skill.id == skill_id:
                return skill
        raise KeyError(skill_id)

    def active(self) -> tuple[Skill, ...]:
        return tuple(skill for skill in self.skills if skill.status not in {"deprecated", "archived"})

    def matching(self, task: str) -> tuple[tuple[Skill, int], ...]:
        tokens = set(task.lower().split())
        matches = []
        for skill in self.active():
            score = sum(1 for trigger in skill.triggers if trigger in tokens or trigger in task.lower())
            if score:
                matches.append((skill, score))
        return tuple(sorted(matches, key=lambda item: (-item[1], item[0].id)))
