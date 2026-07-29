from __future__ import annotations

from dataclasses import dataclass

from .models import Skill


@dataclass(frozen=True)
class EntropyFinding:
    code: str
    subject: str
    message: str


def audit(skills: list[Skill]) -> list[EntropyFinding]:
    findings: list[EntropyFinding] = []
    signatures: dict[tuple[str, tuple[str, ...]], list[str]] = {}
    for skill in skills:
        signature = (skill.kind, tuple(sorted(skill.triggers)))
        signatures.setdefault(signature, []).append(skill.id)
        if skill.status == "experimental" and skill.calls >= 20:
            findings.append(EntropyFinding("lifecycle-stall", skill.id, "experimental skill has substantial usage"))
        if skill.calls >= 3 and skill.success_rate < 0.5:
            findings.append(EntropyFinding("low-success", skill.id, "success rate is below 50 percent"))
    for ids in signatures.values():
        if len(ids) > 1:
            findings.append(EntropyFinding("duplicate-signature", ",".join(ids), "skills share the same kind and triggers"))
    return findings
