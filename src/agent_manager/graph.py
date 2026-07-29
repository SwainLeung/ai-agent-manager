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
        node_ids = set(ids)
        if self.start not in node_ids:
            errors.append(f"start node does not exist: {self.start}")
        for edge in self.edges:
            if edge.get("from") not in node_ids:
                errors.append(f"edge source does not exist: {edge.get('from')}")
            if edge.get("to") not in node_ids:
                errors.append(f"edge target does not exist: {edge.get('to')}")
        return errors

    def assert_valid(self) -> None:
        errors = self.validate()
        if errors:
            raise GraphValidationError("; ".join(errors))
