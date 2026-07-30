from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .adapter import AdapterRun, LocalAgentAdapter
from .models import FeedbackEvent
from .router import RouteSignals


@dataclass(frozen=True)
class HostTaskResult:
    """Provider-neutral result returned to a host Agent."""

    task: str
    run: AdapterRun
    feedback: FeedbackEvent | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "run": self.run.to_dict(),
            "feedback": self.feedback.__dict__ if self.feedback else None,
        }


class LocalAgentHost:
    """Small host-facing facade for governed runs and correction capture.

    Provider calls, tool authentication, and final response composition remain
    outside this class. The facade only joins those host events to the local
    adapter's route, graph, checkpoint, trace, and reversible feedback flows.
    """

    def __init__(self, adapter: LocalAgentAdapter):
        self.adapter = adapter

    @classmethod
    def for_project(
        cls,
        root: str | Path,
        *,
        state_dir: str | Path = ".agent-manager",
    ) -> "LocalAgentHost":
        return cls(LocalAgentAdapter.for_project(root, state_dir=state_dir))

    def run_task(
        self,
        task: str,
        inputs: Mapping[str, Any] | None = None,
        signals: RouteSignals | None = None,
        *,
        graph_path: str | Path | None = None,
        checkpoint: str | Path | None = None,
        trace: str | Path | None = None,
        max_attempts: int = 1,
        backoff_seconds: float = 0.0,
        max_steps: int = 100,
        correction_subject: str | None = None,
        correction_note: str | None = None,
        correction_scope: str = "project",
        correction_confidence: float = 0.5,
    ) -> HostTaskResult:
        if correction_note is not None and not correction_subject:
            raise ValueError("correction_subject is required when correction_note is provided")

        result = self.adapter.run(
            task,
            inputs,
            signals,
            graph_path=graph_path,
            checkpoint=checkpoint,
            trace=trace,
            max_attempts=max_attempts,
            backoff_seconds=backoff_seconds,
            max_steps=max_steps,
        )
        feedback = None
        if correction_note is not None:
            feedback = self.adapter.record_feedback(
                "correction",
                correction_scope,
                correction_subject or "task",
                correction_note,
                correction_confidence,
            )
        return HostTaskResult(task, result, feedback)

    def resume_task(
        self,
        task: str,
        checkpoint: str | Path,
        inputs: Mapping[str, Any] | None = None,
        signals: RouteSignals | None = None,
        **kwargs: Any,
    ) -> HostTaskResult:
        """Resume a paused checkpoint through the same host-facing contract."""

        return self.run_task(
            task,
            inputs,
            signals,
            checkpoint=checkpoint,
            **kwargs,
        )
