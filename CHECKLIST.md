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
- 2026-07-29: 13 unit tests passed after adding Local Agent Adapter integration coverage.
- 2026-07-29: adapter `prepare`, `run`, `feedback`, and `report` CLI flows passed.
- 2026-07-29: Flowus knowledge-ingestion task routes to the experimental preparation skill.
- 2026-07-29: a persisted feedback reload/append pitfall was fixed; 16 unit tests now pass.
- 2026-07-29: public `main` is synchronized; runtime state remains ignored.
- 2026-07-29: checkpoint test found that max-step interruption was terminal and lost `next_node`; scheduler now writes resumable `paused` checkpoints and regression coverage passes.
- 2026-07-29: added entity-level DecisionMatrix; deterministic schema-known operations propose Scripts, semantic operations propose Skills, and sensitive/merge/writeback operations require human review.
- 2026-07-29: added ProposalExecutor; Script proposals execute deterministically, Skill and human-review proposals remain pending, and large batches resume from checkpoints.
- 2026-07-29: added promotion ledger; repeated Script success produces a reversible candidate, and human approval does not mutate the registry.
- 2026-07-29: added RegistryApplier; approved candidates produce dry-run patches by default, and explicit writes remain candidate-status registry changes.
- 2026-07-29: added registry apply manifests; plan/approve locks before-and-after hashes, explicit apply saves a backup, and rollback restores only when no external drift is detected.
- 2026-07-29: CLI end-to-end test passed for manifest plan, approval, dry-run, apply, and rollback on an isolated temporary registry.
- 2026-07-29: PromotionLedger schema v2 deduplicates repeated evidence by stable key and preserves cumulative candidate statistics across reloads.

## Gradual local-agent adoption

- [x] Define `LocalAgentAdapter` as the single local control-plane entry point.
- [x] Route tasks through `SkillRegistry` and `Router` before execution.
- [x] Execute the example graph through the adapter with checkpoint and trace persistence.
- [x] Record feedback as reversible profile/project candidates.
- [x] Generate a combined feedback, lifecycle, and entropy report.
- [ ] Connect one real local-agent host to `adapter prepare` and `adapter run`.
- [ ] Add a provider/tool adapter behind the public-neutral boundary.
- [ ] Pilot one low-risk task and review its trace and feedback candidate.
- [ ] Promote only reviewed feedback into project rules.

## Codex host integration

- [x] Add repository-level `AGENTS.md` with adapter and verification conventions.
- [x] Install the local global Codex bridge at `~/.codex/AGENTS.md`.
- [x] Smoke-test Codex bridge commands through `LocalAgentAdapter`.
- [x] Add quick-start `ADAPTER.md` for other Agents.
- [x] Add detailed adapter integration guide and machine-readable contract.
- [x] Add minimal host Agent example and contract test.
- [x] Add an experimental knowledge-ingestion preparation route for Flowus-style tasks.
- [x] Capture and fix the persisted feedback reload pitfall.
- [ ] Add automatic host-side feedback capture after user corrections.
- [ ] Run a low-risk Codex task through the adapter and review its trace.
- [x] Add entity-level Skills-vs-Scripts decision proposals with human gates.
- [ ] Connect private FlowUs entity batches to `adapter decide` and review promotion candidates.
- [x] Execute a shadow batch through ProposalExecutor without registry mutation.
- [ ] Add reviewed promotion ledger for repeated Script success.
- [x] Add reviewed promotion ledger for repeated Script success.
- [x] Add separate versioned registry-apply workflow after promotion review.
- [x] Add exact-diff approval manifest and rollback/undo for reviewed registry apply.
