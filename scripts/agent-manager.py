#!/usr/bin/env python3
"""Small, dependency-free CLI for the public Agent Manager examples."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_manager.entropy import audit
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

    audit_command = sub.add_parser("audit")
    audit_command.set_defaults(func=cmd_audit)

    lifecycle = sub.add_parser("lifecycle")
    lifecycle.set_defaults(func=cmd_lifecycle)
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    raise SystemExit(args.func(args))
