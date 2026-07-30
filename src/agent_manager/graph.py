from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


class GraphValidationError(ValueError):
    pass


@dataclass(frozen=True)
class GraphDefinition:
    graph_id: str
    version: str
    start: str
    nodes: tuple[dict, ...]
    edges: tuple[dict, ...]

    @classmethod
    def load(cls, path: str | Path) -> "GraphDefinition":
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(str(value["id"]), str(value.get("version", "0.1.0")), str(value["start"]), tuple(value["nodes"]), tuple(value["edges"]))

    def validate(self) -> list[str]:
        errors: list[str] = []
        ids = [str(node.get("id")) for node in self.nodes]
        if len(ids) != len(set(ids)):
            errors.append("node IDs must be unique")
        for node in self.nodes:
            if str(node.get("kind")) == "subgraph":
                if not str(node.get("subgraph_id", "")):
                    errors.append(f"subgraph node {node.get('id')} has no subgraph_id")
        node_ids = set(ids)
        if self.start not in node_ids:
            errors.append(f"start node does not exist: {self.start}")
        for edge in self.edges:
            if edge.get("from") not in node_ids:
                errors.append(f"edge source does not exist: {edge.get('from')}")
            if edge.get("to") not in node_ids:
                errors.append(f"edge target does not exist: {edge.get('to')}")
        return errors

    def expand(self, base_path: str | None = None) -> "GraphDefinition":
        """Return a new GraphDefinition with all subgraph nodes expanded inline.

        Parameters
        ----------
        base_path : str | None
            Directory path for resolving subgraph JSON files.
            Defaults to config/ relative to CWD.

        Returns
        -------
        GraphDefinition with subgraph nodes replaced by their content.
        """
        if not any(str(n.get("kind")) == "subgraph" for n in self.nodes):
            return self
        base = Path(base_path or "config")
        new_nodes: list[dict] = []
        new_edges: list[dict] = []
        node_map: dict[str, str] = {}  # subgraph node_id -> expanded set

        for node in self.nodes:
            if str(node.get("kind")) == "subgraph":
                sub_id = str(node.get("subgraph_id", ""))
                if not sub_id:
                    raise GraphValidationError(f"subgraph node {node.get('id')} has no subgraph_id")
                sub_path = base / sub_id
                if not sub_path.exists():
                    sub_path = sub_path.with_suffix(".json")
                if not sub_path.exists():
                    # Try resolving as known graph
                    known = str(Path(__file__).resolve().parent.parent.parent / "config" / sub_id)
                    sub_path = Path(known)
                    if not sub_path.exists():
                        sub_path = Path(known + ".json")
                if not sub_path.exists():
                    raise GraphValidationError(f"subgraph file not found: {sub_id}")
                sub_graph = GraphDefinition.load(str(sub_path))
                sub_errors = sub_graph.validate()
                if sub_errors:
                    raise GraphValidationError(f"subgraph {sub_id} validation failed: {'; '.join(sub_errors)}")
                prefix = f"{node.get('id')}."
                for sn in sub_graph.nodes:
                    mapped = dict(sn)
                    mapped["id"] = prefix + str(sn["id"])
                    new_nodes.append(mapped)
                for se in sub_graph.edges:
                    mapped = dict(se)
                    mapped["from"] = prefix + str(se["from"])
                    mapped["to"] = prefix + str(se["to"])
                    new_edges.append(mapped)
                # Map subgraph start
                node_map[str(node.get("id"))] = prefix + sub_graph.start
            else:
                new_nodes.append(dict(node))

        # Remap edges that reference the original subgraph node
        for edge in self.edges:
            src = str(edge.get("from", ""))
            dst = str(edge.get("to", ""))
            if src in node_map:
                src = node_map[src]
            if dst in node_map:
                dst = node_map[dst]
            new_edges.append({"from": src, "to": dst, **{k: v for k, v in edge.items() if k not in ("from", "to")}})

        return GraphDefinition(
            graph_id=self.graph_id,
            version=self.version,
            start=str(node_map.get(self.start, self.start)),
            nodes=tuple(new_nodes),
            edges=tuple(new_edges),
        )

    def assert_valid(self) -> None:
        errors = self.validate()
        if errors:
            raise GraphValidationError("; ".join(errors))
