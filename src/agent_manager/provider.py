from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, runtime_checkable


@dataclass(frozen=True)
class ProviderResponse:
    text: str
    provider: str
    model: str
    usage: dict[str, int] = field(default_factory=dict)


@runtime_checkable
class ProviderAdapter(Protocol):
    name: str

    def complete(
        self,
        prompt: str,
        *,
        metadata: Mapping[str, Any] | None = None,
    ) -> ProviderResponse:
        """Return a provider response without owning governance state."""


class ProviderUnavailable(RuntimeError):
    pass


class MockProvider:
    """Deterministic provider for tests and local contract smoke runs."""

    name = "mock"

    def __init__(self, prefix: str = "mock response"):
        self.prefix = prefix
        self.calls: list[dict[str, Any]] = []

    def complete(
        self,
        prompt: str,
        *,
        metadata: Mapping[str, Any] | None = None,
    ) -> ProviderResponse:
        self.calls.append({"prompt": prompt, "metadata": dict(metadata or {})})
        words = len(prompt.split())
        return ProviderResponse(
            text=f"{self.prefix}: {prompt}",
            provider=self.name,
            model="deterministic",
            usage={"prompt_tokens": words, "completion_tokens": words + 2},
        )
