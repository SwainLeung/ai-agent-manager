# Adapter Integration Guide

This guide describes the provider-neutral contract for connecting a local Agent to Agent Manager.

## 1. What the adapter owns

The adapter owns governance and execution plumbing:

1. route task metadata through `SkillRegistry` and `Router`;
2. execute a validated graph through `GraphScheduler`;
3. persist checkpoints and structured traces;
4. store explicit user feedback as reversible candidates;
5. report lifecycle and anti-entropy signals.

## 2. What the host Agent owns

The host Agent owns interpretation and external effects:

- model/provider calls;
- tool selection and authentication;
- user clarification and approval;
- domain-specific handlers;
- final response composition;
- deciding whether a feedback candidate is promoted.

Never put provider credentials or private user context in the public registry, graph definition, or adapter contract.

## 3. Recommended task lifecycle

```text
request
  -> adapter.prepare(task, signals)
  -> host selects/loads provider capability
  -> adapter.run(task, inputs, graph, handlers)
  -> host reviews result and trace
  -> adapter.record_feedback(...) when the user gives a correction
  -> adapter.report() during periodic maintenance
```

`prepare` is lightweight and safe to run before every non-trivial task. `run` is for a graph-backed workflow. A host may execute its own provider handler between routing and graph execution when the public example graph is not sufficient.

## 4. Minimal Python integration

```python
from agent_manager.adapter import LocalAgentAdapter
from agent_manager.router import RouteSignals

adapter = LocalAgentAdapter.for_project(".", state_dir=".agent-manager")
plan = adapter.prepare(
    "summarize a report",
    RouteSignals(structured=True, deterministic=True),
)

result = adapter.run(
    "summarize a report",
    inputs={"structured": True},
)

if result.context.status != "completed":
    # A paused context retains next_node and may be resumed.
    # A failed context is terminal and needs fallback or restart.
    print(result.context.error)
```

The public adapter uses built-in example handlers. A real host can pass a graph-specific handler mapping directly to `GraphScheduler` when it needs provider calls or domain behavior.

### Recoverable pauses

When `max_steps` is reached, the scheduler returns `status: "paused"`, keeps
the current `next_node`, and saves a resumable checkpoint. Hosts may pass that
checkpoint back to `adapter.run(..., checkpoint=...)`. A `completed` or
`failed` checkpoint is terminal and must not be resumed; choose an explicit
fallback or a fresh run instead.

## 5. Feedback is not automatic policy

Feedback is first stored as a candidate:

```powershell
python scripts/agent-manager.py adapter feedback `
  --event-type correction `
  --scope project `
  --subject tone `
  --note "use concise language" `
  --confidence 0.9
```

Review `adapter report` before promoting any candidate. Promotion should be explicit, versioned, reversible, and covered by tests.

## 6. Integration checklist for another Agent

- [ ] Import `LocalAgentAdapter` or invoke the adapter CLI.
- [ ] Call `prepare` before non-trivial work.
- [ ] Pass only task metadata and safe structured inputs to the public layer.
- [ ] Keep provider calls in the host Agent or a private provider adapter.
- [ ] Persist runtime state under ignored `.agent-manager/` or an external state directory.
- [ ] Review traces after failures and checkpoints after interruptions.
- [ ] Record user corrections as candidates, not immediate policy changes.
- [ ] Run tests and public-boundary checks before sharing changes.

The machine-readable schema is `config/adapter-contract.json`.
