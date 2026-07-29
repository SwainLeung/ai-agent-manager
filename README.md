# Agent Manager

An open, provider-neutral framework for governing AI Agent skills, scripts, feedback, loops, and execution graphs.

This project turns an Agent from a pile of prompts and utilities into a governed system:

1. The dual-pyramid model separates system, domain, and project skills from hot to cold usage tiers.
2. Lazy routing loads only the small set of skills relevant to a task.
3. A decision matrix chooses flexible Skills or deterministic Scripts.
4. Profile and Project memory turn undo/redo, pitfalls, and fallbacks into governed meta-rules.
5. Anti-entropy audits detect stale, duplicate, and unowned capabilities.
6. Loop Engineering connects execution, distillation, adaptation, recovery, and cleanup loops.
7. Graph Engineering makes execution paths explicit, testable, and reusable.

## Quick start

```powershell
python scripts/agent-manager.py registry list
python scripts/agent-manager.py route --task "summarize a report" --top-k 3
python scripts/agent-manager.py graph validate --file config/example-graph.json
python scripts/agent-manager.py graph run --file config/example-graph.json
python scripts/agent-manager.py trace show --file .agent-manager/traces/<run-id>.json
python scripts/agent-manager.py audit
python -m unittest discover -s tests -v
```

## Repository structure

```text
config/                 generic registries and graph examples
docs/                   architecture and theory distillations
scripts/                command-line entry point
src/agent_manager/      provider-neutral implementation
tests/                  deterministic unit tests
```

The original working notes are kept locally under `theory txt/` and ignored from the public repository. Public documentation contains sanitized distillations under `docs/theory/`.

## Design principles

- Registry before prompt: every reusable capability has an identity, owner, version, triggers, and lifecycle state.
- Lazy before full load: route from metadata, then load full implementation only when selected.
- Script for certainty, Skill for ambiguity: use deterministic code for structured, repeatable work; use LLM-driven skills for interpretation and planning.
- Feedback must be reversible: profile/project rules start as candidates and can be weakened or removed.
- Graphs over hidden chains: nodes, edges, fallbacks, and checkpoints are inspectable.
- Every mutation is observable: record version, source, decision, and outcome.

## Runtime execution in v0.2.0

The scheduler executes validated graphs with deterministic handlers or application-provided handlers. Each run supports:

- checkpoint persistence after every node;
- retry attempts with optional backoff;
- error-edge fallback routing;
- maximum-step protection against runaway graphs;
- JSON traces for replay and diagnosis.

The public example graph uses built-in handlers so it can run without a model provider. Applications can pass a handler mapping to `GraphScheduler` for real node behavior.

## Public boundary

This repository contains generic code and examples only. Do not add credentials, provider keys, private prompts, user profiles, real domains, customer data, local absolute paths, or production logs.

See [CHECKLIST.md](CHECKLIST.md), [SECURITY.md](SECURITY.md), and [docs/architecture.md](docs/architecture.md).
