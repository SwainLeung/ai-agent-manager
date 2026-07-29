from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .models import Skill


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
