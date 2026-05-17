from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import yaml

from marama_route import RoutingRequest, load_model_registry

from .audit import build_audit_record
from .planner import plan_coding_turn
from .platform import (
    build_capsule_summary,
    build_opencode_workspace_config,
    build_policy_matrix,
    build_turn_brief,
    check_tool_request,
)
from .policy import DataCapsule, SovereignRequest, SovereigntyPolicyEngine


def _load_mapping(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".json":
        payload = json.loads(text)
    else:
        payload = yaml.safe_load(text)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected mapping in {path}")
    return payload


def _evaluate(args: argparse.Namespace) -> int:
    capsule = DataCapsule.from_payload(_load_mapping(args.capsule))
    request = SovereignRequest.from_payload(_load_mapping(args.request))
    decision = SovereigntyPolicyEngine().evaluate(capsule, request)
    payload: dict[str, Any] = {"decision": decision.to_dict()}
    if args.audit:
        payload["audit_record"] = build_audit_record(capsule, request, decision).to_dict()
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if decision.allowed or args.allow_denied_exit_zero else 2


def _plan_turn(args: argparse.Namespace) -> int:
    capsule = DataCapsule.from_payload(_load_mapping(args.capsule))
    request = SovereignRequest.from_payload(_load_mapping(args.request))
    routing_request = RoutingRequest.from_payload(_load_mapping(args.route_request))
    models = load_model_registry(args.registry)
    plan = plan_coding_turn(capsule, request, routing_request, models)
    payload = plan.to_dict()
    payload["turn_brief"] = build_turn_brief(payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if plan.allowed or args.allow_blocked_exit_zero else 2


def _policy_matrix(args: argparse.Namespace) -> int:
    result = build_policy_matrix(_load_mapping(args.capsule), _load_mapping(args.request))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["blocked_count"] >= 0 else 2


def _tool_check(args: argparse.Namespace) -> int:
    tool_payload = {
        "tool_name": args.tool_name,
        "action": args.action,
        "writes_files": args.writes_files,
        "exports_data": args.exports_data,
        "trains_model": args.trains_model,
        "human_approved": args.human_approved,
    }
    result = check_tool_request(
        _load_mapping(args.capsule),
        _load_mapping(args.request),
        tool_payload,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] or args.allow_blocked_exit_zero else 2


def _capsule_summary(args: argparse.Namespace) -> int:
    print(json.dumps(build_capsule_summary(_load_mapping(args.capsule)), indent=2, sort_keys=True))
    return 0


def _opencode_config(args: argparse.Namespace) -> int:
    print(
        json.dumps(
            build_opencode_workspace_config(base_url=args.base_url, model=args.model),
            indent=2,
            sort_keys=True,
        ),
    )
    return 0


def _ui(args: argparse.Namespace) -> int:
    from .ui import run_ui

    return run_ui(
        capsule_path=args.capsule,
        request_path=args.request,
        route_request_path=args.route_request,
        registry_path=args.registry,
        host=args.host,
        port=args.port,
        open_browser=args.open,
        smoke=args.smoke,
    )


def _serve(args: argparse.Namespace) -> int:
    from .server import serve_service

    return serve_service(
        capsule_path=args.capsule,
        request_path=args.request,
        route_request_path=args.route_request,
        registry_path=args.registry,
        ledger_path=args.ledger,
        host=args.host,
        port=args.port,
        open_browser=args.open,
        smoke=args.smoke,
    )


def _audit(args: argparse.Namespace) -> int:
    from .ledger import AuditLedger, default_ledger_path

    ledger = AuditLedger(args.ledger or default_ledger_path())
    print(json.dumps({"ok": True, "ledger_path": str(ledger.path), "records": ledger.tail(args.limit)}, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="abteex-sovereigncode",
        description="Evaluate AbteeX SovereignCode Data Capsule policies.",
    )
    subparsers = parser.add_subparsers(dest="command")
    evaluate = subparsers.add_parser("evaluate", help="Evaluate a governed code/data request.")
    evaluate.add_argument("--capsule", type=Path, required=True, help="Data Capsule JSON/YAML file.")
    evaluate.add_argument("--request", type=Path, required=True, help="Sovereign request JSON/YAML file.")
    evaluate.add_argument("--audit", action=argparse.BooleanOptionalAction, default=True)
    evaluate.add_argument(
        "--allow-denied-exit-zero",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Return exit code 0 even when policy denies the request.",
    )
    evaluate.set_defaults(handler=_evaluate)

    plan_turn = subparsers.add_parser(
        "plan-turn",
        help="Plan a governed coding-agent turn with model routing.",
    )
    plan_turn.add_argument("--capsule", type=Path, required=True, help="Data Capsule JSON/YAML file.")
    plan_turn.add_argument("--request", type=Path, required=True, help="Sovereign request JSON/YAML file.")
    plan_turn.add_argument(
        "--route-request",
        type=Path,
        required=True,
        help="MaramaRoute routing request JSON/YAML file.",
    )
    plan_turn.add_argument(
        "--registry",
        type=Path,
        required=True,
        help="MaramaRoute model registry JSON.",
    )
    plan_turn.add_argument(
        "--allow-blocked-exit-zero",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Return exit code 0 even when the planned turn is blocked.",
    )
    plan_turn.set_defaults(handler=_plan_turn)

    matrix = subparsers.add_parser(
        "policy-matrix",
        help="Evaluate the built-in tool/action matrix against a capsule.",
    )
    matrix.add_argument("--capsule", type=Path, required=True, help="Data Capsule JSON/YAML file.")
    matrix.add_argument("--request", type=Path, required=True, help="Base sovereign request JSON/YAML file.")
    matrix.set_defaults(handler=_policy_matrix)

    tool_check = subparsers.add_parser(
        "tool-check",
        help="Check one tool/action request before execution.",
    )
    tool_check.add_argument("--capsule", type=Path, required=True, help="Data Capsule JSON/YAML file.")
    tool_check.add_argument("--request", type=Path, required=True, help="Base sovereign request JSON/YAML file.")
    tool_check.add_argument("--tool-name", default="workspace_reader")
    tool_check.add_argument("--action", default="read_context")
    tool_check.add_argument("--writes-files", action=argparse.BooleanOptionalAction, default=False)
    tool_check.add_argument("--exports-data", action=argparse.BooleanOptionalAction, default=False)
    tool_check.add_argument("--trains-model", action=argparse.BooleanOptionalAction, default=False)
    tool_check.add_argument("--human-approved", action=argparse.BooleanOptionalAction, default=False)
    tool_check.add_argument("--allow-blocked-exit-zero", action=argparse.BooleanOptionalAction, default=False)
    tool_check.set_defaults(handler=_tool_check)

    capsule_summary = subparsers.add_parser(
        "capsule-summary",
        help="Summarise Data Capsule controls and risk flags.",
    )
    capsule_summary.add_argument("--capsule", type=Path, required=True, help="Data Capsule JSON/YAML file.")
    capsule_summary.set_defaults(handler=_capsule_summary)

    opencode = subparsers.add_parser(
        "opencode-config",
        help="Emit an OpenCode-compatible SovereignCode workspace config.",
    )
    opencode.add_argument("--base-url", default="http://127.0.0.1:8787/v1")
    opencode.add_argument("--model", default="lumynax-infused-qwen3-coder-30b-a3b-gguf")
    opencode.set_defaults(handler=_opencode_config)

    ui = subparsers.add_parser(
        "ui",
        help="Launch the local SovereignCode browser platform.",
    )
    ui.add_argument("--capsule", type=Path, default=None, help="Data Capsule JSON/YAML file.")
    ui.add_argument("--request", type=Path, default=None, help="Sovereign request JSON/YAML file.")
    ui.add_argument("--route-request", type=Path, default=None, help="MaramaRoute routing request JSON.")
    ui.add_argument("--registry", type=Path, default=None, help="MaramaRoute model registry JSON.")
    ui.add_argument("--host", type=str, default="127.0.0.1")
    ui.add_argument("--port", type=int, default=8788)
    ui.add_argument("--open", action=argparse.BooleanOptionalAction, default=False)
    ui.add_argument("--smoke", action=argparse.BooleanOptionalAction, default=False)
    ui.set_defaults(handler=_ui)

    serve = subparsers.add_parser(
        "serve",
        help="Run the local SovereignCode policy API, audit ledger, and browser console.",
    )
    serve.add_argument("--capsule", type=Path, default=None, help="Data Capsule JSON/YAML file.")
    serve.add_argument("--request", type=Path, default=None, help="Sovereign request JSON/YAML file.")
    serve.add_argument("--route-request", type=Path, default=None, help="MaramaRoute routing request JSON.")
    serve.add_argument("--registry", type=Path, default=None, help="MaramaRoute model registry JSON.")
    serve.add_argument("--ledger", type=Path, default=None, help="Audit ledger JSONL path.")
    serve.add_argument("--host", type=str, default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8788)
    serve.add_argument("--open", action=argparse.BooleanOptionalAction, default=False)
    serve.add_argument("--smoke", action=argparse.BooleanOptionalAction, default=False)
    serve.set_defaults(handler=_serve)

    audit = subparsers.add_parser("audit", help="Read the local SovereignCode audit ledger.")
    audit.add_argument("--ledger", type=Path, default=None, help="Audit ledger JSONL path.")
    audit.add_argument("--limit", type=int, default=25)
    audit.set_defaults(handler=_audit)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 0
    return int(handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
