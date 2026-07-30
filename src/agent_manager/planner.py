"""Natural-language graph planner: LLM -> JSON GraphPlan."""

from __future__ import annotations

import json
import re
from typing import Any

from .graph import GraphDefinition, GraphValidationError
from .provider import ProviderAdapter


def plan_from_task(
    task: str,
    provider: ProviderAdapter,
    *,
    model: str = "mock",
    graph_id: str = "dynamic-plan",
    max_nodes: int = 10,
) -> GraphDefinition:
    """Generate a GraphDefinition from a natural-language task description.

    Parameters
    ----------
    task : str
        Task description (e.g. "summarize a report").
    provider : ProviderAdapter
        Provider adapter for LLM call.
    model : str
        Model identifier.
    graph_id : str
        Graph identifier for the result.
    max_nodes : int
        Safety limit on generated nodes.

    Returns
    -------
    GraphDefinition
        Validated graph definition ready for execution.

    Raises
    ------
    GraphValidationError
        If the generated graph fails validation.
    """
    prompt = f"""Generate a JSON GraphDefinition for the task: "{task}"

The graph must follow this JSON schema:
{{
  "start": "first_node_id",
  "nodes": [
    {{"id": "node1", "kind": "decision|script|skill|checkpoint", "label": "human readable name"}}
  ],
  "edges": [
    {{"from": "node1", "to": "node2", "when": "success|error|ambiguous|structured|default"}}
  ]
}}

Rules:
- At least 2 nodes, at most {max_nodes}.
- "start" must reference a node that exists.
- Every "from" and "to" in edges must reference existing nodes.
- Use "decision" for routing, "script" for deterministic work, "skill" for LLM work, "checkpoint" for output validation.
- Return ONLY valid JSON, no explanation.

Example for "summarize a report":
{{"start": "route", "nodes": [{{"id": "route", "kind": "decision", "label": "Route task"}}, {{"id": "collect", "kind": "script", "label": "Collect inputs"}}, {{"id": "synthesize", "kind": "skill", "label": "Synthesize"}}, {{"id": "finish", "kind": "checkpoint", "label": "Validate"}}], "edges": [{{"from": "route", "to": "collect", "when": "structured"}}, {{"from": "route", "to": "synthesize", "when": "ambiguous"}}, {{"from": "collect", "to": "finish", "when": "success"}}, {{"from": "synthesize", "to": "finish", "when": "success"}}, {{"from": "collect", "to": "synthesize", "when": "error"}}]}}
"""
    response = provider.complete(prompt, model=model)
    text = response.content if hasattr(response, "content") else str(response)
    # Extract JSON from response
    json_match = re.search(r"\{[\s\S]*?\}", text)
    if not json_match:
        raise GraphValidationError("no JSON found in provider response")
    raw = json_match.group()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise GraphValidationError(f"invalid JSON: {exc}") from exc
    if "nodes" not in data or "edges" not in data:
        raise GraphValidationError("generated graph missing nodes or edges")
    if not isinstance(data["start"], str) or not data["start"].strip():
        raise GraphValidationError("generated graph has invalid start")
    graph = GraphDefinition(
        graph_id=graph_id,
        version="0.1.0",
        start=str(data["start"]),
        nodes=tuple(data["nodes"]),
        edges=tuple(data["edges"]),
    )
    errors = graph.validate()
    if errors:
        raise GraphValidationError(f"generated graph invalid: {'; '.join(errors)}")
    return graph
