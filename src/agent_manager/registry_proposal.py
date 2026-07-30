from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


class RegistryProposalError(ValueError):
    pass


@dataclass(frozen=True)
class RegistryChangeProposal:
    schema_version: int
    operation: str
    target_id: str
    registry_path: str
    preview_path: str
    descriptor: dict[str, Any]
    suggestions: tuple[str, ...]
    before_sha256: str
    after_sha256: str
    status: str = "proposed"
    approval_note: str | None = None
    backup_path: str | None = None
    applied_sha256: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def load(cls, path: str | Path) -> "RegistryChangeProposal":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(**payload)

    def save(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class RegistryChangeWorkflow:
    """Propose and explicitly approve Registry changes through a temp preview."""

    def __init__(self, registry_path: str | Path):
        self.registry_path = Path(registry_path)

    @staticmethod
    def _sha256(value: bytes) -> str:
        return hashlib.sha256(value).hexdigest()

    @staticmethod
    def _payload_bytes(payload: dict[str, Any]) -> bytes:
        return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

    def _registry_bytes(self) -> bytes:
        try:
            return self.registry_path.read_bytes()
        except FileNotFoundError as exc:
            raise RegistryProposalError(f"registry file does not exist: {self.registry_path}") from exc

    def _registry_payload(self) -> dict[str, Any]:
        payload = json.loads(self._registry_bytes().decode("utf-8"))
        if not isinstance(payload, dict) or not isinstance(payload.get("skills"), list):
            raise RegistryProposalError("registry must contain a skills list")
        return payload

    @staticmethod
    def _candidate_payload(candidate: Mapping[str, Any]) -> Mapping[str, Any]:
        payload = candidate.get("candidate") if isinstance(candidate.get("candidate"), dict) else candidate
        if not isinstance(payload, Mapping):
            raise RegistryProposalError("candidate file must contain a Script candidate or solidify report")
        return payload

    def _descriptor(self, candidate: Mapping[str, Any]) -> tuple[str, str, dict[str, Any], list[str]]:
        payload = self._candidate_payload(candidate)
        target_id = str(payload.get("id", "")).strip()
        operation = str(payload.get("operation", "")).strip()
        if not target_id or not operation:
            raise RegistryProposalError("candidate requires id and operation")
        if str(payload.get("kind", "")) != "script":
            raise RegistryProposalError("only Script candidates can produce Registry proposals")
        if str(payload.get("status", "candidate")) != "candidate":
            raise RegistryProposalError("candidate must have status=candidate")
        if bool(payload.get("registry_mutated", False)):
            raise RegistryProposalError("candidate is already marked as registry-mutated")
        success_rate = float(payload.get("success_rate", 0.0))
        descriptor = {
            "id": target_id,
            "layer": str(payload.get("layer", "project")),
            "kind": "script",
            "frequency": str(payload.get("frequency", "cold")),
            "version": str(payload.get("version", "0.1.0")),
            "status": "candidate",
            "triggers": [str(item) for item in payload.get("triggers", [operation])],
            "description": str(payload.get("description", f"Deterministic Script candidate for {operation}.")),
            "calls": int(payload.get("calls", payload.get("evidence_count", 0))),
            "successes": int(payload.get("successes", payload.get("success_count", 0))),
            "last_used": payload.get("last_used"),
        }
        suggestions = [
            "Run adapter sandbox against representative fixtures before approval.",
            "Keep status=candidate until a separate activation review is complete.",
            "Review triggers, source skill provenance, and rollback ownership before writing.",
        ]
        if success_rate < 1:
            suggestions.append("Investigate replay failures because the candidate success rate is below 1.0.")
        if not payload.get("source_skill_id"):
            suggestions.append("Add source_skill_id provenance before approving this candidate.")
        return f"solidify:{target_id}", target_id, descriptor, suggestions

    def propose(
        self,
        candidate: Mapping[str, Any],
        proposal_path: str | Path,
        *,
        preview_path: str | Path | None = None,
    ) -> RegistryChangeProposal:
        operation, target_id, descriptor, suggestions = self._descriptor(candidate)
        payload = self._registry_payload()
        existing = next((skill for skill in payload["skills"] if skill.get("id") == target_id), None)
        if existing is not None:
            raise RegistryProposalError(f"registry ID conflict: {target_id}")
        before = self._registry_bytes()
        next_payload = {**payload, "skills": [*payload["skills"], descriptor]}
        after = self._payload_bytes(next_payload)
        proposal_file = Path(proposal_path)
        preview_file = Path(preview_path) if preview_path else proposal_file.with_suffix(".preview.json")
        preview_file.parent.mkdir(parents=True, exist_ok=True)
        preview_file.write_bytes(after)
        proposal = RegistryChangeProposal(
            schema_version=1,
            operation=operation,
            target_id=target_id,
            registry_path=str(self.registry_path),
            preview_path=str(preview_file),
            descriptor=descriptor,
            suggestions=tuple(suggestions),
            before_sha256=self._sha256(before),
            after_sha256=self._sha256(after),
        )
        proposal.save(proposal_file)
        return proposal

    def approve(self, proposal_path: str | Path, note: str) -> RegistryChangeProposal:
        path = Path(proposal_path)
        proposal = RegistryChangeProposal.load(path)
        if proposal.status != "proposed":
            raise RegistryProposalError(f"proposal is not awaiting approval: {proposal.status}")
        if not note.strip():
            raise RegistryProposalError("approval note is required")
        if self._sha256(self._registry_bytes()) != proposal.before_sha256:
            raise RegistryProposalError("registry changed after proposal was created")
        approved = RegistryChangeProposal(**{**proposal.to_dict(), "status": "approved", "approval_note": note.strip()})
        approved.save(path)
        return approved

    def apply(self, proposal_path: str | Path, *, write: bool = False) -> dict[str, Any]:
        path = Path(proposal_path)
        proposal = RegistryChangeProposal.load(path)
        if proposal.status == "applied":
            return {"proposal": proposal.to_dict(), "registry_mutated": False, "mode": "already-applied"}
        if proposal.status != "approved":
            raise RegistryProposalError(f"proposal is not approved: {proposal.status}")
        current = self._registry_bytes()
        if self._sha256(current) != proposal.before_sha256:
            raise RegistryProposalError("registry changed after proposal approval")
        if not write:
            return {"proposal": proposal.to_dict(), "registry_mutated": False, "mode": "dry-run"}
        preview = Path(proposal.preview_path)
        if not preview.exists() or self._sha256(preview.read_bytes()) != proposal.after_sha256:
            raise RegistryProposalError("temporary preview is missing or has drifted")
        backup = path.with_suffix(path.suffix + ".registry.backup")
        backup.write_bytes(current)
        self.registry_path.write_bytes(preview.read_bytes())
        applied = RegistryChangeProposal(**{**proposal.to_dict(), "status": "applied", "backup_path": str(backup), "applied_sha256": proposal.after_sha256})
        applied.save(path)
        return {"proposal": applied.to_dict(), "registry_mutated": True, "mode": "explicit-write"}

    def rollback(self, proposal_path: str | Path, *, write: bool = False) -> dict[str, Any]:
        path = Path(proposal_path)
        proposal = RegistryChangeProposal.load(path)
        if proposal.status != "applied" or not proposal.backup_path:
            raise RegistryProposalError("only an applied proposal with a backup can be rolled back")
        current = self._registry_bytes()
        if self._sha256(current) != (proposal.applied_sha256 or proposal.after_sha256):
            raise RegistryProposalError("registry changed after apply; refusing rollback")
        backup = Path(proposal.backup_path)
        if not backup.exists():
            raise RegistryProposalError(f"rollback backup does not exist: {backup}")
        if not write:
            return {"proposal": proposal.to_dict(), "registry_mutated": False, "mode": "dry-run-rollback"}
        self.registry_path.write_bytes(backup.read_bytes())
        rolled_back = RegistryChangeProposal(**{**proposal.to_dict(), "status": "rolled_back"})
        rolled_back.save(path)
        return {"proposal": rolled_back.to_dict(), "registry_mutated": True, "mode": "explicit-rollback"}
