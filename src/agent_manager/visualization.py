"""Trace visualizer: convert execution traces to DOT and Mermaid graph formats."""

from __future__ import annotations

from typing import Any

from .recorder import TraceEvent


# ── Node/edge extraction from trace events ──────────────────────────────

_NODE_KIND_SHAPES = {
    "decision": "diamond",
    "script": "box",
    "skill": "box",
    "checkpoint": "hexagon",
}


def _extract_nodes_and_edges(
    events: list[TraceEvent],
    graph_kinds: dict[str, str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Extract nodes and edges from a list of TraceEvents.

    Parameters
    ----------
    events : list[TraceEvent]
        Sorted chronologically.
    graph_kinds : dict[str, str] | None
        Optional mapping from node_id → kind (decision/script/skill/checkpoint)
        providing richer shape information.

    Returns
    -------
    nodes : list[dict]
        Each dict: {"id": str, "kind": str | None, "failed": bool, "label": str}
    edges : list[dict]
        Each dict: {"from": str, "to": str, "label": str | None}
    """
    node_set: dict[str, dict[str, Any]] = {}
    edges_raw: list[dict[str, Any]] = []
    prev_node: str | None = None
    prev_is_failure = False

    for event in events:
        node_id = event.node_id
        if node_id is None:
            continue

        # Register node
        if node_id not in node_set:
            kind = (graph_kinds or {}).get(node_id)
            node_set[node_id] = {
                "id": node_id,
                "kind": kind,
                "failed": False,
                "label": node_id.replace("_", " ").title(),
            }

        if event.event == "node_started":
            # Build edge from prev finished node to this started node
            if prev_node is not None and prev_node != node_id:
                edge_label = None
                if prev_is_failure:
                    edge_label = "error"
                edges_raw.append({
                    "from": prev_node,
                    "to": node_id,
                    "label": edge_label,
                })
            prev_node = node_id
            prev_is_failure = False

        elif event.event == "node_failed":
            if node_id in node_set:
                node_set[node_id]["failed"] = True
            # Mark the incoming edge as error
            if edges_raw:
                edges_raw[-1]["label"] = "error"
            prev_is_failure = True

        elif event.event == "node_finished":
            signal = (event.data or {}).get("signal")
            # Update the last edge label with the signal if available
            if signal and edges_raw:
                edges_raw[-1]["label"] = str(signal)
            prev_is_failure = False

    nodes = list(node_set.values())
    return nodes, edges_raw


# ── DOT renderer ────────────────────────────────────────────────────────


def _node_attrs(node: dict[str, Any]) -> str:
    kind = node.get("kind")
    shape = _NODE_KIND_SHAPES.get(kind, "box")
    attrs = [f'shape={shape}', f'label="{node["label"]}"']
    if node.get("failed"):
        attrs.append('style="filled"')
        attrs.append('fillcolor="#ffcccc"')
        attrs.append('color="#cc0000"')
        attrs.append('fontcolor="#cc0000"')
    else:
        attrs.append('style="filled"')
        attrs.append('fillcolor="#e1f5fe"')
        attrs.append('color="#0288d1"')
    return " [" + ", ".join(attrs) + "]"


def _edge_label(label: str | None) -> str:
    if label:
        safe = label.replace('"', '\\"')
        return f' [label="{safe}"]'
    return ""


def trace_to_dot(
    events: list[TraceEvent],
    graph_kinds: dict[str, str] | None = None,
    *,
    graph_id: str = "trace",
) -> str:
    """Render execution trace events as DOT (Graphviz) source.

    Parameters
    ----------
    events : list[TraceEvent]
        Chronological trace events.
    graph_kinds : dict[str, str] | None
        Optional mapping node_id → kind for shape hints.
    graph_id : str
        DOT graph name (default "trace").

    Returns
    -------
    str
        Valid DOT source text suitable for Graphviz or `dot` CLI.
    """
    nodes, edges = _extract_nodes_and_edges(events, graph_kinds)
    lines = [
        f"digraph {graph_id} {{",
        '  rankdir=LR;',
        '  node [fontname="sans-serif"];',
        '  edge [fontname="sans-serif"];',
    ]
    for node in nodes:
        lines.append(f'  "{node["id"]}"{_node_attrs(node)};')
    for edge in edges:
        lines.append(f'  "{edge["from"]}" -> "{edge["to"]}"{_edge_label(edge["label"])};')
    lines.append("}")
    return "\n".join(lines) + "\n"


# ── Mermaid renderer ────────────────────────────────────────────────────


def trace_to_mermaid(
    events: list[TraceEvent],
    graph_kinds: dict[str, str] | None = None,
) -> str:
    """Render execution trace events as Mermaid flow-chart source.

    Parameters
    ----------
    events : list[TraceEvent]
        Chronological trace events.
    graph_kinds : dict[str, str] | None
        Optional mapping node_id → kind for shape hints.

    Returns
    -------
    str
        Mermaid ``graph LR`` diagram source.
    """
    nodes, edges = _extract_nodes_and_edges(events, graph_kinds)
    lines = ["graph LR"]

    # Node declarations with shapes
    for node in nodes:
        nid = node["id"]
        safe_id = nid.replace("-", "_").replace(" ", "_")
        label = node["label"]
        if node.get("failed"):
            style = "fill:#ffcccc,stroke:#cc0000"
            lines.append(f'  {safe_id}["{label}"]:::{safe_id}_fail')
            lines.append(f'  classDef {safe_id}_fail {style}')
        else:
            lines.append(f'  {safe_id}["{label}"]')

    # Edges
    for edge in edges:
        src = edge["from"].replace("-", "_").replace(" ", "_")
        dst = edge["to"].replace("-", "_").replace(" ", "_")
        label = edge.get("label")
        if edge.get("label") == "error":
            lines.append(f'  {src} -.->|"error"| {dst}')
        elif label:
            lines.append(f'  {src} -->|"{label}"| {dst}')
        else:
            lines.append(f'  {src} --> {dst}')

    return "\n".join(lines) + "\n"


# ── CLI convenience ─────────────────────────────────────────────────────


def render(
    events: list[TraceEvent],
    fmt: str,
    graph_kinds: dict[str, str] | None = None,
    *,
    graph_id: str = "trace",
) -> str:
    """Render trace to the requested format.

    Parameters
    ----------
    events : list[TraceEvent]
    fmt : str
        ``"dot"`` or ``"mermaid"``.
    graph_kinds : dict[str, str] | None
    graph_id : str

    Returns
    -------
    str
        Rendered graph source.
    """
    if fmt == "dot":
        return trace_to_dot(events, graph_kinds, graph_id=graph_id)
    if fmt == "mermaid":
        return trace_to_mermaid(events, graph_kinds)
    msg = f"unsupported format: {fmt!r} (choose 'dot' or 'mermaid')"
    raise ValueError(msg)
