# Architecture

Agent Manager is a small control-plane library. It does not call a model,
store user data, or publish to a provider. It defines the governance contracts
that a provider adapter or application can implement.

## Core flow

```text
task
  -> registry metadata
  -> lightweight router
  -> selected Skill or Script
  -> execution graph / checkpoint
  -> feedback and telemetry
  -> reviewed rule store
  -> lifecycle and anti-entropy audit
```

## Components

- `models.py`: immutable descriptors for skills, route decisions, and feedback.
- `registry.py`: validates identities, layers, kinds, and hot/warm/cold tiers.
- `router.py`: performs deterministic keyword routing and applies the
  Skills-versus-Scripts decision signals.
- `lifecycle.py`: proposes status and frequency changes from observed usage.
- `feedback.py`: keeps reversible profile/project feedback as candidates.
- `graph.py`: loads and validates explicit nodes, edges, starts, and fallbacks.
- `execution.py`: executes graphs with retries, error-edge fallbacks, checkpoints, and step limits.
- `recorder.py`: records structured run traces and persists them as JSON.
- `adapter.py`: bridges a local agent into routing, graph execution, feedback, and improvement reports.
- `rules.py`: stores reviewed Profile/Project rules and exposes only explicitly enabled rules to adapter plans.
- `solidification.py`: compiles repeated Skill evidence into candidate Script descriptors without mutating the registry.
- `entropy.py`: finds lifecycle stalls, low-success capabilities, and duplicate
  signatures.

## SSOT boundary

The registry and graph files are the public examples' source of truth. Runtime
telemetry, credentials, provider configuration, private prompts, and user
memories must live outside the repository. Changes should be made at the
source registry or graph first, then derived artifacts should be regenerated.

The local `theory txt/` directory is reference material only and is ignored by
Git. The public `docs/theory/` files are short, sanitized distillations rather
than copies of the source notes.

## Extension points

Applications may add provider adapters, vector indexes, custom execution
handlers, human approval nodes, and persistent stores. Those integrations
should remain behind explicit interfaces and should never make secrets part of
registry metadata, graph definitions, or traces.

## Local adoption boundary

`LocalAgentAdapter` is the recommended integration seam for a host agent. It
keeps public contracts in the repository while placing traces, checkpoints, and
feedback events in the ignored `.agent-manager/` runtime directory. Feedback is
reported as a candidate first; it does not silently mutate the registry or
project rules.

Reviewed Profile/Project rules live under the ignored runtime directory. Rule
sync creates candidates, review approval enables a reversible rule, and revoke
disables it. Active rules are exposed as plan metadata for the host Agent; they
are never silently merged into provider prompts or the public registry.
