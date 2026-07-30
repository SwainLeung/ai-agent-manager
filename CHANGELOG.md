# Changelog

## [Unreleased]

- Changed max-step interruption from terminal `failed` to resumable `paused`.
- Preserved `next_node` in paused checkpoints and added regression coverage for CLI/API resume.
- Documented the distinction between recoverable pauses and terminal failures.
- Added entity-level `DecisionMatrix` and `ExecutionProposal` for Script/Skill/human-review routing.
- Added `adapter decide` CLI flow and contract coverage without automatic rule promotion.
- Added `ProposalExecutor` and `adapter execute` for gated Script execution with pending Skill/human-review records and resumable checkpoints.
- Added persistent Script promotion ledger with evidence thresholds and explicit approve/reject review; registry mutation remains separate.
- Added dry-run/explicit-write RegistryApplier with approval checks, ID conflict detection, and candidate-only descriptors.
- Added versioned registry apply manifests with before/after SHA-256 locks, explicit manifest approval, backup creation, drift checks, and rollback/undo.
- Added CLI and contract coverage for the complete promotion transaction: plan, approve, dry-run, apply, and rollback.
- Upgraded PromotionLedger to schema v2 with cross-run evidence persistence, stable-key deduplication, and latest-status success-rate tracking.
- Added manifest-aware batch execution with declared-count validation and SHA-256 input fingerprints in resumable checkpoints.
- Added segmented atomic checkpoint writes for large proposal batches, avoiding per-proposal O(n²) checkpoint I/O.
- Added read-only local file Anti-entropy audit with provenance, freshness, duplicate, ownership, reference-integrity, merge-candidate, and delete-candidate reports.

## [0.6.0] - 2026-07-30

- Added `FeedbackInterceptor` for validated host-side correction, undo, redo, pitfall, fallback, and approval capture.
- Added deterministic `Reflector` hypotheses grouped by feedback evidence and confidence.
- Added `RuleDistiller` reversible candidates with `registry_mutated=false` and `injection=disabled` safeguards.
- Exposed metacognition hypotheses and rule candidates through `adapter report` without automatic policy injection.

## [0.5.0] - 2026-07-30

- Added provider-neutral `ProviderAdapter` and deterministic `MockProvider` interfaces.
- Added `ToolAdapter`, `DryRunToolAdapter`, `CallableToolAdapter`, and explicit `EffectGate` approval for external effects.
- Integrated provider completion and tool invocation into `LocalAgentHost` without owning credentials or enabling writeback by default.
- Added `adapter provider-mock` and `adapter tool-dry-run` smoke flows and regression coverage for denied and approved effects.

## [0.4.0] - 2026-07-30

- Added an ignored runtime `UsageLedger` for per-run Skill calls/successes and status metrics.
- Made usage accounting idempotent by `run_id + skill_id`; paused runs upgrade to completed without double-counting on resume.
- Projected runtime usage into lifecycle and entropy reports without mutating the public registry.
- Exposed runtime metrics through `adapter report` and added regression coverage for idempotency and lifecycle projection.

## [0.3.0] - 2026-07-30

- Added `LocalAgentHost` as a provider-neutral host-facing facade for governed task runs and checkpoint resume.
- Added host-side correction capture that records reversible feedback candidates without auto-promoting rules.
- Added `adapter host-run` CLI flow with optional correction capture.
- Added host integration contract, example usage, and regression coverage for run, pause/resume, and feedback validation.

## [0.2.4] - 2026-07-29

- Added an experimental knowledge-ingestion preparation route for Flowus/ontology/Obsidian mapping tasks.
- Fixed persisted `FeedbackStore` reloads so feedback remains appendable after restart.
- Added regression coverage for route discovery and feedback round trips.

## [0.2.3] - 2026-07-29

- Added `ADAPTER.md` and a detailed adapter integration guide for other Agents.
- Added a machine-readable adapter contract and a minimal host integration example.
- Added a contract test to keep the public integration surface discoverable.

## [0.2.2] - 2026-07-29

- Added repository-level `AGENTS.md` instructions for Codex and other local hosts.
- Added documented global Codex bridge guidance for routing work through `LocalAgentAdapter`.
- Kept the provider-neutral boundary intact: host agents remain responsible for model and tool calls.

## [0.2.1] - 2026-07-29

- Added `LocalAgentAdapter` as the local control-plane bridge.
- Added adapter task preparation, graph execution, feedback recording, and improvement reports.
- Added adapter CLI commands: `prepare`, `run`, `feedback`, and `report`.
- Added adapter integration tests while keeping runtime state under ignored `.agent-manager/`.

## [0.2.0] - 2026-07-29

- Added a provider-neutral Graph Scheduler with checkpoints and max-step protection.
- Added retry and error-edge fallback handling for graph nodes.
- Added JSON execution traces with run, node, failure, checkpoint, and completion events.
- Added `graph run` and `trace show` CLI commands.
- Added scheduler, retry, fallback, resume, and trace persistence tests.

## [0.1.0] - 2026-07-29

- Added registry-driven skill descriptors and lazy keyword routing.
- Added Skills-versus-Scripts decision scoring.
- Added lifecycle health proposals and hot/warm/cold tiers.
- Added feedback events for undo, redo, pitfalls, fallbacks, and corrections.
- Added graph validation and anti-entropy auditing.
- Added theory distillations, tests, and GitHub Actions CI.
