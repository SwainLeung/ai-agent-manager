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
- 2026-07-30: v0.9.0 completed with deterministic ScriptSandbox replay and registry proposal workflow (propose-approve-apply-rollback) plus CLI coverage.

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
- [x] Add reviewed promotion ledger for repeated Script success.
- [x] Add separate versioned registry-apply workflow after promotion review.
- [x] Add exact-diff approval manifest and rollback/undo for reviewed registry apply.
- 2026-07-30: v1.0.0 released with 55 tests passing and full solidify-sandbox-proposal pipeline.

## Backlog: Theory gap implementations

> 从 REPORT-theory-to-practice.md 各域提取的缺失项，按优先级 P0→P3 排列。
> 每个条目标注目标、依赖模块和验收标准。

---

### 🔴 P0 — Immediate (low effort, high visibility, few dependencies)

---

#### [ ] 1. Graph visualization: trace → DOT/Mermaid output

- **Target version**: v1.1.0
- **Dual-pyramid domain**: Graph Engineering (§7)
- **Module**: `src/agent_manager/recorder.py` (TraceEvent), new module `src/agent_manager/visualization.py`
- **Goal**: Export execution trace to standard graph formats (DOT for Graphviz, Mermaid for markdown docs).
- **Acceptance**:
  - `adapter trace viz --run-id <id> --format dot` produces valid DOT text.
  - `adapter trace viz --run-id <id> --format mermaid` produces embeddable Mermaid block.
  - All node types (decision/script/skill/checkpoint/fallback/finish) appear with distinct styles.
  - Error/failure edges are highlighted.
  - Tests: 2+ unit tests for DOT and Mermaid output.
- **Dependencies**: Recorder (`recorder.py`) already writes trace JSON; only output conversion needed.
- **Estimated complexity**: ⭐ (1–2 Python modules, ~150 lines)

#### [ ] 2. Pitfall knowledge base: queryable pitfall feedback store

- **Target version**: v1.1.0
- **Dual-pyramid domain**: Loop Engineering — self-correction loop (§6)
- **Module**: `src/agent_manager/feedback.py`, `src/agent_manager/pitfall.py` (new)
- **Goal**: Extract pitfall-type FeedbackEvents into a queryable knowledge base with deduplication and frequency ranking.
- **Acceptance**:
  - `adapter pitfall list` shows all captured pitfalls ranked by frequency.
  - `adapter pitfall show --id <id>` shows full context (event_type, scope, subject, note, confidence, timestamp).
  - Deduplication: same (scope + subject + signal) counts as repeat, increments counter.
  - No registry mutation, no automatic rule injection.
  - Tests: 2+ tests for recording dedup and listing.
- **Dependencies**: FeedbackEvent types already exist in `feedback.py`. Persistence similar to FeedbackStore.
- **Estimated complexity**: ⭐ (1 new module, ~200 lines)

#### [ ] 3. Slim report: structural entropy audit → formatted report

- **Target version**: v1.1.0
- **Dual-pyramid domain**: Anti-entropy governance (§5)
- **Module**: `src/agent_manager/entropy.py`, `scripts/agent-manager.py`
- **Goal**: Generate a human-readable structure or JSON report from entropy audit findings for capacity planning.
- **Acceptance**:
  - `adapter report --slim` produces a categorized breakdown: duplicate signatures, low-success skills, lifecycle-stalled entries, unused capabilities.
  - JSON mode (`--format json`) for machine consumption.
  - Summary line: "X duplicate, Y low-success, Z stalled [total N findings]".
  - No registry or side effects.
  - Tests: 1+ test verifying report shape and counts.
- **Dependencies**: `entropy.audit()` already returns structured findings list.
- **Estimated complexity**: ⭐ (extend existing, ~100 lines)

---

### 🟡 P1 — Short-term (moderate effort, clear architecture)

---

#### [ ] 4. Circuit breaker: runtime protection for runaway failure loops

- **Target version**: v1.2.0
- **Dual-pyramid domain**: Loop Engineering — self-correction loop (§6)
- **Module**: `src/agent_manager/execution.py` (GraphScheduler)
- **Goal**: Add configurable circuit breaker to GraphScheduler: if a node fails N times consecutively (configurable threshold), the run transitions to terminal `failed` instead of retrying indefinitely.
- **Acceptance**:
  - CircuitBreakerPolicy dataclass: `max_consecutive_failures`, `recovery_interval_seconds`.
  - Scheduler checks breaker state before each node execution.
  - When threshold reached, run enters `failed` state with reason `circuit_breaker: node <id> failed N times`.
  - After recovery interval, a new run resets the breaker.
  - Tests: 2+ tests for threshold tripping, recovery, and no-op below threshold.
- **Dependencies**: `GraphScheduler._run_node()` already has retry logic; breaker sits before retry.
- **Estimated complexity**: ⭐⭐ (extend scheduler, ~120 lines)

#### [ ] 5. Error analyzer: structured failure aggregation from trace events

- **Target version**: v1.2.0
- **Dual-pyramid domain**: Loop Engineering — self-correction loop (§6)
- **Module**: `src/agent_manager/analyzer.py` (new)
- **Goal**: Parse execution trace events (failure/error) and produce aggregated failure reports grouped by node, error type, frequency.
- **Acceptance**:
  - `adapter analyze --run-id <id>` outputs: node-wise failure rate, top error messages, edge failure count.
  - `adapter analyze --all` aggregates across all stored traces.
  - Output format: table (stdout) and JSON (`--format json`).
  - Tests: 2+ tests with synthetic trace data.
- **Dependencies**: `recorder.py` trace JSON schema, `adapter.py` CLI integration.
- **Estimated complexity**: ⭐⭐ (1 new module, ~250 lines)

#### [ ] 6. Subgraph nesting and reuse: composite graph nodes

- **Target version**: v1.2.0
- **Dual-pyramid domain**: Graph Engineering (§7)
- **Module**: `src/agent_manager/graph.py`, `src/agent_manager/execution.py`
- **Goal**: Allow a graph node to reference another GraphDefinition as a subgraph. Subgraphs share the parent's ExecutionContext but maintain their own checkpoint namespace.
- **Acceptance**:
  - GraphDefinition supports `kind: "subgraph"` nodes with a `subgraph_id` field.
  - `load()` resolves subgraph reference (same file or named registry reference).
  - `validate()` checks subgraph validity recursively (max depth 3, no circular).
  - Scheduler expands subgraph inline during execution; subgraph start/finish events are recorded as nested trace events.
  - Tests: 3+ tests for subgraph resolution, depth limit, circular detection, execution trace.
- **Dependencies**: `graph.py` Schema + `execution.py` Scheduler.
- **Estimated complexity**: ⭐⭐⭐ (cross-module, ~400 lines)

#### [ ] 7. Prompt template registry (Prompts as Code)

- **Target version**: v1.2.0
- **Dual-pyramid domain**: Anti-entropy governance (§5)
- **Module**: `src/agent_manager/prompt_registry.py` (new)
- **Goal**: Version-controlled prompt template storage with GitOps-style diff review. Each prompt has id, version, content, tags, and lifecycle state.
- **Acceptance**:
  - `prompt_registry add --id <id> --content <path> --version 0.1.0` registers a prompt.
  - `prompt_registry diff --id <id> --v1 <ver> --v2 <ver>` shows content diff.
  - `prompt_registry list --tag <tag>` filters by tag.
  - Storage: JSON file under `.agent-manager/prompts.json` (ignored by Git).
  - Lifecycle: active / deprecated / archived.
  - Tests: 2+ tests for add, diff, filter.
- **Dependencies**: No core dependencies; new standalone module.
- **Estimated complexity**: ⭐⭐ (1 module, ~300 lines, but extends CLI)

#### [ ] 8. OS-level sandbox isolation for Script replay

- **Target version**: v1.2.0
- **Dual-pyramid domain**: Skills vs Scripts (§3), Loop Engineering — script curing loop (§6)
- **Module**: `src/agent_manager/sandbox.py` (extend), `src/agent_manager/sandbox_os.py` (new)
- **Goal**: Current ScriptSandbox is deterministic in-process. Add optional OS-level isolation (subprocess with restricted filesystem/network) for Script execution.
- **Acceptance**:
  - `SandboxMode.IN_PROCESS` (default, existing) and `SandboxMode.SUBPROCESS` (new).
  - SUBPROCESS mode runs the descriptor operations in a Python subprocess with restricted read-only working directory.
  - `external_effects=false` and `provider_calls=0` enforced at subprocess boundary.
  - On Windows, use `subprocess` with restricted token; on POSIX, optional `seccomp` stub.
  - Falls back to IN_PROCESS when OS isolation is unavailable.
  - Tests: 2+ tests for subprocess mode, fallback, and side-effect enforcement.
- **Dependencies**: `sandbox.py`, Python `subprocess` module.
- **Estimated complexity**: ⭐⭐⭐ (os-specific, ~350 lines)

#### [ ] 9. Auto-generate fix proposals from lifecycle drift detection

- **Target version**: v1.2.0
- **Dual-pyramid domain**: Dynamic governance (§2)
- **Module**: `src/agent_manager/lifecycle.py`, `src/agent_manager/registry_proposal.py`
- **Goal**: When lifecycle audit detects a skill with degrading success rate or stalled status, auto-generate a RegistryChangeProposal candidate (e.g. status → `deprecated` or `archived`).
- **Acceptance**:
  - `lifecycle.propose_fixes()` returns a list of candidate RegistryChangeProposal objects.
  - Each candidate includes source audit finding, proposed action, before/after state.
  - `adapter lifecycle fix --review` shows all auto-generated fix candidates without applying.
  - No automatic registry mutation: candidates require manual review + approve.
  - Tests: 2+ tests for fix candidate generation from synthetic lifecycle data.
- **Dependencies**: `lifecycle.py` (has propose()), `registry_proposal.py` (has data model).
- **Estimated complexity**: ⭐⭐ (extend existing, ~200 lines)

---

### 🟡 P2 — Medium-term (higher effort, significant design work)

---

#### [ ] 10. Hot/cold data TTL eviction for registry entries

- **Target version**: v2.0.0
- **Dual-pyramid domain**: Dual pyramid (§1)
- **Module**: `src/agent_manager/registry.py`, `src/agent_manager/entropy.py`
- **Goal**: After N days without use (cold) or N days since last access, auto-evict or archive registry entries. Configurable TTL per frequency tier.
- **Acceptance**:
  - TTL config in registry settings: `cold_ttl_days`, `warm_ttl_days`, `hot_ttl_days`.
  - Expired entries auto-set to `archived` status.
  - `entropy.audit()` reports entries approaching TTL threshold.
  - Archival preserves data in `.agent-manager/archive/` for restore.
  - Tests: 2+ tests for TTL expiry, pre-expiry warning, and archival.
- **Dependencies**: Registry `last_used` field, `entropy.py`, new archival persistence.
- **Estimated complexity**: ⭐⭐⭐ (~300 lines)

#### [ ] 11. Temp file garbage collector

- **Target version**: v2.0.0
- **Dual-pyramid domain**: Anti-entropy governance (§5)
- **Module**: `src/agent_manager/cleanup.py` (new)
- **Goal**: Scan `build/`, `dist/`, `__pycache__/`, temp worktrees, and orphaned `.agent-manager/` artifacts; report candidates for deletion.
- **Acceptance**:
  - `adapter cleanup scan` lists candidate files with size, age, last-access time.
  - Dry-run by default: no deletion without explicit `--execute`.
  - Safe-list: never delete `.git/`, `.agent-manager/rules.json`, `.agent-manager/traces/`.
  - Tests: 1+ test for scan output and safe-list enforcement.
- **Dependencies**: `pathlib`, `os` module; no core architecture changes.
- **Estimated complexity**: ⭐⭐ (~200 lines)

#### [ ] 12. Memory compaction: profile/project rule dedup and pruning

- **Target version**: v2.0.0
- **Dual-pyramid domain**: Meta-cognition & feedback (§4), Anti-entropy (§5)
- **Module**: `src/agent_manager/rules.py`, `src/agent_manager/entropy.py` (extend)
- **Goal**: Detect duplicate, contradictory, or expired profile/project rules; merge or prune automatically with backup.
- **Acceptance**:
  - `adapter rules compact` scans active rules for identical (scope+subject+signal) → merge with highest confidence.
  - Contradiction detection: same scope+subject but opposite signal → flag for human review.
  - Expired rules (no recent feedback associated, >90 days) → auto-archive candidate.
  - All mutations are reversible: backup before prune.
  - Tests: 2+ tests for merge, contradiction flag, expiry detection.
- **Dependencies**: `rules.py` RuleStore, `feedback.py` candidates().
- **Estimated complexity**: ⭐⭐⭐ (~350 lines)

#### [ ] 13. Data source health checker

- **Target version**: v2.0.0
- **Dual-pyramid domain**: Anti-entropy governance (§5)
- **Module**: `src/agent_manager/health.py` (new), `config/health-checks.json` (optional)
- **Goal**: Define configurable health checks for known data sources (filesystem paths, optional network endpoints). Check accessibility, staleness, and schema drift.
- **Acceptance**:
  - HealthCheck config: `type: file|url`, `path`, `max_age_hours`, `expected_schema` (optional).
  - `adapter health run` runs all configured checks; output per-check status (ok/warning/fail).
  - File check: exists, age matches max_age, size > 0.
  - URL check: HTTP 200, response time < threshold.
  - Tests: 2+ tests for file check pass/fail and URL reachability check.
- **Dependencies**: New module; config in existing `config/` convention.
- **Estimated complexity**: ⭐⭐ (~250 lines)

---

### 🔵 P3 — Long-term (experimental, architecture-level)

---

#### [ ] 14. Dynamic graph generation (LLM → JSON GraphPlan)

- **Target version**: v3.0.0
- **Dual-pyramid domain**: Graph Engineering (§7)
- **Module**: `src/agent_manager/planner.py` (new)
- **Goal**: Accept a natural-language task description and route through an LLM to produce a structured GraphPlan (JSON GraphDefinition with nodes and edges) for execution.
- **Acceptance**:
  - `adapter plan --task "summarize a report"` produces a JSON GraphPlan.
  - GraphPlan validates against GraphDefinition schema.
  - Generated graph can be executed via `graph run`.
  - Provider call is behind the provider-neutral boundary (uses ProviderAdapter).
  - Tests: 1+ test for schema-valid output from mocked provider response.
- **Dependencies**: ProviderAdapter (`provider.py`), GraphDefinition (`graph.py`), error handling for malformed LLM output.
- **Estimated complexity**: ⭐⭐⭐⭐ (~500 lines)

#### [ ] 15. Canary / gradual rollout for skill lifecycle transitions

- **Target version**: v3.0.0
- **Dual-pyramid domain**: Dynamic governance (§2)
- **Module**: `src/agent_manager/canary.py` (new)
- **Goal**: When a Skill transitions status (e.g. experimental → stable), route only a percentage of matching tasks through the new version; keep the old version for the rest.
- **Acceptance**:
  - CanaryConfig: skill_id, new_version, traffic_percentage, cooldown_hours.
  - Router checks canary table: X% tasks use new_version, (100-X)% use old_version.
  - `adapter canary list` / `adapter canary promote` / `adapter canary rollback`.
  - Statistics: success rate per version during canary.
  - Tests: 2+ tests for percentage distribution, promote, rollback.
- **Dependencies**: Router (`router.py`), Registry version support, new canary state store.
- **Estimated complexity**: ⭐⭐⭐⭐ (~500 lines)

#### [ ] 16. Long-tail skill auto-generation pipeline

- **Target version**: v3.0.0
- **Dual-pyramid domain**: Dual pyramid (§1)
- **Module**: `src/agent_manager/skill_generator.py` (new)
- **Goal**: Analyze usage patterns and generate lightweight Skill descriptors for unregistered but frequently used tool/task combinations (from UsageLedger + FeedbackStore).
- **Acceptance**:
  - `adapter skill suggest` outputs candidate Skill descriptors from execution history.
  - Each candidate includes: id, layer="project", frequency="cold", triggers from task keywords.
  - Candidates are `status=candidate` and require human review before registry insertion.
  - Tests: 1+ test for candidate generation from synthetic ledger data.
- **Dependencies**: UsageLedger (`metrics.py`), FeedbackStore (`feedback.py`), Registry schema.
- **Estimated complexity**: ⭐⭐⭐⭐⭐ (~600 lines)

---

### Notes

- **Semantic**: Item numbering is for tracking only; actual implementation order may vary based on dependencies.
- **Registry mutation**: No backlog item auto-mutates the registry — all candidate or promoted states require human approval.
- **CI signal**: P0 items should be attempted after GitHub Actions CI shows green for `main`.
- **Provider boundary**: Items that call external models (e.g. #14 dynamic graph) use the provider-neutral `ProviderAdapter` interface.
