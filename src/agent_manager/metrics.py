from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterable

from .models import Skill


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


@dataclass(frozen=True)
class UsageEntry:
    run_id: str
    skill_id: str
    status: str
    timestamp: str


class UsageLedger:
    """Ignored runtime usage ledger with run/skill idempotency."""

    def __init__(
        self,
        runs: dict[str, dict[str, Any]] | None = None,
        entries: Iterable[UsageEntry] | None = None,
    ):
        self.runs = dict(runs or {})
        self.entries = list(entries or [])

    @classmethod
    def load(cls, path: str | Path) -> "UsageLedger":
        source = Path(path)
        if not source.exists():
            return cls()
        payload = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("usage ledger must contain an object")
        entries = [UsageEntry(**item) for item in payload.get("entries", [])]
        runs = payload.get("runs", {})
        if not isinstance(runs, dict):
            raise ValueError("usage ledger runs must contain an object")
        return cls(runs=runs, entries=entries)

    def save(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "runs": self.runs,
            "entries": [asdict(entry) for entry in self.entries],
        }
        destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def record_run(self, run_id: str, skill_ids: Iterable[str], status: str) -> bool:
        """Record a run once and upgrade a paused run when it later completes.

        Returns ``True`` when the ledger changed. Repeated retries and repeated
        terminal observations are no-ops.
        """

        if status not in {"paused", "completed", "failed"}:
            raise ValueError(f"unsupported usage status: {status}")
        timestamp = utc_now()
        changed = False
        previous = self.runs.get(run_id)
        if previous is None:
            self.runs[run_id] = {"status": status, "timestamp": timestamp}
            changed = True
        elif previous.get("status") != "completed" and status == "completed":
            previous["status"] = status
            previous["timestamp"] = timestamp
            changed = True

        by_key = {(entry.run_id, entry.skill_id): index for index, entry in enumerate(self.entries)}
        for skill_id in sorted(set(skill_ids)):
            key = (run_id, skill_id)
            index = by_key.get(key)
            if index is None:
                self.entries.append(UsageEntry(run_id, skill_id, status, timestamp))
                by_key[key] = len(self.entries) - 1
                changed = True
            elif self.entries[index].status != "completed" and status == "completed":
                self.entries[index] = UsageEntry(run_id, skill_id, status, timestamp)
                changed = True
        return changed

    def _skill_totals(self) -> dict[str, dict[str, int]]:
        totals: dict[str, dict[str, int]] = {}
        for entry in self.entries:
            value = totals.setdefault(entry.skill_id, {"calls": 0, "successes": 0})
            value["calls"] += 1
            if entry.status == "completed":
                value["successes"] += 1
        return totals

    def project(self, skills: Iterable[Skill]) -> tuple[Skill, ...]:
        totals = self._skill_totals()
        projected = []
        for skill in skills:
            runtime = totals.get(skill.id, {"calls": 0, "successes": 0})
            projected.append(
                replace(
                    skill,
                    calls=skill.calls + runtime["calls"],
                    successes=skill.successes + runtime["successes"],
                )
            )
        return tuple(projected)

    def report(self, skills: Iterable[Skill]) -> dict[str, Any]:
        skill_list = list(skills)
        totals = self._skill_totals()
        statuses = {status: 0 for status in ("paused", "completed", "failed")}
        for run in self.runs.values():
            status = str(run.get("status", "failed"))
            statuses.setdefault(status, 0)
            statuses[status] += 1
        skill_metrics = []
        for skill in skill_list:
            runtime = totals.get(skill.id, {"calls": 0, "successes": 0})
            calls = skill.calls + runtime["calls"]
            successes = skill.successes + runtime["successes"]
            skill_metrics.append({
                "skill_id": skill.id,
                "baseline_calls": skill.calls,
                "runtime_calls": runtime["calls"],
                "calls": calls,
                "baseline_successes": skill.successes,
                "runtime_successes": runtime["successes"],
                "successes": successes,
                "success_rate": round(successes / calls, 3) if calls else 0.0,
            })
        return {
            "run_count": len(self.runs),
            "status_counts": statuses,
            "skill_metrics": skill_metrics,
            "usage_path": None,
        }
