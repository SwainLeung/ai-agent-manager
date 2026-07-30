"""Analyze usage patterns and suggest candidate Skill descriptors."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def suggest_skills(
    usage_entries: list[dict[str, Any]],
    feedback_events: list[dict[str, Any]],
    *,
    min_calls: int = 3,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Generate candidate Skill descriptors from execution history.

    Parameters
    ----------
    usage_entries : list[dict]
        Entries with keys: skill_id, status, timestamp.
        Typically from UsageLedger entries.
    feedback_events : list[dict]
        Events with keys: event_type, subject, note.
        Typically from FeedbackStore events.
    min_calls : int
        Minimum calls to consider a candidate.
    top_k : int
        Maximum candidates to return.

    Returns
    -------
    list of candidate Skill descriptor dicts with:
        id, layer, kind, frequency, version, status,
        triggers, description, calls, successes, source
    """
    # Group usage by skill_id/operation
    op_counts: dict[str, dict[str, Any]] = {}
    for entry in usage_entries:
        sid = str(entry.get("skill_id", ""))
        status = str(entry.get("status", ""))
        if not sid:
            continue
        if sid not in op_counts:
            op_counts[sid] = {"calls": 0, "successes": 0}
        op_counts[sid]["calls"] += 1
        if status == "completed":
            op_counts[sid]["successes"] += 1

    # Derive operation name from skill_id
    operations = {}
    for sid, stats in op_counts.items():
        if stats["calls"] < min_calls:
            continue
        # Extract operation from skill_id (e.g. "domain.report-synthesis" -> "report")
        parts = sid.rsplit(".", 1)
        operation = parts[-1] if len(parts) > 1 else sid
        triggers = [operation]
        # Add feedback subjects as potential triggers
        for ev in feedback_events:
            sub = str(ev.get("subject", "")).lower().strip()
            if sub and sub not in triggers:
                triggers.append(sub)
        ops_key = operation.lower()
        if ops_key not in operations:
            operations[ops_key] = {
                "operation": operation,
                "triggers": triggers[:5],
                "total_calls": 0,
                "total_successes": 0,
            }
        operations[ops_key]["total_calls"] += stats["calls"]
        operations[ops_key]["total_successes"] += stats["successes"]

    # Build candidates
    candidates = []
    for ops_key, data in sorted(operations.items(), key=lambda x: x[1]["total_calls"], reverse=True)[:top_k]:
        rate = data["total_successes"] / data["total_calls"] if data["total_calls"] else 0.0
        candidates.append({
            "id": f"project.{ops_key}",
            "layer": "project",
            "kind": "skill",
            "frequency": "cold",
            "version": "0.1.0",
            "status": "candidate",
            "triggers": data["triggers"],
            "description": f"Auto-suggested skill for {data['operation']} operations",
            "calls": data["total_calls"],
            "successes": data["total_successes"],
            "success_rate": round(rate, 3),
            "source": "skill-generator",
        })

    return candidates
