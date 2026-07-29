from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
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
    manifest_path: str | None = None
    before_sha256: str | None = None
    after_sha256: str | None = None
    backup_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RegistryApplyManifest:
    """Human-reviewable transaction record for a registry mutation."""

    schema_version: int
    operation: str
    target_id: str
    registry_path: str
    descriptor: dict[str, Any]
    before_sha256: str
    after_sha256: str
    status: str = "planned"
    approval_note: str | None = None
    backup_path: str | None = None
    applied_sha256: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def load(cls, path: str | Path) -> "RegistryApplyManifest":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(**payload)

    def save(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class RegistryApplier:
    """Create or explicitly apply a reviewed promotion candidate to a registry."""

    def __init__(self, registry_path: str | Path, ledger_path: str | Path):
        self.registry_path = Path(registry_path)
        self.ledger = PromotionLedger.load(ledger_path)

    @staticmethod
    def _sha256_bytes(value: bytes) -> str:
        return hashlib.sha256(value).hexdigest()

    def _registry_bytes(self) -> bytes:
        try:
            return self.registry_path.read_bytes()
        except FileNotFoundError as exc:
            raise RegistryApplyError(f"registry file does not exist: {self.registry_path}") from exc

    def _registry_hash(self) -> str:
        return self._sha256_bytes(self._registry_bytes())

    def _payload_bytes(self, payload: dict[str, Any]) -> bytes:
        return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

    def _write_bytes_atomically(self, destination: Path, content: bytes) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        tmp = destination.with_suffix(destination.suffix + ".tmp")
        tmp.write_bytes(content)
        tmp.replace(destination)

    def plan(self, operation: str) -> RegistryPatch:
        candidate = self.ledger.candidates.get(operation)
        if candidate is None:
            raise RegistryApplyError(f"no promotion candidate for operation: {operation}")
        if candidate.status != "approved":
            raise RegistryApplyError(f"promotion candidate is not approved: {operation} ({candidate.status})")
        payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
        skills = list(payload.get("skills", []))
        before_sha256 = self._registry_hash()
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
                return RegistryPatch(operation, target_id, descriptor, str(self.registry_path), False, "already-present", "identical descriptor already exists", before_sha256=before_sha256, after_sha256=before_sha256)
            raise RegistryApplyError(f"registry ID conflict: {target_id}")
        next_payload = {**payload, "skills": [*skills, descriptor]}
        after_sha256 = self._sha256_bytes(self._payload_bytes(next_payload))
        return RegistryPatch(operation, target_id, descriptor, str(self.registry_path), False, "planned", "approved candidate requires explicit apply", before_sha256=before_sha256, after_sha256=after_sha256)

    def create_manifest(self, operation: str, path: str | Path) -> RegistryPatch:
        patch = self.plan(operation)
        if patch.status == "already-present":
            raise RegistryApplyError(f"cannot create manifest for an already-present operation: {operation}")
        manifest = RegistryApplyManifest(
            schema_version=1,
            operation=patch.operation,
            target_id=patch.target_id,
            registry_path=patch.registry_path,
            descriptor=patch.descriptor,
            before_sha256=patch.before_sha256 or "",
            after_sha256=patch.after_sha256 or "",
        )
        manifest.save(path)
        return RegistryPatch(**{**patch.to_dict(), "manifest_path": str(path)})

    def approve_manifest(self, path: str | Path, note: str) -> RegistryApplyManifest:
        manifest_path = Path(path)
        manifest = RegistryApplyManifest.load(manifest_path)
        if manifest.status != "planned":
            raise RegistryApplyError(f"manifest is not awaiting approval: {manifest.status}")
        if self._registry_hash() != manifest.before_sha256:
            raise RegistryApplyError("registry changed since manifest was planned")
        approved = RegistryApplyManifest(**{**manifest.to_dict(), "status": "approved", "approval_note": note})
        approved.save(manifest_path)
        return approved

    def apply_manifest(self, path: str | Path, *, write: bool = False) -> RegistryPatch:
        manifest_path = Path(path)
        manifest = RegistryApplyManifest.load(manifest_path)
        if manifest.status == "applied":
            return RegistryPatch(manifest.operation, manifest.target_id, manifest.descriptor, manifest.registry_path, False, "already-applied", "manifest is already applied", str(manifest_path), manifest.before_sha256, manifest.applied_sha256 or manifest.after_sha256, manifest.backup_path)
        if manifest.status != "approved":
            raise RegistryApplyError(f"manifest is not approved: {manifest.status}")
        current_hash = self._registry_hash()
        if current_hash != manifest.before_sha256:
            raise RegistryApplyError("registry changed after manifest approval")
        if not write:
            return RegistryPatch(manifest.operation, manifest.target_id, manifest.descriptor, manifest.registry_path, False, "approved", "approved manifest requires explicit --write", str(manifest_path), manifest.before_sha256, manifest.after_sha256)
        payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
        skills = list(payload.get("skills", []))
        if any(skill.get("id") == manifest.target_id for skill in skills):
            raise RegistryApplyError(f"registry ID conflict: {manifest.target_id}")
        payload["skills"] = [*skills, manifest.descriptor]
        content = self._payload_bytes(payload)
        actual_after = self._sha256_bytes(content)
        if actual_after != manifest.after_sha256:
            raise RegistryApplyError("manifest payload does not match the current registry shape")
        backup_path = manifest_path.with_suffix(manifest_path.suffix + ".backup")
        backup_path.write_bytes(self._registry_bytes())
        self._write_bytes_atomically(self.registry_path, content)
        applied = RegistryApplyManifest(**{**manifest.to_dict(), "status": "applied", "backup_path": str(backup_path), "applied_sha256": actual_after})
        applied.save(manifest_path)
        return RegistryPatch(manifest.operation, manifest.target_id, manifest.descriptor, manifest.registry_path, True, "applied", "explicit write requested after manifest approval", str(manifest_path), manifest.before_sha256, actual_after, str(backup_path))

    def rollback(self, path: str | Path, *, write: bool = False) -> RegistryPatch:
        manifest_path = Path(path)
        manifest = RegistryApplyManifest.load(manifest_path)
        if manifest.status == "rolled_back":
            return RegistryPatch(manifest.operation, manifest.target_id, manifest.descriptor, manifest.registry_path, False, "already-rolled-back", "manifest is already rolled back", str(manifest_path), manifest.before_sha256, manifest.applied_sha256, manifest.backup_path)
        if manifest.status != "applied" or not manifest.backup_path:
            raise RegistryApplyError("only an applied manifest with a backup can be rolled back")
        if self._registry_hash() != (manifest.applied_sha256 or manifest.after_sha256):
            raise RegistryApplyError("registry changed after apply; refusing rollback")
        backup = Path(manifest.backup_path)
        if not backup.exists():
            raise RegistryApplyError(f"rollback backup does not exist: {backup}")
        if not write:
            return RegistryPatch(manifest.operation, manifest.target_id, manifest.descriptor, manifest.registry_path, False, "rollback-planned", "explicit --write required for rollback", str(manifest_path), manifest.applied_sha256, manifest.before_sha256, str(backup))
        self._write_bytes_atomically(self.registry_path, backup.read_bytes())
        rolled_back = RegistryApplyManifest(**{**manifest.to_dict(), "status": "rolled_back"})
        rolled_back.save(manifest_path)
        return RegistryPatch(manifest.operation, manifest.target_id, manifest.descriptor, manifest.registry_path, True, "rolled-back", "restored the pre-apply registry snapshot", str(manifest_path), manifest.applied_sha256, manifest.before_sha256, str(backup))

    def apply(self, operation: str, *, write: bool = False, manifest_path: str | Path | None = None) -> RegistryPatch:
        if manifest_path is not None:
            manifest = Path(manifest_path)
            if not manifest.exists():
                self.create_manifest(operation, manifest)
                return RegistryPatch(**{**self.plan(operation).to_dict(), "manifest_path": str(manifest)})
            return self.apply_manifest(manifest, write=write)
        patch = self.plan(operation)
        if not write or patch.status == "already-present":
            return patch
        payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
        payload.setdefault("skills", []).append(patch.descriptor)
        content = self._payload_bytes(payload)
        self._write_bytes_atomically(self.registry_path, content)
        return RegistryPatch(patch.operation, patch.target_id, patch.descriptor, patch.registry_path, True, "applied", "explicit write requested", before_sha256=patch.before_sha256, after_sha256=self._sha256_bytes(content))
