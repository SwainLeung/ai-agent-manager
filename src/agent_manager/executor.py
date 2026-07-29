from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Callable, Mapping

from .decision import DecisionMatrix, ExecutionProposal


UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
ScriptHandler = Callable[[Mapping[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class ExecutionRecord:
    subject_id: str
    operation: str
    kind: str
    status: str
    gate: str
    output: dict[str, Any] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _snapshot_hash(entity: Mapping[str, Any]) -> dict[str, Any]:
    content = entity.get("content")
    if content is None:
        return {"verified": None, "reason": "content-not-provided"}
    digest = hashlib.sha256(str(content).encode("utf-8")).hexdigest().upper()
    expected = entity.get("content_hash")
    return {"sha256": digest, "expected": expected, "match": expected is None or digest == str(expected).upper()}


def _frontmatter_validate(entity: Mapping[str, Any]) -> dict[str, Any]:
    required = tuple(entity.get("required_fields", ("entity_id", "title", "source_id")))
    missing = [field for field in required if not entity.get(field)]
    return {"valid": not missing, "missing": missing}


def _duplicate_key(entity: Mapping[str, Any]) -> dict[str, Any]:
    value = str(entity.get("title", "")).strip().lower()
    key = re.sub(r"[^\w\u4e00-\u9fff]+", "", value)
    return {"duplicate_key": key}


def _link_extract(entity: Mapping[str, Any]) -> dict[str, Any]:
    content = str(entity.get("content", ""))
    links = sorted({item.lower() for item in UUID_RE.findall(content)})
    return {"linked_source_ids": links, "count": len(links)}


def _category_count(entity: Mapping[str, Any]) -> dict[str, Any]:
    return {"domain": entity.get("domain"), "entity_type": entity.get("entity_type"), "count": 1}


def _idempotency_check(entity: Mapping[str, Any]) -> dict[str, Any]:
    source_id = entity.get("source_id") or entity.get("entity_id")
    content_hash = entity.get("content_hash")
    return {"idempotency_key": f"{source_id}:{content_hash}", "stable": bool(source_id and content_hash)}


DEFAULT_SCRIPT_HANDLERS: dict[str, ScriptHandler] = {
    "snapshot_hash": _snapshot_hash,
    "frontmatter_validate": _frontmatter_validate,
    "duplicate_key": _duplicate_key,
    "link_extract": _link_extract,
    "category_count": _category_count,
    "idempotency_check": _idempotency_check,
}


class ProposalExecutor:
    """Execute only Script proposals; leave Skill and human gates pending."""

    def __init__(self, *, matrix: DecisionMatrix | None = None, handlers: Mapping[str, ScriptHandler] | None = None):
        self.matrix = matrix or DecisionMatrix()
        self.handlers = dict(DEFAULT_SCRIPT_HANDLERS)
        self.handlers.update(handlers or {})

    def execute(self, entity: Mapping[str, Any], proposal: ExecutionProposal) -> ExecutionRecord:
        if proposal.kind != "script":
            return ExecutionRecord(proposal.subject_id, proposal.operation, proposal.kind, "pending", proposal.gate)
        handler = self.handlers.get(proposal.operation)
        if handler is None:
            return ExecutionRecord(proposal.subject_id, proposal.operation, proposal.kind, "failed", proposal.gate, error="no-script-handler")
        try:
            output = handler(entity)
            status = "completed" if output.get("valid", True) and output.get("match", True) else "failed"
            return ExecutionRecord(proposal.subject_id, proposal.operation, proposal.kind, status, proposal.gate, output=output)
        except Exception as exc:  # pragma: no cover - defensive execution boundary
            return ExecutionRecord(proposal.subject_id, proposal.operation, proposal.kind, "failed", proposal.gate, error=f"{type(exc).__name__}: {exc}")

    def execute_entities(
        self,
        entities: list[Mapping[str, Any]],
        *,
        checkpoint: str | Path | None = None,
        max_items: int | None = None,
    ) -> dict[str, Any]:
        plan = self.matrix.decide_many(entities)
        proposals = [ExecutionProposal(**item) for item in plan["proposals"]]
        entity_by_id = {str(entity.get("entity_id") or entity.get("source_id")): entity for entity in entities}
        checkpoint_path = Path(checkpoint) if checkpoint else None
        state = {"schema_version": 1, "status": "running", "next_index": 0, "records": []}
        if checkpoint_path and checkpoint_path.exists():
            state = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            if state.get("proposal_count") not in {None, len(proposals)}:
                raise ValueError("checkpoint proposal count does not match current plan")
        records = [ExecutionRecord(**item) for item in state.get("records", [])]
        index = int(state.get("next_index", len(records)))
        limit = len(proposals) if max_items is None else min(len(proposals), index + max_items)
        while index < limit:
            proposal = proposals[index]
            entity = entity_by_id.get(proposal.subject_id, {})
            records.append(self.execute(entity, proposal))
            index += 1
            if checkpoint_path:
                checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
                checkpoint_path.write_text(json.dumps({"schema_version": 1, "status": "running", "proposal_count": len(proposals), "next_index": index, "records": [item.to_dict() for item in records]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        status = "completed" if index >= len(proposals) else "paused"
        if checkpoint_path:
            checkpoint_path.write_text(json.dumps({"schema_version": 1, "status": status, "proposal_count": len(proposals), "next_index": index, "records": [item.to_dict() for item in records]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        status_counts = {status: sum(1 for item in records if item.status == status) for status in ("completed", "pending", "failed")}
        kind_counts = {kind: sum(1 for item in records if item.kind == kind) for kind in ("script", "skill", "human_review")}
        return {
            "status": status,
            "entity_count": len(entities),
            "proposal_count": len(proposals),
            "processed": len(records),
            "status_counts": status_counts,
            "kind_counts": kind_counts,
            "human_gate_required": kind_counts["human_review"] > 0,
            "checkpoint": str(checkpoint_path) if checkpoint_path else None,
            "records": [item.to_dict() for item in records],
        }
