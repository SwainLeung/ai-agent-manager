"""Execution trace analyzer: aggregate failure data from trace events."""

from __future__ import annotations

from typing import Any

from .recorder import ExecutionRecorder


def analyze_trace(recorder: ExecutionRecorder) -> dict[str, Any]:
    """Analyze a single trace and return aggregated failure report.

    Parameters
    ----------
    recorder : ExecutionRecorder
        Loaded trace recorder.

    Returns
    -------
    dict with keys: run_id, graph_id, total_nodes, success_count,
    failure_count, node_stats (list per node), top_errors.
    """
    events = recorder.events
    node_stats: dict[str, dict[str, Any]] = {}
    error_messages: dict[str, int] = {}
    for event in events:
        nid = event.node_id
        if nid is None:
            continue
        if nid not in node_stats:
            node_stats[nid] = {"node_id": nid, "attempts": 0, "failures": 0, "errors": []}
        if event.event in ("node_started", "node_finished", "node_failed"):
            node_stats[nid]["attempts"] += 1
        if event.event == "node_failed":
            node_stats[nid]["failures"] += 1
            err = (event.data or {}).get("error", "unknown")
            node_stats[nid]["errors"].append(str(err))
            error_messages[str(err)] = error_messages.get(str(err), 0) + 1
    total_nodes = len(node_stats)
    success_count = sum(1 for ns in node_stats.values() if ns["failures"] == 0)
    failure_count = total_nodes - success_count
    top_errors = sorted(error_messages.items(), key=lambda x: x[1], reverse=True)[:10]
    return {
        "run_id": recorder.run_id,
        "graph_id": recorder.graph_id,
        "total_nodes": total_nodes,
        "success_count": success_count,
        "failure_count": failure_count,
        "node_stats": sorted(node_stats.values(), key=lambda x: x["failures"], reverse=True),
        "top_errors": [{"error": e, "count": c} for e, c in top_errors],
    }
