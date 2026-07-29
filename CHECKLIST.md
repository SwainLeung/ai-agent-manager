# Public Repository Checklist

## Theory alignment

- [x] Dual pyramid: abstraction layer and usage-frequency tier.
- [x] Lazy activation and registry-based routing.
- [x] Skills versus Scripts decision matrix.
- [x] Profile/Project meta-cognition and reversible feedback rules.
- [x] Anti-entropy lifecycle governance.
- [x] Five Loop Engineering loops.
- [x] Graph Engineering nodes, edges, fallbacks, and validation.

## Public safety

- [x] No real domains, emails, usernames, server addresses, private URLs, or local absolute paths.
- [x] No credentials, API keys, tokens, cookies, private prompts, or user memories.
- [x] `theory txt/` remains local-only and is excluded from Git.
- [x] No generated telemetry, production logs, or private graph plans.

## Quality gates

- [x] `python -m unittest discover -s tests -v` passes.
- [x] Registry and graph examples validate.
- [x] Route output contains no prompt or secret material.
- [ ] `git diff --cached --check` passes.
- [ ] GitHub Actions CI is green before public visibility.
- [ ] Remote URL is reviewed before the first push.

## Local verification

- 2026-07-29: 7 unit tests passed.
- 2026-07-29: registry listing, deterministic route, graph validation, and public boundary check passed.
- 2026-07-29: v0.2 Graph Scheduler example completed with checkpoint and 12-event trace.
- 2026-07-29: 11 unit tests passed after adding scheduler, retry, fallback, resume, and recorder coverage.
- 2026-07-29: no Git remote is configured; no public push was attempted.
