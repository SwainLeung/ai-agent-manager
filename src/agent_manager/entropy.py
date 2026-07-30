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


def slim_report(findings: list[dict]) -> dict:
    """Categorize entropy audit findings into a structured slim report.

    Parameters
    ----------
    findings : list[dict]
        Output of ``audit()``.

    Returns
    -------
    dict with keys: duplicate_count, low_success_count, stall_count,
    total_findings, categories (list per category).
    """
    dup = [f for f in findings if f.get("code") == "duplicate-signature"]
    low = [f for f in findings if f.get("code") == "low-success"]
    stall = [f for f in findings if f.get("code") == "lifecycle-stall"]
    other = [f for f in findings if f.get("code") not in ("duplicate-signature", "low-success", "lifecycle-stall")]
    report = {
        "duplicate_count": len(dup),
        "low_success_count": len(low),
        "stall_count": len(stall),
        "other_count": len(other),
        "total_findings": len(findings),
        "categories": {
            "duplicate": [{"subject": f.get("subject", ""), "message": f.get("message", "")} for f in dup],
            "low_success": [{"subject": f.get("subject", ""), "message": f.get("message", "")} for f in low],
            "stalled": [{"subject": f.get("subject", ""), "message": f.get("message", "")} for f in stall],
            "other": [{"subject": f.get("subject", ""), "message": f.get("message", "")} for f in other],
        },
    }
    return report


def print_slim_report(report: dict) -> str:
    """Return human-readable slim report string."""
    lines = [
        "=== Slim Report ===",
        f"  Duplicate signatures:  {report['duplicate_count']}",
        f"  Low success rate:      {report['low_success_count']}",
        f"  Lifecycle stalled:     {report['stall_count']}",
        f"  Other findings:        {report['other_count']}",
        f"  ─────────────────────",
        f"  Total findings:        {report['total_findings']}",
    ]
    return "\n".join(lines) + "\n"
