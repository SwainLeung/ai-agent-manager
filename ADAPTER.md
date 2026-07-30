# Local Agent Adapter

`LocalAgentAdapter` is the small integration seam between a host Agent and the Agent Manager control plane.

It gives a host Agent six governed operations:

```text
prepare(task)   -> route candidates
run(task)       -> graph execution + checkpoint + trace
host-run(task)  -> host facade + optional correction capture
feedback(...)   -> reversible improvement candidate
report()        -> feedback + lifecycle + entropy signals + metrics
metacognition  -> hypotheses + reversible rule candidates
decide(...)     -> entity operation proposal: script / skill / human_review
```

The adapter does not call a model, own provider credentials, or silently change project rules. The host Agent remains responsible for interpretation, model calls, tools, approvals, and final user communication. Version 0.5.0 exposes provider and tool interfaces without selecting a production provider or enabling external effects by default.

## Quick start

From the repository root:

```powershell
python scripts/agent-manager.py adapter prepare --task "summarize a report"
python scripts/agent-manager.py adapter run --task "summarize a report"
python scripts/agent-manager.py adapter host-run --task "summarize a report" --feedback-subject tone --feedback-note "use concise language" --feedback-confidence 0.9
python scripts/agent-manager.py adapter provider-mock --prompt "hello"
python scripts/agent-manager.py adapter tool-dry-run --tool "write_file"
python scripts/agent-manager.py adapter feedback --event-type correction --scope project --subject tone --note "use concise language" --confidence 0.9
python scripts/agent-manager.py adapter report
```

For a Python host:

```python
from agent_manager.host import LocalAgentHost

host = LocalAgentHost.for_project(".")
result = host.run_task(
    "summarize a report",
    {"structured": True},
    correction_subject="tone",
    correction_note="use concise language",
    correction_confidence=0.9,
)
if result.run.context.status != "completed":
    raise RuntimeError(result.run.context.error)
```

## State boundary

Runtime files go under `.agent-manager/`, which is ignored by Git:

- `checkpoints/`: resumable execution contexts;
- `traces/`: structured execution events;
- `feedback.json`: reversible feedback events;
- `usage.json`: idempotent per-run/per-skill usage ledger and derived metrics;
- reports generated from those signals.

When `max_steps` is reached, the scheduler writes a `paused` checkpoint that
retains `next_node` and can be resumed. Terminal `failed` and `completed`
checkpoints are not resumable; hosts should distinguish a recoverable pause
from a terminal failure before choosing retry, fallback, or restart.

`adapter report` also exposes runtime metrics. Usage is stored under ignored
`.agent-manager/usage.json`; the public registry remains a baseline and is not
rewritten by normal task execution. A resumed paused run updates its existing
`run_id + skill_id` record instead of creating a duplicate call.

Version 0.6.0 adds deterministic feedback metacognition to `adapter report`:
high-confidence feedback is reflected into hypotheses and distilled into
candidate rules. Candidates remain non-injected and do not mutate the registry
until a separate reviewed promotion workflow approves them.

Do not commit credentials, private prompts, user data, production logs, traces, checkpoints, or feedback state.

Read the [adapter integration guide](docs/adapter-integration.md) and the machine-readable [adapter contract](config/adapter-contract.json) before writing another host adapter.

For structured entities, use the decision matrix before execution. A manifest
may be either a plain entity array or an object containing `entities[]`; when
`entity_count` is present, it must match the array length.

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
- large batches checkpoint atomically in configurable segments (`--checkpoint-every`, default 100);
- checkpoints bind to an input entity fingerprint and reject a different manifest;
- no execution result automatically changes the registry.

For local FlowUs or knowledge-vault files, use the read-only file audit before
any merge, quarantine, or delete workflow:

```powershell
python scripts/agent-manager.py adapter audit-files `
  --root D:\path\to\vault\wiki-entities `
  --output-dir D:\path\to\reports\flowus-anti-entropy `
  --stale-days 2
```

The audit writes `flowus-local-manifest.json`,
`flowus-anti-entropy-report.json`, `flowus-merge-candidates.json`, and
`flowus-delete-candidates.json`. It only scans and reports; it does not merge,
quarantine, delete, or write to FlowUs. Source freshness uses source
verification/scrape timestamps when present. A local `last_modified` value is
not treated as source freshness; missing source timestamps produce a
`freshness-unknown` finding.

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
