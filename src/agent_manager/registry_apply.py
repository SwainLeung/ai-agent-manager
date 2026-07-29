from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
from typing import Any

from .promotion import PromotionLedger


class RegistryApplyError(ValueError):
    pass


@dataclass(frozen=True)
class RegistryPatch:
    operation: str
    target_id: str
    descriptor: dict[str, Any]
    registry_path: str
    registry_mutated: bool
    status: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RegistryApplier:
    """Create or explicitly apply a reviewed promotion candidate to a registry."""

    def __init__(self, registry_path: str | Path, ledger_path: str | Path):
        self.registry_path = Path(registry_path)
        self.ledger = PromotionLedger.load(ledger_path)

    def plan(self, operation: str) -> RegistryPatch:
        candidate = self.ledger.candidates.get(operation)
        if candidate is None:
            raise RegistryApplyError(f"no promotion candidate for operation: {operation}")
        if candidate.status != "approved":
            raise RegistryApplyError(f"promotion candidate is not approved: {operation} ({candidate.status})")
        payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
        skills = list(payload.get("skills", []))
        target_id = "script." + re.sub(r"[^a-z0-9]+", "-", operation.lower()).strip("-")
        existing = next((skill for skill in skills if skill.get("id") == target_id), None)
        descriptor = {
            "id": target_id,
            "layer": "project",
            "kind": "script",
            "frequency": "cold",
            "version": "0.1.0",
            "status": "candidate",
            "triggers": [operation, *operation.split("_")],
            "description": f"Deterministic handler promoted from reviewed operation {operation}.",
            "calls": candidate.evidence_count,
            "successes": candidate.success_count,
            "last_used": None,
        }
        if existing is not None:
            if existing == descriptor:
                return RegistryPatch(operation, target_id, descriptor, str(self.registry_path), False, "already-present", "identical descriptor already exists")
            raise RegistryApplyError(f"registry ID conflict: {target_id}")
        return RegistryPatch(operation, target_id, descriptor, str(self.registry_path), False, "planned", "approved candidate requires explicit apply")

    def apply(self, operation: str, *, write: bool = False) -> RegistryPatch:
        patch = self.plan(operation)
        if not write or patch.status == "already-present":
            return patch
        payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
        payload.setdefault("skills", []).append(patch.descriptor)
        tmp = self.registry_path.with_suffix(self.registry_path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(self.registry_path)
        return RegistryPatch(patch.operation, patch.target_id, patch.descriptor, patch.registry_path, True, "applied", "explicit write requested")
