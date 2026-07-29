# Local Agent Adapter

`LocalAgentAdapter` is the small integration seam between a host Agent and the Agent Manager control plane.

It gives a host Agent four governed operations:

```text
prepare(task)   -> route candidates
run(task)       -> graph execution + checkpoint + trace
feedback(...)   -> reversible improvement candidate
report()        -> feedback + lifecycle + entropy signals
decide(...)     -> entity operation proposal: script / skill / human_review
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

When `max_steps` is reached, the scheduler writes a `paused` checkpoint that
retains `next_node` and can be resumed. Terminal `failed` and `completed`
checkpoints are not resumable; hosts should distinguish a recoverable pause
from a terminal failure before choosing retry, fallback, or restart.

Do not commit credentials, private prompts, user data, production logs, traces, checkpoints, or feedback state.

Read the [adapter integration guide](docs/adapter-integration.md) and the machine-readable [adapter contract](config/adapter-contract.json) before writing another host adapter.

For structured entities, use the decision matrix before execution:

```powershell
python scripts/agent-manager.py adapter decide --entity-file entities.json
python scripts/agent-manager.py adapter execute --entity-file entities.json --summary-only
python scripts/agent-manager.py adapter promote propose --checkpoint .agent-manager/checkpoints/entities.json
python scripts/agent-manager.py adapter promote plan --operation duplicate_key --manifest-file .agent-manager/promotion.manifest.json
python scripts/agent-manager.py adapter promote approve --manifest-file .agent-manager/promotion.manifest.json --note "reviewed isolated registry patch"
python scripts/agent-manager.py adapter promote apply --manifest-file .agent-manager/promotion.manifest.json --write
python scripts/agent-manager.py adapter promote rollback --manifest-file .agent-manager/promotion.manifest.json --write
```

The matrix treats hashing, validation, link extraction, duplicate keys, and
other schema-known repeatable operations as Script candidates. Ontology
interpretation and relation discovery remain Skill candidates. Merge and
writeback operations require `human_review`; the matrix never promotes a
candidate directly into a registry rule.

Execution is intentionally gated:

- Script proposals run through deterministic handlers and write result records;
- Skill proposals remain `pending` for the host Agent;
- human-review proposals remain `pending` for approval;
- execution checkpoints can pause and resume by proposal index;
- no execution result automatically changes the registry.

Promotion is a separate reversible ledger:

```powershell
python scripts/agent-manager.py adapter promote review `
  --operation duplicate_key `
  --decision approve `
  --note "reviewed deterministic handler"
```

Approval records evidence and review status only. Applying a promotion to the
registry remains a separate versioned change. The recommended transaction is
`plan -> approve -> apply -> rollback`: the manifest records the registry
before/after hashes, `apply --write` saves a backup, and rollback refuses to
overwrite a registry that changed after apply.

`promote apply` defaults to dry-run. It requires an approved candidate and
rejects unapproved candidates or registry ID conflicts. The manifest workflow
adds a second approval boundary for the exact registry diff. Add `--write`
only in an explicitly reviewed change workflow; the generated descriptor
starts as a `candidate` registry entry rather than silently becoming stable.
