#!/usr/bin/env python3
"""Small, dependency-free CLI for the public Agent Manager examples."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_manager.entropy import audit
from agent_manager.adapter import LocalAgentAdapter
from agent_manager.file_audit import run_local_audit
from agent_manager.execution import GraphScheduler, RetryPolicy
from agent_manager.graph import GraphDefinition
from agent_manager.lifecycle import propose
from agent_manager.recorder import ExecutionRecorder
from agent_manager.registry import SkillRegistry
from agent_manager.router import Router, RouteSignals


def registry_path() -> Path:
    return ROOT / "config" / "skill-registry.json"


def load_registry() -> SkillRegistry:
    return SkillRegistry.load(registry_path())


def cmd_registry_list(_: argparse.Namespace) -> int:
    registry = load_registry()
    for skill in registry.skills:
        print(f"{skill.id}\t{skill.kind}\t{skill.layer}\t{skill.frequency}\t{skill.status}")
    return 0


def cmd_route(args: argparse.Namespace) -> int:
    signals = RouteSignals(
        structured=args.structured,
        deterministic=args.deterministic,
        low_latency=args.low_latency,
        creative=args.creative,
    )
    decisions = Router(load_registry()).decide(args.task, signals, args.top_k)
    print(json.dumps([decision.__dict__ for decision in decisions], indent=2))
    return 0


def cmd_graph_validate(args: argparse.Namespace) -> int:
    graph = GraphDefinition.load(args.file)
    errors = graph.validate()
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(f"valid: {graph.graph_id} v{graph.version}")
    return 0


def parse_input(value: str) -> dict:
    candidate = value.strip()
    if candidate.startswith("{") or candidate.startswith("["):
        parsed = json.loads(candidate)
    else:
        source = Path(value)
        if not source.exists():
            parsed = json.loads(value)
        else:
            parsed = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("graph input must be a JSON object")
    return parsed


def cmd_graph_run(args: argparse.Namespace) -> int:
    graph = GraphDefinition.load(args.file)
    inputs = parse_input(args.input)
    recorder = ExecutionRecorder(graph_id=graph.graph_id)
    if args.resume:
        checkpoint_path = Path(args.resume)
        checkpoint = checkpoint_path
    else:
        checkpoint_path = Path(args.checkpoint) if args.checkpoint else ROOT / ".agent-manager" / "checkpoints" / f"{recorder.run_id}.json"
        checkpoint = None
    scheduler = GraphScheduler(
        graph,
        recorder=recorder,
        retry_policy=RetryPolicy(args.max_attempts, args.backoff_seconds),
        checkpoint_path=checkpoint_path,
        max_steps=args.max_steps,
    )
    context = scheduler.run(inputs, checkpoint=checkpoint)
    trace_path = Path(args.trace) if args.trace else ROOT / ".agent-manager" / "traces" / f"{context.run_id}.json"
    recorder.save(trace_path)
    print(json.dumps({
        "status": context.status,
        "run_id": context.run_id,
        "graph_id": context.graph_id,
        "steps": context.steps,
        "error": context.error,
        "checkpoint": str(checkpoint_path),
        "trace": str(trace_path),
    }, ensure_ascii=False, indent=2))
    return 0 if context.status == "completed" else 1


def cmd_trace_show(args: argparse.Namespace) -> int:
    recorder = ExecutionRecorder.load(args.file)
    payload = {
        "summary": recorder.summary(),
        "events": [event.to_dict() for event in recorder.events],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def adapter_from_args(args: argparse.Namespace) -> LocalAgentAdapter:
    return LocalAgentAdapter.for_project(ROOT, state_dir=args.state_dir)


def adapter_signals(args: argparse.Namespace) -> RouteSignals:
    return RouteSignals(
        structured=getattr(args, "structured", False),
        deterministic=getattr(args, "deterministic", False),
        low_latency=getattr(args, "low_latency", False),
        creative=getattr(args, "creative", False),
    )


def load_entity_file(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, dict) and isinstance(payload.get("entities"), list):
        entities = payload["entities"]
        declared_count = payload.get("entity_count")
        if declared_count is not None and int(declared_count) != len(entities):
            raise ValueError("entity manifest entity_count does not match entities[]")
    elif isinstance(payload, list):
        entities = payload
    elif isinstance(payload, dict):
        entities = [payload]
    else:
        raise ValueError("entity file must contain an object or array")
    if not all(isinstance(entity, dict) for entity in entities):
        raise ValueError("entity file entities must be JSON objects")
    return entities


def cmd_adapter_prepare(args: argparse.Namespace) -> int:
    plan = adapter_from_args(args).prepare(args.task, adapter_signals(args), top_k=args.top_k)
    print(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2))
    return 0


def cmd_adapter_run(args: argparse.Namespace) -> int:
    adapter = adapter_from_args(args)
    result = adapter.run(
        args.task,
        parse_input(args.input),
        adapter_signals(args),
        graph_path=args.file,
        checkpoint=args.resume,
        trace=args.trace,
        max_attempts=args.max_attempts,
        backoff_seconds=args.backoff_seconds,
        max_steps=args.max_steps,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0 if result.context.status == "completed" else 1


def cmd_adapter_decide(args: argparse.Namespace) -> int:
    entities = load_entity_file(args.entity_file)
    result = adapter_from_args(args).decide_entities(entities)
    if args.summary_only:
        result = {key: value for key, value in result.items() if key != "proposals"}
        result["sample_proposals"] = adapter_from_args(args).decide_entities(entities[:3])["proposals"][:10]
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_adapter_execute(args: argparse.Namespace) -> int:
    entities = load_entity_file(args.entity_file)
    result = adapter_from_args(args).execute_entities(entities, checkpoint=args.checkpoint, max_items=args.max_items, checkpoint_every=args.checkpoint_every)
    if args.summary_only:
        result = {key: value for key, value in result.items() if key != "records"}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "completed" else 1


def cmd_adapter_promote_propose(args: argparse.Namespace) -> int:
    payload = json.loads(args.checkpoint.read_text(encoding="utf-8-sig"))
    records = payload.get("records", []) if isinstance(payload, dict) else payload
    result = adapter_from_args(args).propose_promotions(records, min_successes=args.min_successes, min_success_rate=args.min_success_rate)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_adapter_promote_review(args: argparse.Namespace) -> int:
    result = adapter_from_args(args).review_promotion(args.operation, args.decision, args.note)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_adapter_promote_plan(args: argparse.Namespace) -> int:
    result = adapter_from_args(args).create_promotion_manifest(
        args.operation,
        registry_path=args.registry_file,
        manifest_path=args.manifest_file,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_adapter_promote_approve(args: argparse.Namespace) -> int:
    result = adapter_from_args(args).approve_promotion_manifest(
        registry_path=args.registry_file,
        manifest_path=args.manifest_file,
        note=args.note,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_adapter_promote_apply(args: argparse.Namespace) -> int:
    result = adapter_from_args(args).apply_promotion(
        args.operation,
        registry_path=args.registry_file,
        manifest_path=args.manifest_file,
        write=args.write,
    )
    if args.plan_file:
        args.plan_file.parent.mkdir(parents=True, exist_ok=True)
        args.plan_file.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_adapter_promote_rollback(args: argparse.Namespace) -> int:
    result = adapter_from_args(args).rollback_promotion(
        registry_path=args.registry_file,
        manifest_path=args.manifest_file,
        write=args.write,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_adapter_feedback(args: argparse.Namespace) -> int:
    event = adapter_from_args(args).record_feedback(
        args.event_type,
        args.scope,
        args.subject,
        args.note,
        args.confidence,
    )
    print(json.dumps({"recorded": event.__dict__}, ensure_ascii=False, indent=2))
    return 0


def cmd_adapter_report(args: argparse.Namespace) -> int:
    report = adapter_from_args(args).report()
    if args.output:
        adapter_from_args(args).save_report(args.output)
        report["report"] = str(args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def cmd_adapter_audit_files(args: argparse.Namespace) -> int:
    result = run_local_audit(args.root, args.output_dir, stale_days=args.stale_days)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_audit(_: argparse.Namespace) -> int:
    registry = load_registry()
    findings = audit(list(registry.skills))
    payload = [finding.__dict__ for finding in findings]
    print(json.dumps(payload, indent=2))
    return 0


def cmd_lifecycle(_: argparse.Namespace) -> int:
    registry = load_registry()
    for skill in registry.skills:
        proposal = propose(skill)
        print(f"{proposal.skill_id}: {proposal.current_status}->{proposal.proposed_status}, "
              f"{proposal.current_frequency}->{proposal.proposed_frequency}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-manager")
    sub = parser.add_subparsers(dest="command", required=True)

    registry = sub.add_parser("registry")
    registry_sub = registry.add_subparsers(dest="registry_command", required=True)
    registry_list = registry_sub.add_parser("list")
    registry_list.set_defaults(func=cmd_registry_list)

    route = sub.add_parser("route")
    route.add_argument("--task", required=True)
    route.add_argument("--top-k", type=int, default=3)
    route.add_argument("--structured", action="store_true")
    route.add_argument("--deterministic", action="store_true")
    route.add_argument("--low-latency", action="store_true")
    route.add_argument("--creative", action="store_true")
    route.set_defaults(func=cmd_route)

    graph = sub.add_parser("graph")
    graph_sub = graph.add_subparsers(dest="graph_command", required=True)
    validate = graph_sub.add_parser("validate")
    validate.add_argument("--file", required=True, type=Path)
    validate.set_defaults(func=cmd_graph_validate)
    run = graph_sub.add_parser("run")
    run.add_argument("--file", required=True, type=Path)
    run.add_argument("--input", default="{}", help="JSON object or path to a JSON object")
    run.add_argument("--resume", type=Path)
    run.add_argument("--trace", type=Path)
    run.add_argument("--checkpoint", type=Path)
    run.add_argument("--max-attempts", type=int, default=1)
    run.add_argument("--backoff-seconds", type=float, default=0.0)
    run.add_argument("--max-steps", type=int, default=100)
    run.set_defaults(func=cmd_graph_run)

    trace = sub.add_parser("trace")
    trace_sub = trace.add_subparsers(dest="trace_command", required=True)
    show = trace_sub.add_parser("show")
    show.add_argument("--file", required=True, type=Path)
    show.set_defaults(func=cmd_trace_show)

    adapter = sub.add_parser("adapter")
    adapter_sub = adapter.add_subparsers(dest="adapter_command", required=True)
    prepare = adapter_sub.add_parser("prepare")
    prepare.add_argument("--task", required=True)
    prepare.add_argument("--top-k", type=int, default=3)
    prepare.add_argument("--state-dir", type=Path, default=ROOT / ".agent-manager")
    for option in ("structured", "deterministic", "low_latency", "creative"):
        prepare.add_argument(f"--{option.replace('_', '-')}", action="store_true", dest=option)
    prepare.set_defaults(func=cmd_adapter_prepare)

    adapter_run = adapter_sub.add_parser("run")
    adapter_run.add_argument("--task", required=True)
    adapter_run.add_argument("--input", default="{}")
    adapter_run.add_argument("--file", type=Path)
    adapter_run.add_argument("--resume", type=Path)
    adapter_run.add_argument("--trace", type=Path)
    adapter_run.add_argument("--state-dir", type=Path, default=ROOT / ".agent-manager")
    adapter_run.add_argument("--max-attempts", type=int, default=1)
    adapter_run.add_argument("--backoff-seconds", type=float, default=0.0)
    adapter_run.add_argument("--max-steps", type=int, default=100)
    for option in ("structured", "deterministic", "low_latency", "creative"):
        adapter_run.add_argument(f"--{option.replace('_', '-')}", action="store_true", dest=option)
    adapter_run.set_defaults(func=cmd_adapter_run)

    decide = adapter_sub.add_parser("decide")
    decide.add_argument("--entity-file", required=True, type=Path)
    decide.add_argument("--summary-only", action="store_true")
    decide.add_argument("--state-dir", type=Path, default=ROOT / ".agent-manager")
    decide.set_defaults(func=cmd_adapter_decide)

    execute = adapter_sub.add_parser("execute")
    execute.add_argument("--entity-file", required=True, type=Path)
    execute.add_argument("--checkpoint", type=Path)
    execute.add_argument("--max-items", type=int)
    execute.add_argument("--checkpoint-every", type=int, default=100)
    execute.add_argument("--summary-only", action="store_true")
    execute.add_argument("--state-dir", type=Path, default=ROOT / ".agent-manager")
    execute.set_defaults(func=cmd_adapter_execute)

    promote = adapter_sub.add_parser("promote")
    promote_sub = promote.add_subparsers(dest="promote_command", required=True)
    propose_promotion = promote_sub.add_parser("propose")
    propose_promotion.add_argument("--checkpoint", required=True, type=Path)
    propose_promotion.add_argument("--min-successes", type=int, default=3)
    propose_promotion.add_argument("--min-success-rate", type=float, default=0.9)
    propose_promotion.add_argument("--state-dir", type=Path, default=ROOT / ".agent-manager")
    propose_promotion.set_defaults(func=cmd_adapter_promote_propose)
    review_promotion = promote_sub.add_parser("review")
    review_promotion.add_argument("--operation", required=True)
    review_promotion.add_argument("--decision", required=True, choices=["approve", "reject"])
    review_promotion.add_argument("--note", required=True)
    review_promotion.add_argument("--state-dir", type=Path, default=ROOT / ".agent-manager")
    review_promotion.set_defaults(func=cmd_adapter_promote_review)
    plan_promotion = promote_sub.add_parser("plan")
    plan_promotion.add_argument("--operation", required=True)
    plan_promotion.add_argument("--registry-file", type=Path, default=ROOT / "config" / "skill-registry.json")
    plan_promotion.add_argument("--manifest-file", required=True, type=Path)
    plan_promotion.add_argument("--state-dir", type=Path, default=ROOT / ".agent-manager")
    plan_promotion.set_defaults(func=cmd_adapter_promote_plan)
    approve_promotion = promote_sub.add_parser("approve")
    approve_promotion.add_argument("--registry-file", type=Path, default=ROOT / "config" / "skill-registry.json")
    approve_promotion.add_argument("--manifest-file", required=True, type=Path)
    approve_promotion.add_argument("--note", required=True)
    approve_promotion.add_argument("--state-dir", type=Path, default=ROOT / ".agent-manager")
    approve_promotion.set_defaults(func=cmd_adapter_promote_approve)
    apply_promotion = promote_sub.add_parser("apply")
    apply_promotion.add_argument("--operation")
    apply_promotion.add_argument("--registry-file", type=Path, default=ROOT / "config" / "skill-registry.json")
    apply_promotion.add_argument("--manifest-file", type=Path)
    apply_promotion.add_argument("--plan-file", type=Path)
    apply_promotion.add_argument("--write", action="store_true")
    apply_promotion.add_argument("--state-dir", type=Path, default=ROOT / ".agent-manager")
    apply_promotion.set_defaults(func=cmd_adapter_promote_apply)
    rollback_promotion = promote_sub.add_parser("rollback")
    rollback_promotion.add_argument("--registry-file", type=Path, default=ROOT / "config" / "skill-registry.json")
    rollback_promotion.add_argument("--manifest-file", required=True, type=Path)
    rollback_promotion.add_argument("--write", action="store_true")
    rollback_promotion.add_argument("--state-dir", type=Path, default=ROOT / ".agent-manager")
    rollback_promotion.set_defaults(func=cmd_adapter_promote_rollback)

    feedback = adapter_sub.add_parser("feedback")
    feedback.add_argument("--event-type", required=True, choices=["undo", "redo", "pitfall", "fallback", "correction", "approval"])
    feedback.add_argument("--scope", required=True, choices=["profile", "project"])
    feedback.add_argument("--subject", required=True)
    feedback.add_argument("--note", required=True)
    feedback.add_argument("--confidence", type=float, default=0.5)
    feedback.add_argument("--state-dir", type=Path, default=ROOT / ".agent-manager")
    feedback.set_defaults(func=cmd_adapter_feedback)

    report = adapter_sub.add_parser("report")
    report.add_argument("--output", type=Path)
    report.add_argument("--state-dir", type=Path, default=ROOT / ".agent-manager")
    report.set_defaults(func=cmd_adapter_report)

    audit_files = adapter_sub.add_parser("audit-files")
    audit_files.add_argument("--root", required=True, type=Path)
    audit_files.add_argument("--output-dir", required=True, type=Path)
    audit_files.add_argument("--stale-days", type=float, default=2.0)
    audit_files.set_defaults(func=cmd_adapter_audit_files)

    audit_command = sub.add_parser("audit")
    audit_command.set_defaults(func=cmd_audit)

    lifecycle = sub.add_parser("lifecycle")
    lifecycle.set_defaults(func=cmd_lifecycle)
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    raise SystemExit(args.func(args))
