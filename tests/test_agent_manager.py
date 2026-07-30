import json
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_manager.adapter import LocalAgentAdapter
from agent_manager.decision import DecisionMatrix
from agent_manager.executor import ProposalExecutor
from agent_manager.file_audit import run_local_audit
from agent_manager.host import LocalAgentHost
from agent_manager.promotion import PromotionLedger
from agent_manager.registry_apply import RegistryApplyError, RegistryApplier
from agent_manager.entropy import audit
from agent_manager.execution import GraphScheduler, NodeResult, RetryPolicy
from agent_manager.feedback import FeedbackStore
from agent_manager.graph import GraphDefinition
from agent_manager.lifecycle import propose
from agent_manager.models import FeedbackEvent, Skill
from agent_manager.recorder import ExecutionRecorder
from agent_manager.registry import RegistryError, SkillRegistry
from agent_manager.router import RouteSignals, Router


def skill(**overrides):
    value = {
        "id": "demo.skill",
        "layer": "domain",
        "kind": "skill",
        "frequency": "warm",
        "version": "0.1.0",
        "status": "candidate",
        "triggers": ["report", "summary"],
        "calls": 4,
        "successes": 3,
    }
    value.update(overrides)
    return Skill.from_dict(value)


class AgentManagerTests(unittest.TestCase):
    def test_decision_matrix_chooses_script_for_deterministic_entity_operation(self):
        proposal = DecisionMatrix().decide({
            "entity_id": "flowus-1",
            "operation": "duplicate_key",
            "confidence": 0.98,
        })
        self.assertEqual(proposal.kind, "script")
        self.assertEqual(proposal.gate, "automatic")

    def test_decision_matrix_chooses_skill_for_ambiguous_ontology_operation(self):
        proposal = DecisionMatrix().decide({
            "entity_id": "flowus-2",
            "operation": "ontology_classify",
            "confidence": 0.92,
            "schema_known": True,
        })
        self.assertEqual(proposal.kind, "skill")
        self.assertEqual(proposal.gate, "host-agent")

    def test_decision_matrix_forces_human_gate_for_sensitive_writeback(self):
        proposal = DecisionMatrix().decide({
            "entity_id": "flowus-3",
            "operation": "candidate_writeback",
            "confidence": 0.99,
            "safety_status": "blocked",
        })
        self.assertEqual(proposal.kind, "human_review")
        self.assertEqual(proposal.gate, "human")

    def test_adapter_decides_entity_batch(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter = LocalAgentAdapter.for_project(Path(__file__).parents[1], state_dir=directory)
            result = adapter.decide_entities([
                {"entity_id": "one", "operation": "snapshot_hash", "confidence": 1.0},
                {"entity_id": "two", "operation": "relation_discovery", "confidence": 0.9},
                {"entity_id": "three", "operation": "candidate_writeback", "confidence": 0.95},
            ])
            self.assertEqual(result["counts"], {"script": 1, "skill": 1, "human_review": 1})
            self.assertTrue(result["human_gate_required"])

    def test_decision_matrix_infers_entity_pipeline(self):
        result = DecisionMatrix().decide_many([{
            "entity_id": "flowus-pipeline",
            "confidence": 0.95,
            "source_url": "https://flowus.cn/example",
            "content_hash": "ABC",
            "linked_source_ids": ["source-2"],
            "duplicate_key": "same-title",
        }])
        self.assertEqual(result["entity_count"], 1)
        self.assertEqual(result["proposal_count"], 8)
        self.assertEqual(result["counts"], {"script": 4, "skill": 2, "human_review": 2})

    def test_proposal_executor_runs_scripts_and_leaves_gates_pending(self):
        entities = [
            {"entity_id": "script-1", "operation": "duplicate_key", "title": "Hello World", "confidence": 0.99},
            {"entity_id": "skill-1", "operation": "ontology_classify", "confidence": 0.99},
            {"entity_id": "review-1", "operation": "candidate_writeback", "confidence": 0.99},
        ]
        result = ProposalExecutor().execute_entities(entities)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["status_counts"], {"completed": 1, "pending": 2, "failed": 0})
        self.assertEqual(result["records"][0]["output"]["duplicate_key"], "helloworld")

    def test_proposal_executor_pauses_and_resumes_checkpoint(self):
        entities = [
            {"entity_id": "one", "operation": "duplicate_key", "title": "One", "confidence": 0.99},
            {"entity_id": "two", "operation": "duplicate_key", "title": "Two", "confidence": 0.99},
        ]
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "proposal-checkpoint.json"
            first = ProposalExecutor().execute_entities(entities, checkpoint=checkpoint, max_items=1)
            self.assertEqual(first["status"], "paused")
            self.assertEqual(first["processed"], 1)
            resumed = ProposalExecutor().execute_entities(entities, checkpoint=checkpoint)
            self.assertEqual(resumed["status"], "completed")
            self.assertEqual(resumed["processed"], 2)

    def test_proposal_executor_checkpoints_at_configured_segments(self):
        entities = [
            {"entity_id": str(index), "operation": "duplicate_key", "title": str(index), "confidence": 0.99}
            for index in range(5)
        ]
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "proposal-checkpoint.json"
            write_count = 0
            original_write_text = Path.write_text

            def counted_write_text(path, data, *args, **kwargs):
                nonlocal write_count
                write_count += 1
                return original_write_text(path, data, *args, **kwargs)

            with mock.patch.object(Path, "write_text", new=counted_write_text):
                result = ProposalExecutor().execute_entities(entities, checkpoint=checkpoint, checkpoint_every=2)
            self.assertEqual(result["status"], "completed")
            self.assertEqual(write_count, 3)
            self.assertEqual(json.loads(checkpoint.read_text(encoding="utf-8"))["next_index"], 5)

    def test_proposal_executor_rejects_invalid_checkpoint_interval(self):
        with self.assertRaisesRegex(ValueError, "checkpoint_every must be at least 1"):
            ProposalExecutor().execute_entities([], checkpoint_every=0)

    def test_proposal_executor_rejects_checkpoint_for_different_manifest(self):
        entities = [
            {"entity_id": "one", "operation": "duplicate_key", "title": "One", "confidence": 0.99},
        ]
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "proposal-checkpoint.json"
            ProposalExecutor().execute_entities(entities, checkpoint=checkpoint, max_items=1)
            changed = [{**entities[0], "title": "Changed"}]
            with self.assertRaises(ValueError):
                ProposalExecutor().execute_entities(changed, checkpoint=checkpoint)

    def test_adapter_executes_entity_batch(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter = LocalAgentAdapter.for_project(Path(__file__).parents[1], state_dir=directory)
            result = adapter.execute_entities([
                {"entity_id": "one", "operation": "snapshot_hash", "content": "abc", "confidence": 1.0},
            ])
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["status_counts"]["completed"], 1)

    def test_promotion_ledger_proposes_only_repeated_successful_scripts(self):
        ledger = PromotionLedger()
        records = [
            {"subject_id": "one", "operation": "duplicate_key", "kind": "script", "status": "completed"},
            {"subject_id": "two", "operation": "duplicate_key", "kind": "script", "status": "completed"},
            {"subject_id": "three", "operation": "duplicate_key", "kind": "script", "status": "completed"},
            {"subject_id": "skill", "operation": "ontology_classify", "kind": "skill", "status": "pending"},
        ]
        candidates = ledger.propose(records)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].operation, "duplicate_key")
        self.assertEqual(candidates[0].status, "candidate")
        self.assertEqual(candidates[0].success_rate, 1.0)

    def test_promotion_review_is_persistent_and_does_not_apply_registry(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "promotion.json"
            ledger = PromotionLedger()
            ledger.propose([
                {"subject_id": "one", "operation": "link_extract", "kind": "script", "status": "completed"},
                {"subject_id": "two", "operation": "link_extract", "kind": "script", "status": "completed"},
                {"subject_id": "three", "operation": "link_extract", "kind": "script", "status": "completed"},
            ])
            ledger.save(path)
            loaded = PromotionLedger.load(path)
            reviewed = loaded.review("link_extract", "approve", "reviewed deterministic fixture")
            loaded.save(path)
            self.assertEqual(reviewed.status, "approved")
            self.assertEqual(PromotionLedger.load(path).report()[0]["status"], "approved")

    def test_promotion_ledger_deduplicates_evidence_across_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "promotion.json"
            ledger = PromotionLedger()
            first = [
                {"subject_id": "one", "operation": "snapshot_hash", "kind": "script", "status": "completed"},
                {"subject_id": "two", "operation": "snapshot_hash", "kind": "script", "status": "completed"},
                {"subject_id": "two", "operation": "snapshot_hash", "kind": "script", "status": "completed"},
            ]
            ledger.propose(first, min_successes=2)
            ledger.save(path)

            loaded = PromotionLedger.load(path)
            candidates = loaded.propose(first + [
                {"subject_id": "three", "operation": "snapshot_hash", "kind": "script", "status": "completed"},
            ], min_successes=2)
            self.assertEqual(candidates[0].evidence_count, 3)
            self.assertEqual(candidates[0].success_count, 3)
            self.assertEqual(len(loaded.evidence["snapshot_hash"]), 3)

    def test_promotion_ledger_tracks_latest_status_per_evidence_key(self):
        ledger = PromotionLedger()
        ledger.propose([
            {"subject_id": "one", "operation": "link_extract", "kind": "script", "status": "completed"},
            {"subject_id": "two", "operation": "link_extract", "kind": "script", "status": "completed"},
            {"subject_id": "three", "operation": "link_extract", "kind": "script", "status": "completed"},
        ])
        ledger.propose([
            {"subject_id": "two", "operation": "link_extract", "kind": "script", "status": "failed"},
        ], min_successes=2, min_success_rate=0.6)
        candidate = ledger.candidates["link_extract"]
        self.assertEqual(candidate.success_count, 2)
        self.assertEqual(candidate.failure_count, 1)
        self.assertEqual(candidate.success_rate, 0.667)

    def test_registry_applier_plans_and_applies_only_approved_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = root / "registry.json"
            ledger_path = root / "promotion.json"
            registry.write_text(json.dumps({"schema_version": 1, "skills": []}), encoding="utf-8")
            ledger = PromotionLedger()
            ledger.propose([
                {"subject_id": "one", "operation": "duplicate_key", "kind": "script", "status": "completed"},
                {"subject_id": "two", "operation": "duplicate_key", "kind": "script", "status": "completed"},
                {"subject_id": "three", "operation": "duplicate_key", "kind": "script", "status": "completed"},
            ])
            ledger.review("duplicate_key", "approve", "reviewed")
            ledger.save(ledger_path)
            applier = RegistryApplier(registry, ledger_path)
            plan = applier.apply("duplicate_key")
            self.assertEqual(plan.status, "planned")
            self.assertFalse(plan.registry_mutated)
            applied = applier.apply("duplicate_key", write=True)
            self.assertEqual(applied.status, "applied")
            payload = json.loads(registry.read_text(encoding="utf-8"))
            self.assertEqual(payload["skills"][0]["id"], "script.duplicate-key")

    def test_registry_applier_rejects_unapproved_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = root / "registry.json"
            ledger_path = root / "promotion.json"
            registry.write_text(json.dumps({"schema_version": 1, "skills": []}), encoding="utf-8")
            ledger = PromotionLedger()
            ledger.propose([
                {"subject_id": "one", "operation": "link_extract", "kind": "script", "status": "completed"},
                {"subject_id": "two", "operation": "link_extract", "kind": "script", "status": "completed"},
                {"subject_id": "three", "operation": "link_extract", "kind": "script", "status": "completed"},
            ])
            ledger.save(ledger_path)
            with self.assertRaises(RegistryApplyError):
                RegistryApplier(registry, ledger_path).apply("link_extract")

    def test_registry_manifest_apply_and_rollback_is_hash_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = root / "registry.json"
            ledger_path = root / "promotion.json"
            manifest_path = root / "duplicate-key.manifest.json"
            original = b'{"schema_version": 1, "skills": []}\n'
            registry.write_bytes(original)
            ledger = PromotionLedger()
            ledger.propose([
                {"subject_id": "one", "operation": "duplicate_key", "kind": "script", "status": "completed"},
                {"subject_id": "two", "operation": "duplicate_key", "kind": "script", "status": "completed"},
                {"subject_id": "three", "operation": "duplicate_key", "kind": "script", "status": "completed"},
            ])
            ledger.review("duplicate_key", "approve", "reviewed")
            ledger.save(ledger_path)
            applier = RegistryApplier(registry, ledger_path)

            planned = applier.create_manifest("duplicate_key", manifest_path)
            self.assertEqual(planned.status, "planned")
            self.assertEqual(registry.read_bytes(), original)
            approved = applier.approve_manifest(manifest_path, "approved for isolated fixture")
            self.assertEqual(approved.status, "approved")
            dry_run = applier.apply_manifest(manifest_path)
            self.assertEqual(dry_run.status, "approved")
            self.assertFalse(dry_run.registry_mutated)

            applied = applier.apply_manifest(manifest_path, write=True)
            self.assertEqual(applied.status, "applied")
            self.assertTrue(Path(applied.backup_path).exists())
            self.assertNotEqual(registry.read_bytes(), original)

            rollback_plan = applier.rollback(manifest_path)
            self.assertEqual(rollback_plan.status, "rollback-planned")
            rolled_back = applier.rollback(manifest_path, write=True)
            self.assertEqual(rolled_back.status, "rolled-back")
            self.assertEqual(registry.read_bytes(), original)

    def test_registry_manifest_refuses_drift_after_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = root / "registry.json"
            ledger_path = root / "promotion.json"
            manifest_path = root / "manifest.json"
            registry.write_text(json.dumps({"schema_version": 1, "skills": []}) + "\n", encoding="utf-8")
            ledger = PromotionLedger()
            ledger.propose([
                {"subject_id": "one", "operation": "snapshot_hash", "kind": "script", "status": "completed"},
                {"subject_id": "two", "operation": "snapshot_hash", "kind": "script", "status": "completed"},
                {"subject_id": "three", "operation": "snapshot_hash", "kind": "script", "status": "completed"},
            ])
            ledger.review("snapshot_hash", "approve", "reviewed")
            ledger.save(ledger_path)
            applier = RegistryApplier(registry, ledger_path)
            applier.create_manifest("snapshot_hash", manifest_path)
            applier.approve_manifest(manifest_path, "approved")
            registry.write_text(json.dumps({"schema_version": 1, "skills": [{"id": "external.change"}]}) + "\n", encoding="utf-8")
            with self.assertRaises(RegistryApplyError):
                applier.apply_manifest(manifest_path, write=True)

    def test_registry_rejects_duplicate_ids(self):
        with self.assertRaises(RegistryError):
            SkillRegistry([skill(), skill()])

    def test_router_prefers_script_for_deterministic_work(self):
        registry = SkillRegistry([
            skill(id="flexible", kind="skill"),
            skill(id="fixed", kind="script"),
        ])
        decisions = Router(registry).decide(
            "report summary", RouteSignals(structured=True, deterministic=True)
        )
        self.assertEqual(decisions[0].skill_id, "fixed")

    def test_lifecycle_promotes_repeated_success(self):
        proposal = propose(skill(calls=12, successes=11, status="candidate", frequency="cold"))
        self.assertEqual(proposal.proposed_status, "stable")
        self.assertEqual(proposal.proposed_frequency, "warm")

    def test_feedback_is_scoped_and_reversible_candidate(self):
        store = FeedbackStore()
        store.record(FeedbackEvent("undo", "profile", "tone", "too formal", 0.9))
        self.assertEqual(store.candidates()[0]["status"], "candidate")
        with self.assertRaises(ValueError):
            store.record(FeedbackEvent("unknown", "profile", "x", "bad", 0.9))

    def test_feedback_store_round_trip_remains_appendable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "feedback.json"
            store = FeedbackStore()
            store.record(FeedbackEvent("pitfall", "project", "sync", "retry", 0.9))
            store.save(path)
            loaded = FeedbackStore.load(path)
            loaded.record(FeedbackEvent("redo", "project", "sync", "repeat", 0.8))
            self.assertEqual(len(loaded.events), 2)

    def test_graph_example_validates(self):
        path = Path(__file__).parents[1] / "config" / "example-graph.json"
        graph = GraphDefinition.load(path)
        self.assertEqual(graph.validate(), [])

    def test_entropy_detects_duplicate_and_low_success(self):
        findings = audit([
            skill(id="a", calls=4, successes=1),
            skill(id="b", calls=4, successes=1),
        ])
        codes = {finding.code for finding in findings}
        self.assertIn("low-success", codes)
        self.assertIn("duplicate-signature", codes)

    def test_local_file_audit_is_read_only_and_reports_entropy_candidates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "entities"
            output = Path(directory) / "reports"
            root.mkdir()
            (root / "one.md").write_text(
                "---\ntitle: One\nowner: team\nlast_scraped: 2026-07-01\n---\n# One\n\n[Missing](missing.md)\n",
                encoding="utf-8",
            )
            (root / "copy.md").write_text((root / "one.md").read_text(encoding="utf-8"), encoding="utf-8")
            (root / "one-copy.md").write_text("---\ntitle: One\nlast_scraped: 2026-07-01\n---\n# One\n\nDifferent body\n", encoding="utf-8")
            (root / "derived.json").write_text('{"generated_at":"2026-07-01T00:00:00Z"}\n', encoding="utf-8")
            result = run_local_audit(root, output, stale_days=2, now=datetime(2026, 7, 10, tzinfo=timezone.utc))
            codes = {finding["code"] for finding in result["findings"]}
            self.assertIn("stale", codes)
            self.assertIn("exact-duplicate", codes)
            self.assertIn("normalized-duplicate", codes)
            self.assertIn("unowned", codes)
            self.assertIn("unresolved-reference", codes)
            self.assertFalse(result["mutation_performed"])
            self.assertTrue((output / "flowus-local-manifest.json").exists())
            self.assertTrue((output / "flowus-anti-entropy-report.json").exists())
            self.assertTrue((output / "flowus-merge-candidates.json").exists())
            self.assertTrue((output / "flowus-delete-candidates.json").exists())
            self.assertTrue((root / "one.md").exists())

    def test_graph_rejects_missing_edge_target(self):
        value = {"id": "bad", "start": "a", "nodes": [{"id": "a"}], "edges": [{"from": "a", "to": "b"}]}
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as handle:
            json.dump(value, handle)
            path = handle.name
        try:
            self.assertTrue(GraphDefinition.load(path).validate())
        finally:
            Path(path).unlink(missing_ok=True)

    def test_scheduler_runs_example_and_records_trace(self):
        graph = GraphDefinition.load(Path(__file__).parents[1] / "config" / "example-graph.json")
        with tempfile.TemporaryDirectory() as directory:
            trace_path = Path(directory) / "trace.json"
            checkpoint_path = Path(directory) / "checkpoint.json"
            recorder = ExecutionRecorder(graph_id=graph.graph_id)
            context = GraphScheduler(
                graph,
                recorder=recorder,
                checkpoint_path=checkpoint_path,
            ).run({"structured": True})
            recorder.save(trace_path)
            self.assertEqual(context.status, "completed")
            self.assertEqual(context.steps, 3)
            self.assertTrue(trace_path.exists())
            self.assertEqual(ExecutionRecorder.load(trace_path).summary()["status"], "completed")

    def test_scheduler_retries_failed_node(self):
        graph = GraphDefinition("retry-flow", "1.0.0", "work", ({"id": "work", "kind": "script"},), ())
        attempts = {"count": 0}

        def flaky(_: dict, __):
            attempts["count"] += 1
            if attempts["count"] == 1:
                return NodeResult.failure("temporary failure")
            return NodeResult(output={"ok": True})

        recorder = ExecutionRecorder(graph_id=graph.graph_id)
        context = GraphScheduler(
            graph,
            handlers={"work": flaky},
            recorder=recorder,
            retry_policy=RetryPolicy(max_attempts=2),
        ).run()
        self.assertEqual(context.status, "completed")
        self.assertEqual(attempts["count"], 2)
        self.assertTrue(any(event.event == "node_failed" for event in recorder.events))

    def test_scheduler_falls_back_after_failure(self):
        graph = GraphDefinition(
            "fallback-flow",
            "1.0.0",
            "work",
            ({"id": "work", "kind": "script"}, {"id": "fallback", "kind": "fallback"}),
            ({"from": "work", "to": "fallback", "when": "error"},),
        )
        context = GraphScheduler(
            graph,
            handlers={"work": lambda *_: NodeResult.failure("bad input")},
        ).run()
        self.assertEqual(context.status, "completed")
        self.assertEqual(context.data["errors"]["work"], "bad input")

    def test_scheduler_resumes_running_checkpoint(self):
        graph = GraphDefinition("resume-flow", "1.0.0", "finish", ({"id": "finish", "kind": "checkpoint"},), ())
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "checkpoint.json"
            checkpoint.write_text(json.dumps({
                "run_id": "resume-run",
                "graph_id": "resume-flow",
                "inputs": {},
                "data": {"previous": "ok"},
                "next_node": "finish",
                "current_node": "previous",
                "status": "running",
                "error": None,
                "steps": 1,
            }), encoding="utf-8")
            context = GraphScheduler(graph, checkpoint_path=checkpoint).run(checkpoint=checkpoint)
            self.assertEqual(context.status, "completed")
            self.assertEqual(context.run_id, "resume-run")

    def test_scheduler_pauses_at_max_steps_and_resumes(self):
        graph = GraphDefinition.load(Path(__file__).parents[1] / "config" / "example-graph.json")
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "checkpoint.json"
            first = GraphScheduler(
                graph,
                checkpoint_path=checkpoint,
                max_steps=1,
            ).run({"structured": True})
            self.assertEqual(first.status, "paused")
            self.assertEqual(first.error, "maximum graph steps exceeded")
            self.assertEqual(first.next_node, "collect")

            resumed = GraphScheduler(
                graph,
                checkpoint_path=checkpoint,
            ).run({"structured": True}, checkpoint=checkpoint)
            self.assertEqual(resumed.status, "completed")
            self.assertEqual(resumed.steps, 3)

    def test_local_adapter_prepares_and_runs_task(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter = LocalAgentAdapter.for_project(Path(__file__).parents[1], state_dir=directory)
            plan = adapter.prepare("summarize a report", RouteSignals(structured=True))
            self.assertEqual(plan.decisions[0].skill_id, "domain.report-synthesis")
            result = adapter.run("summarize a report", {"structured": True})
            self.assertEqual(result.context.status, "completed")
            self.assertTrue(result.trace_path.exists())
            self.assertTrue(result.checkpoint_path.exists())

    def test_local_host_runs_and_captures_correction(self):
        with tempfile.TemporaryDirectory() as directory:
            host = LocalAgentHost.for_project(Path(__file__).parents[1], state_dir=directory)
            result = host.run_task(
                "summarize a report",
                {"structured": True},
                RouteSignals(structured=True),
                correction_subject="task-completion-state",
                correction_note="keep the report aligned before commit",
                correction_confidence=0.99,
            )
            self.assertEqual(result.run.context.status, "completed")
            self.assertIsNotNone(result.feedback)
            self.assertEqual(result.feedback.event_type, "correction")
            self.assertTrue(host.adapter.feedback_path.exists())

    def test_local_host_resumes_paused_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "host-checkpoint.json"
            host = LocalAgentHost.for_project(Path(__file__).parents[1], state_dir=directory)
            paused = host.run_task(
                "summarize a report",
                {"structured": True},
                RouteSignals(structured=True),
                checkpoint=checkpoint,
                max_steps=1,
            )
            self.assertEqual(paused.run.context.status, "paused")
            resumed = host.resume_task(
                "summarize a report",
                checkpoint,
                {"structured": True},
                RouteSignals(structured=True),
            )
            self.assertEqual(resumed.run.context.status, "completed")
            self.assertEqual(resumed.run.context.steps, 3)

    def test_local_host_requires_subject_for_correction_capture(self):
        with tempfile.TemporaryDirectory() as directory:
            host = LocalAgentHost.for_project(Path(__file__).parents[1], state_dir=directory)
            with self.assertRaisesRegex(ValueError, "correction_subject is required"):
                host.run_task(
                    "summarize a report",
                    {"structured": True},
                    correction_note="missing subject",
                )

    def test_local_adapter_routes_knowledge_ingestion_prep(self):
        adapter = LocalAgentAdapter.for_project(Path(__file__).parents[1])
        plan = adapter.prepare("Flowus ontology knowledge mapping sync")
        self.assertEqual(plan.decisions[0].skill_id, "project.knowledge-ingestion-prep")

    def test_local_adapter_feedback_is_reversible_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter = LocalAgentAdapter.for_project(Path(__file__).parents[1], state_dir=directory)
            adapter.record_feedback("correction", "project", "tone", "use concise language", 0.9)
            report = adapter.report()
            self.assertEqual(report["feedback_candidates"][0]["subject"], "tone")
            self.assertEqual(report["feedback_candidates"][0]["status"], "candidate")

    def test_adapter_contract_is_machine_readable(self):
        path = Path(__file__).parents[1] / "config" / "adapter-contract.json"
        contract = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(contract["name"], "local-agent-adapter")
        self.assertIn("prepare", contract["operations"])
        self.assertIn("host_run", contract["operations"])
        self.assertIn("checkpoint_saved", contract["events"])


if __name__ == "__main__":
    unittest.main()
