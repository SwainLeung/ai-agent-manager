from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping
from enum import Enum
import json
import subprocess
from tempfile import TemporaryDirectory
import sys

from .decision import ExecutionProposal
from .executor import ProposalExecutor


class SandboxMode(Enum):
    IN_PROCESS = "in_process"
    SUBPROCESS = "subprocess"


class SandboxError(ValueError):
    pass


@dataclass(frozen=True)
class SandboxReport:
    candidate_id: str
    operation: str
    status: str
    entity_count: int
    processed: int
    skipped: int
    completed: int
    failed: int
    success_rate: float
    expected_success_rate: float
    drift: bool
    cases: tuple[dict[str, Any], ...]
    registry_mutated: bool = False
    external_effects: bool = False
    provider_calls: int = 0
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ScriptSandbox:
    """Replay a candidate Script through deterministic, side-effect-free handlers."""

    def __init__(self, *, executor: ProposalExecutor | None = None):
        self.executor = executor or ProposalExecutor()

    def replay(
        self,
        candidate: Mapping[str, Any],
        entities: Iterable[Mapping[str, Any]],
        *,
        drift_tolerance: float = 0.05,
        mode: SandboxMode = SandboxMode.IN_PROCESS,
    ) -> SandboxReport:
        payload = candidate.get("candidate") if isinstance(candidate.get("candidate"), dict) else candidate
        candidate_id = str(payload.get("id", ""))
        operation = str(payload.get("operation", "")).strip()
        if not candidate_id or not operation:
            raise SandboxError("candidate requires id and operation")
        if str(payload.get("kind", "")) != "script":
            raise SandboxError("sandbox accepts Script candidates only")
        if str(payload.get("status", "candidate")) != "candidate":
            raise SandboxError("sandbox requires a candidate-status descriptor")
        if bool(payload.get("registry_mutated", False)):
            raise SandboxError("sandbox refuses a candidate that already mutated the registry")
        if not 0 <= drift_tolerance <= 1:
            raise ValueError("drift_tolerance must be between 0 and 1")

        if mode == SandboxMode.SUBPROCESS:
            return self._replay_subprocess(candidate, entities)
        source_entities = list(entities)
        selected = []
        skipped = 0
        for entity in source_entities:
            entity_operation = str(entity.get("operation", "")).strip()
            if entity_operation and entity_operation != operation:
                skipped += 1
                continue
            selected.append(entity)

        cases = []
        for entity in selected:
            subject_id = str(entity.get("entity_id") or entity.get("source_id") or "unknown")
            proposal = ExecutionProposal(
                subject_id=subject_id,
                operation=operation,
                kind="script",
                score=1.0,
                confidence=1.0,
                reasons=("sandbox-replay",),
                gate="none",
            )
            cases.append(self.executor.execute(entity, proposal).to_dict())

        completed = sum(item.get("status") == "completed" for item in cases)
        failed = sum(item.get("status") == "failed" for item in cases)
        processed = len(cases)
        success_rate = completed / processed if processed else 0.0
        expected = float(payload.get("success_rate", 0.0))
        drift = abs(success_rate - expected) > drift_tolerance
        reasons = []
        if not cases:
            reasons.append("no-matching-fixtures")
        if failed:
            reasons.append("replay-failure")
        if drift:
            reasons.append("success-rate-drift")
        status = "passed" if cases and not failed and not drift else "failed"
        return SandboxReport(
            candidate_id=candidate_id,
            operation=operation,
            status=status,
            entity_count=len(source_entities),
            processed=processed,
            skipped=skipped,
            completed=completed,
            failed=failed,
            success_rate=round(success_rate, 3),
            expected_success_rate=round(expected, 3),
            drift=drift,
            cases=tuple(cases),
            reasons=tuple(reasons),
        )

    def _replay_subprocess(self, candidate: dict | Mapping[str, Any], entities: Iterable[Mapping[str, Any]]) -> SandboxReport:
        """Run replay in a Python subprocess for OS-level isolation."""
        payload = {"candidate": dict(candidate) if hasattr(candidate, "get") else candidate, "entities": list(entities)}
        sandbox_dir = r"D:\AI Agent Manager\src"
        script = (
            "import sys, json; sys.path.insert(0, %r); "
            "from agent_manager.sandbox import ScriptSandbox; "
            "data = json.loads(sys.stdin.read()); "
            "result = ScriptSandbox().replay(data[\"candidate\"], data[\"entities\"]); "
            "print(json.dumps(result.to_dict()))"
        ) % sandbox_dir
        try:
            cp = subprocess.run(
                [sys.executable, "-c", script],
                input=json.dumps(payload),
                capture_output=True, text=True, timeout=30,
            )
            if cp.returncode != 0:
                raise SandboxError(f"subprocess sandbox failed: {cp.stderr}")
            return SandboxReport(**json.loads(cp.stdout))
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError) as exc:
            raise SandboxError(f"subprocess error: {exc}")
