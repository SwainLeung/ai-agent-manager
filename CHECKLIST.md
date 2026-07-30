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
- [x] `git diff --cached --check` passes.
- [ ] GitHub Actions CI is green before public visibility.
- [x] Remote URL is reviewed before the first push.

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
- 2026-07-29: adapter entity manifests validate declared counts and reject checkpoint resume against a changed input fingerprint.
- 2026-07-29: real local FlowUs v3 manifest smoke test covered 8,169 entities, 62,070 proposals, and two resumable 100-proposal chunks without writeback.
- 2026-07-29: full local FlowUs v3 execution completed 62,070/62,070 proposals with 21,839 Script completions, 40,231 gated pending records, 0 failures, and 250-item atomic checkpoints.
- 2026-07-29: full-batch promotion proposal generated four Script candidates; no registry mutation occurred.
- 2026-07-30: segmented checkpoint regression and interval validation coverage passed; full suite now has 36 passing tests.
- 2026-07-30: read-only local FlowUs file audit ran against 16 assets and produced 107 findings; no merge or delete mutation occurred.
- 2026-07-30: rebuilt eight granite.wiki derived files from normalized pipeline outputs, archived the prior versions, and reduced actionable stale/drift/duplicate findings to zero; 92 provenance/reference findings remain.
- 2026-07-30: v0.3.0 Host Integration added `LocalAgentHost`, provider-neutral run/resume handling, optional correction capture, CLI coverage, and 3 regression tests.
- 2026-07-30: v0.4.0 runtime accounting added ignored `UsageLedger` metrics, idempotent run/skill counting, paused-to-completed upgrades, and 2 regression tests; full suite now has 42 passing tests.
- 2026-07-30: v0.5.0 Provider/Tool boundary added provider-neutral interfaces, MockProvider, dry-run tools, explicit EffectGate approval, CLI smoke flows, and 2 regression tests; full suite now has 44 passing tests.
- 2026-07-30: v0.6.0 Feedback metacognition added Interceptor, Reflector, RuleDistiller, candidate-only rule output, and 4 regression tests; full suite now has 48 passing tests.
- 2026-07-30: v0.7.0 reviewed Profile/Project rule storage, explicit sync/review/revoke CLI flows, plan exposure, and regression coverage completed.
- 2026-07-30: v0.8.0 deterministic Skill→Script candidate solidification and evidence thresholds completed.
- 2026-07-30: v0.9.0 development started with deterministic ScriptSandbox replay, fixture filtering, drift detection, side-effect safeguards, and CLI coverage.

## Gradual local-agent adoption

- [x] Define `LocalAgentAdapter` as the single local control-plane entry point.
- [x] Route tasks through `SkillRegistry` and `Router` before execution.
- [x] Execute the example graph through the adapter with checkpoint and trace persistence.
- [x] Record feedback as reversible profile/project candidates.
- [x] Generate a combined feedback, lifecycle, and entropy report.
- [x] Connect one real local-agent host to `adapter prepare` and `adapter run`.
- [x] Define provider/tool adapter boundary with mock and dry-run implementations.
- [ ] Add a production provider/tool adapter behind the public-neutral boundary.
- [x] Generate Skill→Script candidates from repeated execution evidence without automatic Registry mutation.
- [x] Replay candidate Scripts against deterministic fixtures without Registry/provider/external effects.
- [ ] Pilot one low-risk task and review its trace and feedback candidate.
- [ ] Promote only reviewed feedback into project rules.
- [x] Store reviewed Profile/Project rule candidates separately from the public registry.
- [x] Expose only approved and enabled rules to adapter plans; keep provider prompt injection host-owned.

## Codex host integration

- [x] Add repository-level `AGENTS.md` with adapter and verification conventions.
- [x] Install the local global Codex bridge at `~/.codex/AGENTS.md`.
- [x] Smoke-test Codex bridge commands through `LocalAgentAdapter`.
- [x] Add quick-start `ADAPTER.md` for other Agents.
- [x] Add detailed adapter integration guide and machine-readable contract.
- [x] Add minimal host Agent example and contract test.
- [x] Add an experimental knowledge-ingestion preparation route for Flowus-style tasks.
- [x] Capture and fix the persisted feedback reload pitfall.
- [x] Add host-side feedback capture after user corrections.
- [x] Run a low-risk Codex task through the adapter and review its trace.
- [x] Add entity-level Skills-vs-Scripts decision proposals with human gates.
- [ ] Connect private FlowUs entity batches to `adapter decide` and review promotion candidates.
- [x] Execute a shadow batch through ProposalExecutor without registry mutation.
- [ ] Add reviewed promotion ledger for repeated Script success.
- [x] Add reviewed promotion ledger for repeated Script success.
- [x] Add separate versioned registry-apply workflow after promotion review.
- [x] Add exact-diff approval manifest and rollback/undo for reviewed registry apply.
