# Local Agent Adapter

`LocalAgentAdapter` is the small integration seam between a host Agent and the Agent Manager control plane.

It gives a host Agent four governed operations:

```text
prepare(task)   -> route candidates
run(task)       -> graph execution + checkpoint + trace
feedback(...)   -> reversible improvement candidate
report()        -> feedback + lifecycle + entropy signals
```

The adapter does not call a model, own provider credentials, or silently change project rules. The host Agent remains responsible for interpretation, model calls, tools, approvals, and final user communication.

## Quick start

From the repository root:

```powershell
python scripts/agent-manager.py adapter prepare --task "summarize a report"
python scripts/agent-manager.py adapter run --task "summarize a report"
python scripts/agent-manager.py adapter feedback --event-type correction --scope project --subject tone --note "use concise language" --confidence 0.9
python scripts/agent-manager.py adapter report
```

For a Python host:

```python
from agent_manager.adapter import LocalAgentAdapter

adapter = LocalAgentAdapter.for_project(".")
plan = adapter.prepare("summarize a report")
result = adapter.run("summarize a report", {"structured": True})
if result.context.status != "completed":
    raise RuntimeError(result.context.error)
```

## State boundary

Runtime files go under `.agent-manager/`, which is ignored by Git:

- `checkpoints/`: resumable execution contexts;
- `traces/`: structured execution events;
- `feedback.json`: reversible feedback events;
- reports generated from those signals.

Do not commit credentials, private prompts, user data, production logs, traces, checkpoints, or feedback state.

Read the [adapter integration guide](docs/adapter-integration.md) and the machine-readable [adapter contract](config/adapter-contract.json) before writing another host adapter.
