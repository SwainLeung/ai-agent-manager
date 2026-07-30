from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path
from typing import Any, Iterable, Mapping


RULE_SCOPES = {"profile", "project"}
RULE_DECISIONS = {"approve", "reject"}


@dataclass(frozen=True)
class GovernedRule:
    """A reviewed, reversible rule that may be exposed to a host plan."""

    rule_id: str
    scope: str
    subject: str
    signal: str
    action: str
    evidence_count: int
    confidence: float
    status: str = "candidate"
    injection: str = "disabled"
    review_note: str = ""
    revision: int = 1

    @classmethod
    def from_candidate(cls, candidate: Mapping[str, Any]) -> "GovernedRule":
        rule_id = str(candidate.get("rule_id", "")).strip()
        if not rule_id:
            raise ValueError("rule candidate requires rule_id")
        scope = str(candidate.get("scope", ""))
        if scope not in RULE_SCOPES:
            raise ValueError(f"unsupported rule scope: {scope}")
        confidence = float(candidate.get("confidence", 0.0))
        if not 0 <= confidence <= 1:
            raise ValueError("rule confidence must be between 0 and 1")
        return cls(
            rule_id=rule_id,
            scope=scope,
            subject=str(candidate.get("subject", "")),
            signal=str(candidate.get("signal", "")),
            action=str(candidate.get("action", "")),
            evidence_count=int(candidate.get("evidence_count", 0)),
            confidence=confidence,
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "GovernedRule":
        item = cls.from_candidate(value)
        status = str(value.get("status", item.status))
        injection = str(value.get("injection", item.injection))
        if status not in {"candidate", "approved", "rejected", "revoked"}:
            raise ValueError(f"unsupported rule status: {status}")
        if injection not in {"enabled", "disabled"}:
            raise ValueError(f"unsupported rule injection state: {injection}")
        if status != "approved" and injection == "enabled":
            raise ValueError("only approved rules may be enabled")
        return replace(
            item,
            status=status,
            injection=injection,
            review_note=str(value.get("review_note", "")),
            revision=max(1, int(value.get("revision", 1))),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RuleStore:
    """Persist candidate and reviewed Profile/Project rules outside Git."""

    def __init__(self, rules: Iterable[GovernedRule] | None = None):
        self.rules = list(rules or [])
        self._validate_unique_ids()

    def _validate_unique_ids(self) -> None:
        ids = [rule.rule_id for rule in self.rules]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate rule_id in rule store")

    def upsert_candidates(self, candidates: Iterable[Mapping[str, Any]]) -> list[GovernedRule]:
        by_id = {rule.rule_id: index for index, rule in enumerate(self.rules)}
        for candidate in candidates:
            incoming = GovernedRule.from_candidate(candidate)
            index = by_id.get(incoming.rule_id)
            if index is None:
                by_id[incoming.rule_id] = len(self.rules)
                self.rules.append(incoming)
                continue
            current = self.rules[index]
            updated = replace(
                current,
                scope=incoming.scope,
                subject=incoming.subject,
                signal=incoming.signal,
                action=incoming.action,
                evidence_count=incoming.evidence_count,
                confidence=incoming.confidence,
            )
            self.rules[index] = replace(
                updated,
                revision=current.revision + 1 if updated != current else current.revision,
            )
        return list(self.rules)

    def get(self, rule_id: str) -> GovernedRule:
        for rule in self.rules:
            if rule.rule_id == rule_id:
                return rule
        raise KeyError(f"unknown rule: {rule_id}")

    def review(self, rule_id: str, decision: str, note: str) -> GovernedRule:
        if decision not in RULE_DECISIONS:
            raise ValueError(f"unsupported rule decision: {decision}")
        if not note.strip():
            raise ValueError("rule review note is required")
        current = self.get(rule_id)
        updated = replace(
            current,
            status="approved" if decision == "approve" else "rejected",
            injection="enabled" if decision == "approve" else "disabled",
            review_note=note.strip(),
            revision=current.revision + 1,
        )
        self.rules[self.rules.index(current)] = updated
        return updated

    def revoke(self, rule_id: str, note: str) -> GovernedRule:
        if not note.strip():
            raise ValueError("rule revoke note is required")
        current = self.get(rule_id)
        updated = replace(
            current,
            status="revoked",
            injection="disabled",
            review_note=note.strip(),
            revision=current.revision + 1,
        )
        self.rules[self.rules.index(current)] = updated
        return updated

    def active(self, scope: str | None = None) -> list[GovernedRule]:
        if scope is not None and scope not in RULE_SCOPES:
            raise ValueError(f"unsupported rule scope: {scope}")
        return [
            rule
            for rule in self.rules
            if rule.status == "approved"
            and rule.injection == "enabled"
            and (scope is None or rule.scope == scope)
        ]

    def to_dict(self) -> list[dict[str, Any]]:
        return [rule.to_dict() for rule in self.rules]

    def save(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: str | Path) -> "RuleStore":
        source = Path(path)
        if not source.exists():
            return cls()
        payload = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("rule store must contain a list")
        return cls(GovernedRule.from_dict(item) for item in payload)


def compact_rules(active_rules: list) -> dict:
    """Deduplicate and prune expired rules.

    Parameters
    ----------
    active_rules : list of dict with keys: scope, subject, signal, confidence, note, created

    Returns
    -------
    dict with: merged (list), contradictions (list), archived (list), summary
    """
    from collections import defaultdict
    groups = defaultdict(list)
    for rule in active_rules:
        key = (str(rule.get("scope", "")), str(rule.get("subject", "")), str(rule.get("signal", "")))
        groups[key].append(rule)

    merged = []
    contradictions = []
    archived = []

    for key, group in groups.items():
        scope, subject, signal = key
        if len(group) > 1:
            # Merge: keep highest confidence
            best = max(group, key=lambda r: float(r.get("confidence", 0)))
            merged.append({
                "scope": scope, "subject": subject, "signal": signal,
                "confidence": best["confidence"], "note": best.get("note", ""),
                "merged_from": len(group),
            })
        else:
            merged.append(dict(group[0]))

        # Contradiction: same scope+subject but opposite signal
        for g in group:
            g_signal = str(g.get("signal", ""))
            if g_signal != signal and (scope + subject) in [str(k[0]) + str(k[1]) for k in groups]:
                if g_signal not in ("correction", "approval"):
                    contradictions.append({
                        "scope": scope, "subject": subject,
                        "signal_a": signal, "signal_b": g_signal,
                    })

    # Archive rules with confidence < 0.3 (expired)
    archived = [r for r in merged if float(r.get("confidence", 0)) < 0.3]
    merged = [r for r in merged if float(r.get("confidence", 0)) >= 0.3]

    return {
        "merged": merged,
        "contradictions": contradictions,
        "archived": archived,
        "summary": {
            "input_count": len(active_rules),
            "merged_count": len(merged),
            "contradiction_count": len(contradictions),
            "archived_count": len(archived),
        }
    }
