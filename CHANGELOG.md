# Changelog

## [1.1.0] - 2026-07-30

- Added `visualization.py` for trace-to-DOT/Mermaid graph output.
- Added `trace viz` CLI subcommand with `--format dot|mermaid`.
- Added Pitfall knowledge base: `pitfall_summary()` and `pitfall_detail()` on FeedbackStore.
- Added `adapter pitfall list/show` CLI for queryable pitfall entries.
- Added Slim report: `slim_report()` and `print_slim_report()` on entropy module.
- Added `adapter report --slim` for categorized audit findings.
- Upgraded test suite to 65 passing tests.

## [1.2.0] - 2026-07-30

- Added `CircuitBreakerPolicy` with configurable `max_consecutive_failures` and recovery interval.
- Integrated circuit breaker into `GraphScheduler._execute_node()`.
- Added `analyzer.py` with `analyze_trace()` for failure aggregation across trace events.
- Added `adapter analyze` CLI for node-wise failure statistics.
- Added `prompt_registry.py` with `PromptRegistry` for version-controlled prompt templates.
- Added `adapter prompt add/list/diff` CLI.
- Added subgraph nesting: `graph.py expand()` method expands `kind: subgraph` nodes.
- GraphScheduler auto-expands subgraphs on construction.
- Added auto-fix proposals: `lifecycle.py propose_fixes()` for degraded/stalled skills.
- Added `adapter lifecycle fix` CLI.
- Added OS-level sandbox: `SandboxMode.SUBPROCESS` replays in subprocess.
- Upgraded test suite to 76 passing tests.

## [2.0.0] - 2026-07-31

- Added `health.py` with `run_health_check()` for file and URL health probes.
- Added `adapter health` CLI for running configured health checks.
- Added `cleanup.py` with `scan_cleanup_candidates()` for temp/artifact file scanning.
- Added `adapter cleanup scan` CLI with dry-run support.
- Added TTL eviction: `TTLConfig` and `evict_expired()` on SkillRegistry.
- Added `adapter ttl` CLI for checking expired skills.
- Added rule compaction: `compact_rules()` for dedup, contradiction detection, and archiving.
- Added `adapter rules compact` CLI.
- Upgraded test suite to 84 passing tests.

## [3.0.0] - 2026-07-31

- Added `planner.py` with `plan_from_task()` for natural-language to GraphDefinition generation.
- Added `adapter plan` CLI that uses ProviderAdapter to generate graph plans.
- Added `canary.py` with `CanaryStore` for percentage-based traffic routing.
- Added `adapter canary start/list/promote/rollback` CLI.
- Added `skill_generator.py` with `suggest_skills()` from UsageLedger and FeedbackStore data.
- Added `adapter skill suggest` CLI for auto-generated Skill candidates.
- All 16 backlog items (P0-P3) completed across 4 releases.
- Upgraded test suite to 90 passing tests.


## [1.0.0] - 2026-07-30

- Added deterministic `ScriptSandbox` replay for candidate Scripts with fixture filtering, success-rate drift detection, and side-effect/provider/registry safeguards.
- Added `RegistryChangeWorkflow` with propose-approve-apply-rollback pipeline for controlled registry mutations.
- Added `adapter change propose/approve/apply/rollback` CLI with SHA-256 checksums, preview, backup, and human-review gates.
- Upgraded project version to 1.0.0 with 55 passing tests.
- Added `adapter sandbox` CLI and regression coverage for successful and failed candidate replays.

## [0.8.0] - 2026-07-30

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
- Added reviewed Profile/Project rule storage with explicit sync, approve/reject, and revoke operations.
- Exposed only approved and enabled rules in adapter plans; registry mutation and provider prompt injection remain disabled.
- Added deterministic Skill→Script candidate solidification from repeated execution evidence.
- Added `adapter solidify`; generated descriptors remain `candidate` and require separate human review before Registry application.

## [0.7.0] - 2026-07-30

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
