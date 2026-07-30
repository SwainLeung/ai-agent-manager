"""Minimal host-Agent integration example.

This file demonstrates the public contract. Replace the example graph handler
with the host Agent's private model and tool adapter.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_manager.host import LocalAgentHost  # noqa: E402
from agent_manager.router import RouteSignals  # noqa: E402


def main() -> int:
    host = LocalAgentHost.for_project(ROOT)
    plan = host.adapter.prepare(
        "summarize a report",
        RouteSignals(structured=True, deterministic=True),
    )
    print("route:", plan.to_dict())

    result = host.run_task("summarize a report", {"structured": True})
    print("run:", result.to_dict())
    return 0 if result.context.status == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
