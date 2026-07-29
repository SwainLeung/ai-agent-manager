import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

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


if __name__ == "__main__":
    unittest.main()
