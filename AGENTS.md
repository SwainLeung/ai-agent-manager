# Agent Manager repository contract

This repository is the public control plane for local-agent routing, graph execution, trace recording, and reversible feedback.

## Before work

- Read `README.md`, `CHECKLIST.md`, and the relevant architecture/theory document.
- For non-trivial tasks, prepare a route from the repository root:
  `python scripts/agent-manager.py adapter prepare --task "<task>"`
- Use `adapter run` for workflows that fit the example graph or an explicitly supplied graph.

## During work

- Keep provider credentials, private prompts, user data, production logs, traces, checkpoints, and feedback state outside Git.
- Runtime state belongs under ignored `.agent-manager/`.
- Feedback is a candidate until reviewed; never silently promote it into the registry or project rules.
- Prefer deterministic scripts for structured work and skills/providers for interpretation.

## Before handoff

- Run `python -m unittest discover -s tests -v`.
- Run `python scripts/public-check.py`.
- Run `git diff --cached --check` before committing.
- Report remaining unchecked items in `CHECKLIST.md`.
