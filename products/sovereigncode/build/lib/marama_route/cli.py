from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .gateway import build_models_response, route_chat_payload
from .platform import (
    build_opencode_provider_config,
    build_registry_analytics,
    catalog_models,
    compare_models,
    route_scenario_matrix,
)
from .registry import RoutingRequest, load_model_registry
from .router import SovereignModelRouter


def _load_json_mapping(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected mapping in {path}")
    return payload


def _route(args: argparse.Namespace) -> int:
    models = load_model_registry(args.registry)
    payload = _load_json_mapping(args.request)
    decision = SovereignModelRouter(models).route(RoutingRequest.from_payload(payload))
    print(json.dumps(decision.to_dict(), indent=2, sort_keys=True))
    return 0 if decision.selected_model is not None else 2


def _models(args: argparse.Namespace) -> int:
    models = load_model_registry(args.registry)
    print(json.dumps(build_models_response(models), indent=2, sort_keys=True))
    return 0


def _chat_dry_run(args: argparse.Namespace) -> int:
    models = load_model_registry(args.registry)
    payload = _load_json_mapping(args.request)
    result = route_chat_payload(payload, models)
    print(json.dumps(result, indent=2, sort_keys=True))
    selected = result["route_decision"]["selected_model"]
    return 0 if selected is not None else 2


def _catalog(args: argparse.Namespace) -> int:
    models = load_model_registry(args.registry)
    result = catalog_models(
        models,
        {
            "search": args.search,
            "task_type": args.task,
            "runtime": args.runtime,
            "modality": args.modality,
            "jurisdiction": args.jurisdiction,
            "min_context_tokens": args.min_context_tokens,
            "requires_json": args.requires_json,
            "requires_tools": args.requires_tools,
            "requires_local": args.requires_local,
            "limit": args.limit,
        },
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def _compare(args: argparse.Namespace) -> int:
    models = load_model_registry(args.registry)
    model_ids = [item.strip() for value in args.model for item in value.split(",") if item.strip()]
    request = _load_json_mapping(args.request) if args.request else None
    result = compare_models(models, model_ids, request)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 2


def _matrix(args: argparse.Namespace) -> int:
    models = load_model_registry(args.registry)
    result = route_scenario_matrix(models)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] or args.allow_blocked_exit_zero else 2


def _analytics(args: argparse.Namespace) -> int:
    print(json.dumps(build_registry_analytics(load_model_registry(args.registry)), indent=2, sort_keys=True))
    return 0


def _opencode_config(args: argparse.Namespace) -> int:
    models = load_model_registry(args.registry)
    result = build_opencode_provider_config(models, base_url=args.base_url)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def _ui(args: argparse.Namespace) -> int:
    from .ui import run_ui

    return run_ui(
        registry_path=args.registry,
        host=args.host,
        port=args.port,
        open_browser=args.open,
        smoke=args.smoke,
    )


def _serve(args: argparse.Namespace) -> int:
    from .server import serve_gateway

    return serve_gateway(
        registry_path=args.registry,
        config_path=args.config,
        host=args.host,
        port=args.port,
        open_browser=args.open,
        smoke=args.smoke,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lumynax-marama-route",
        description="Route requests across LumynaX sovereign model releases.",
    )
    subparsers = parser.add_subparsers(dest="command")
    route = subparsers.add_parser("route", help="Select a LumynaX model for a request.")
    route.add_argument("--registry", type=Path, required=True, help="MaramaRoute model registry JSON.")
    route.add_argument("--request", type=Path, required=True, help="Routing request JSON.")
    route.set_defaults(handler=_route)

    models = subparsers.add_parser(
        "models",
        help="Emit an OpenAI-compatible /v1/models response.",
    )
    models.add_argument("--registry", type=Path, required=True, help="MaramaRoute model registry JSON.")
    models.set_defaults(handler=_models)

    chat = subparsers.add_parser(
        "chat-dry-run",
        help="Route an OpenAI-compatible chat request without invoking a backend.",
    )
    chat.add_argument("--registry", type=Path, required=True, help="MaramaRoute model registry JSON.")
    chat.add_argument("--request", type=Path, required=True, help="OpenAI chat request JSON.")
    chat.set_defaults(handler=_chat_dry_run)

    catalog = subparsers.add_parser(
        "catalog",
        help="Search and filter the MaramaRoute model catalog.",
    )
    catalog.add_argument("--registry", type=Path, required=True, help="MaramaRoute model registry JSON.")
    catalog.add_argument("--search", default="")
    catalog.add_argument("--task", default="")
    catalog.add_argument("--runtime", default="")
    catalog.add_argument("--modality", default="")
    catalog.add_argument("--jurisdiction", default="NZ")
    catalog.add_argument("--min-context-tokens", type=int, default=0)
    catalog.add_argument("--requires-json", action=argparse.BooleanOptionalAction, default=False)
    catalog.add_argument("--requires-tools", action=argparse.BooleanOptionalAction, default=False)
    catalog.add_argument("--requires-local", action=argparse.BooleanOptionalAction, default=False)
    catalog.add_argument("--limit", type=int, default=25)
    catalog.set_defaults(handler=_catalog)

    compare = subparsers.add_parser(
        "compare",
        help="Compare routed fit for selected model ids.",
    )
    compare.add_argument("--registry", type=Path, required=True, help="MaramaRoute model registry JSON.")
    compare.add_argument("--model", action="append", required=True, help="Model id, repeatable or comma-separated.")
    compare.add_argument("--request", type=Path, default=None, help="Optional routing request JSON.")
    compare.set_defaults(handler=_compare)

    matrix = subparsers.add_parser(
        "matrix",
        help="Run the built-in sovereign routing scenario matrix.",
    )
    matrix.add_argument("--registry", type=Path, required=True, help="MaramaRoute model registry JSON.")
    matrix.add_argument("--allow-blocked-exit-zero", action=argparse.BooleanOptionalAction, default=False)
    matrix.set_defaults(handler=_matrix)

    analytics = subparsers.add_parser("analytics", help="Summarise registry coverage.")
    analytics.add_argument("--registry", type=Path, required=True, help="MaramaRoute model registry JSON.")
    analytics.set_defaults(handler=_analytics)

    opencode = subparsers.add_parser(
        "opencode-config",
        help="Emit an OpenCode-compatible MaramaRoute provider config.",
    )
    opencode.add_argument("--registry", type=Path, required=True, help="MaramaRoute model registry JSON.")
    opencode.add_argument("--base-url", default="http://127.0.0.1:8787/v1")
    opencode.set_defaults(handler=_opencode_config)

    ui = subparsers.add_parser(
        "ui",
        help="Launch the local MaramaRoute browser platform.",
    )
    ui.add_argument("--registry", type=Path, default=None, help="MaramaRoute model registry JSON.")
    ui.add_argument("--host", type=str, default="127.0.0.1")
    ui.add_argument("--port", type=int, default=8787)
    ui.add_argument("--open", action=argparse.BooleanOptionalAction, default=False)
    ui.add_argument("--smoke", action=argparse.BooleanOptionalAction, default=False)
    ui.set_defaults(handler=_ui)

    serve = subparsers.add_parser(
        "serve",
        help="Run the local OpenAI-compatible MaramaRoute gateway and browser console.",
    )
    serve.add_argument("--registry", type=Path, default=None, help="MaramaRoute model registry JSON.")
    serve.add_argument("--config", type=Path, default=None, help="Gateway backend config JSON.")
    serve.add_argument("--host", type=str, default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8787)
    serve.add_argument("--open", action=argparse.BooleanOptionalAction, default=False)
    serve.add_argument("--smoke", action=argparse.BooleanOptionalAction, default=False)
    serve.set_defaults(handler=_serve)
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
