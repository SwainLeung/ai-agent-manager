from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol, runtime_checkable


@dataclass(frozen=True)
class EffectGate:
    allow_external: bool = False
    approved: bool = False

    @property
    def permits(self) -> bool:
        return self.allow_external and self.approved


@dataclass(frozen=True)
class ToolResult:
    tool: str
    success: bool
    output: Any = None
    dry_run: bool = True
    external_effect: bool = False


class ExternalEffectDenied(PermissionError):
    pass


@runtime_checkable
class ToolAdapter(Protocol):
    def invoke(
        self,
        tool: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        dry_run: bool = True,
        gate: EffectGate | None = None,
    ) -> ToolResult:
        """Invoke a tool under an explicit external-effect policy."""


class DryRunToolAdapter:
    """Safe adapter that describes a tool call without executing it."""

    def invoke(
        self,
        tool: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        dry_run: bool = True,
        gate: EffectGate | None = None,
    ) -> ToolResult:
        if not dry_run:
            raise ExternalEffectDenied("DryRunToolAdapter cannot perform external effects")
        return ToolResult(
            tool=tool,
            success=True,
            output={"tool": tool, "arguments": dict(arguments or {}), "mode": "dry-run"},
            dry_run=True,
            external_effect=False,
        )


class CallableToolAdapter:
    """Host-owned callable tools guarded by an explicit effect gate."""

    def __init__(self, handlers: Mapping[str, Callable[[Mapping[str, Any]], Any]]):
        self.handlers = dict(handlers)

    def invoke(
        self,
        tool: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        dry_run: bool = True,
        gate: EffectGate | None = None,
    ) -> ToolResult:
        args = dict(arguments or {})
        if dry_run:
            return ToolResult(tool, True, {"tool": tool, "arguments": args, "mode": "dry-run"}, True, False)
        if gate is None or not gate.permits:
            raise ExternalEffectDenied("external tool effect requires allow_external and approved")
        if tool not in self.handlers:
            return ToolResult(tool, False, {"error": f"unknown tool: {tool}"}, False, False)
        return ToolResult(tool, True, self.handlers[tool](args), False, True)
