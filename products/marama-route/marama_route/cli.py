from __future__ import annotations

import argparse
import importlib.metadata as importlib_metadata
import importlib.util
import json
import os
import platform as py_platform
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .compat import build_compatibility_matrix, model_runtime_compatibility
from .download import (
    default_cache_root,
    list_pulled_models,
    load_chat_session,
    local_model_files,
    model_cache_dir,
    pull_model,
    resolve_model,
    run_pulled_model,
)
from .gateway import build_models_response, route_chat_payload
from .ops import (
    cache_report,
    default_state_root,
    delete_alias,
    diff_model_registry,
    estimate_model_download,
    export_audit_receipts,
    export_session_markdown,
    hardware_recommendations,
    inspect_hardware,
    list_audit_receipts,
    load_aliases,
    load_session,
    prune_cache,
    remove_cached_model,
    resolve_alias,
    save_session,
    set_alias,
    set_favorite,
    show_audit_receipt,
    verify_cache,
    write_audit_receipt,
)
from .platform import (
    build_agent_bridge_config,
    build_opencode_provider_config,
    build_registry_analytics,
    catalog_models,
    compare_models,
    recommend_model,
    render_hpe_apptainer_definition,
    render_hpe_gateway_config,
    render_hpe_readme,
    render_hpe_slurm_script,
    route_scenario_matrix,
)
from .registry import RoutingRequest, load_model_registry
from .router import SovereignModelRouter
from .ui import default_registry_path

CHAT_COMMANDS = {"/bye", "/exit", "/q", "/quit"}
_HF_TOKEN_ENV_NAMES = ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "HUGGINGFACE_HUB_TOKEN")
MODEL_PICKER_COMMANDS = {
    "/all",
    "/back",
    "/categories",
    "/catalog",
    "/families",
    "/family",
    "/help",
    "/h",
    "/hardware",
    "/local",
    "/menu",
    "/models",
    "/next",
    "/prev",
    "/pull",
    "/runnable",
    "/search",
    "/switch",
    "/use",
    "/vllm",
    "/nim",
    "/nem",
    "/nemo",
    "/recommended",
    "/recommend",
    "?",
}
MODEL_PICKER_PAGE_SIZE = 12
_DEPLOYMENT_USABLE_STATUSES = {"supported", "candidate", "experimental"}
_DEPLOYMENT_PATHWAY_STATUSES = _DEPLOYMENT_USABLE_STATUSES | {"convert_required"}
_DEPLOYMENT_TARGET_LABELS = {
    "vllm": "vLLM",
    "nvidia_nim": "NVIDIA NIM",
    "nvidia_nemo": "NVIDIA NeMo/NEM",
}


class _ExitConversation(Exception):
    pass


def _load_json_mapping(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected mapping in {path}")
    return payload


def _registry_path(args: argparse.Namespace) -> Path:
    return args.registry or default_registry_path()


def _route(args: argparse.Namespace) -> int:
    models = load_model_registry(_registry_path(args))
    payload = _load_json_mapping(args.request)
    decision = SovereignModelRouter(models).route(RoutingRequest.from_payload(payload))
    print(json.dumps(decision.to_dict(), indent=2, sort_keys=True))
    return 0 if decision.selected_model is not None else 2


def _models(args: argparse.Namespace) -> int:
    models = load_model_registry(_registry_path(args))
    filtered = _filter_models_command(models, args)
    if args.limit > 0:
        filtered = filtered[: args.limit]
    if args.format == "table":
        _print_models_table(filtered)
        return 0
    response = build_models_response(tuple(filtered))
    response["count"] = len(filtered)
    response["total_count"] = len(models)
    print(json.dumps(response, indent=2, sort_keys=True))
    return 0


def _chat_dry_run(args: argparse.Namespace) -> int:
    models = load_model_registry(_registry_path(args))
    payload = _load_json_mapping(args.request)
    result = route_chat_payload(payload, models)
    print(json.dumps(result, indent=2, sort_keys=True))
    selected = result["route_decision"]["selected_model"]
    return 0 if selected is not None else 2


def _catalog(args: argparse.Namespace) -> int:
    models = load_model_registry(_registry_path(args))
    result = catalog_models(
        models,
        {
            "search": args.search,
            "task_type": args.task,
            "runtime": args.runtime,
            "family": args.family,
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


def _filter_models_command(models: tuple[Any, ...], args: argparse.Namespace) -> list[Any]:
    search = str(args.search or "").strip().lower()
    family = str(args.family or "").strip().lower()
    runtime = str(args.runtime or "").strip().lower()
    tag = str(args.tag or "").strip().lower()
    filtered: list[Any] = []
    for model in models:
        tags = {str(item).lower() for item in model.tags}
        searchable = " ".join(
            [
                model.model_id,
                model.repo_id,
                model.family,
                model.runtime,
                " ".join(sorted(tags)),
            ],
        ).lower()
        if search and search not in searchable:
            continue
        if family and family not in model.family.lower() and family not in tags:
            continue
        if runtime and runtime not in model.runtime.lower():
            continue
        if tag and tag not in tags:
            continue
        filtered.append(model)
    return filtered


def _print_models_table(models: list[Any]) -> None:
    if not models:
        print("No matching LumynaX models.")
        return
    print(f"{'model':42} {'runtime':22} {'family':14} {'tags'}")
    print("-" * 110)
    for model in models:
        tags = ", ".join(list(model.tags)[:6])
        print(f"{model.model_id[:42]:42} {model.runtime[:22]:22} {model.family[:14]:14} {tags}")


def _compat(args: argparse.Namespace) -> int:
    models = load_model_registry(_registry_path(args))
    if args.model:
        model = _resolve_cli_model(models, args.model)
        result = {
            "ok": True,
            "model": {
                "model_id": model.model_id,
                "repo_id": model.repo_id,
                "runtime": model.runtime,
                "family": model.family,
                "modalities": list(model.modalities),
                "primary_artifact": model.primary_artifact,
                "tags": list(model.tags),
            },
            "runtime_compatibility": model_runtime_compatibility(model),
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    matrix = build_compatibility_matrix(
        models,
        target=args.target,
        status=args.status,
        limit=args.limit,
    )
    if args.format == "json":
        print(json.dumps(matrix, indent=2, sort_keys=True))
    else:
        _print_compatibility_table(matrix)
    return 0


def _categories(args: argparse.Namespace) -> int:
    models = load_model_registry(_registry_path(args))
    result = _category_summary(models, limit=args.limit)
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        _print_category_summary(result)
    return 0


def _compare(args: argparse.Namespace) -> int:
    models = load_model_registry(_registry_path(args))
    model_ids = [item.strip() for value in args.model for item in value.split(",") if item.strip()]
    request = _load_json_mapping(args.request) if args.request else None
    result = compare_models(models, model_ids, request)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 2


def _matrix(args: argparse.Namespace) -> int:
    models = load_model_registry(_registry_path(args))
    result = route_scenario_matrix(models)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] or args.allow_blocked_exit_zero else 2


def _analytics(args: argparse.Namespace) -> int:
    print(json.dumps(build_registry_analytics(load_model_registry(_registry_path(args))), indent=2, sort_keys=True))
    return 0


def _opencode_config(args: argparse.Namespace) -> int:
    models = load_model_registry(_registry_path(args))
    result = build_opencode_provider_config(models, base_url=args.base_url)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def _recommend(args: argparse.Namespace) -> int:
    models = load_model_registry(_registry_path(args))
    prompt = " ".join(args.prompt).strip() if args.prompt else args.prompt_text
    modalities = tuple(item.strip().lower() for item in args.modality.split(",") if item.strip())
    result = recommend_model(
        models,
        prompt=prompt,
        task_type=args.task,
        jurisdiction=args.jurisdiction,
        data_sensitivity=args.sensitivity,
        min_context_tokens=args.min_context_tokens,
        requires_local=args.requires_local,
        requires_json=args.requires_json,
        requires_tools=args.requires_tools,
        modalities=modalities or ("text",),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 2


def _doctor(args: argparse.Namespace) -> int:
    models = load_model_registry(_registry_path(args))
    cache_root = args.cache_dir or default_cache_root()
    pulled = list_pulled_models(cache_root)
    hardware = inspect_hardware(cache_root) if args.hardware else None
    checks = {
        "python": {
            "ok": sys.version_info >= (3, 11),
            "version": py_platform.python_version(),
            "executable": sys.executable,
        },
        "package": {
            "ok": True,
            "version": _installed_version(),
        },
        "registry": {
            "ok": bool(models),
            "count": len(models),
            "path": str(_registry_path(args)),
            "chat_capable": sum(1 for model in models if _is_chat_runnable(model)),
        },
        "cache": {
            "ok": True,
            "path": str(cache_root),
            "pulled_count": pulled["count"],
        },
        "huggingface_hub": {
            "ok": importlib.util.find_spec("huggingface_hub") is not None,
            "hf_cli": shutil.which("hf") or shutil.which("huggingface-cli") or "",
            "token_env_present": any(os.getenv(name) for name in _HF_TOKEN_ENV_NAMES),
        },
        "llama_cpp": {
            "ok": importlib.util.find_spec("llama_cpp") is not None,
            "needed_for": "local GGUF chat and run",
        },
    }
    if args.online:
        checks["huggingface_hub"]["whoami"] = _hf_whoami_status()
    result = {
        "ok": all(bool(item.get("ok")) for item in checks.values()),
        "product": "LumynaX MaramaRoute",
        "checks": checks,
        "hardware": hardware,
        "next_commands": {
            "install_runtime": "python -m pip install llama-cpp-python",
            "choose_model": "MaramaRoute chat",
            "pull_small_model": "MaramaRoute pull qwen25-05b",
            "run_gateway": "MaramaRoute serve --port 8787",
        },
    }
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        _print_doctor(result)
    return 0 if result["ok"] or args.allow_warnings else 2


def _agent_config(args: argparse.Namespace) -> int:
    models = load_model_registry(_registry_path(args))
    result = build_agent_bridge_config(
        models,
        target=args.target,
        base_url=args.base_url,
        host=args.host,
        port=args.port,
        cache_dir=args.cache_dir,
        model_id=args.model or "",
    )
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


def _hpe_job(args: argparse.Namespace) -> int:
    models = load_model_registry(_registry_path(args))
    model = _resolve_cli_model(models, args.model) if args.model else _recommended_model(models)
    script = render_hpe_slurm_script(
        model_id=model.model_id,
        repo_id=model.repo_id,
        model_runtime=model.runtime,
        mode=args.mode,
        prompt=args.prompt_text,
        port=args.port,
        backend=args.backend,
        backend_port=args.backend_port,
        backend_base_url=args.backend_base_url,
        backend_model=args.backend_model,
        backend_command=args.backend_command,
        api_key_env=args.api_key_env,
        vllm_args=args.vllm_args,
        cache_dir=args.cache_dir,
        job_name=args.job_name,
        partition=args.partition,
        time_limit=args.time,
        cpus=args.cpus,
        memory=args.memory,
        gpus=args.gpus,
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(script, encoding="utf-8")
    else:
        print(script, end="")
    return 0


def _init(args: argparse.Namespace) -> int:
    models = load_model_registry(_registry_path(args))
    model = _resolve_cli_model(models, args.model) if args.model else _recommended_model(models)
    state_root = args.state_dir or default_state_root()
    state_root.mkdir(parents=True, exist_ok=True)
    self_test = _init_self_test(models, model, args) if args.self_test else {"enabled": False}
    config = {
        "product": "LumynaX MaramaRoute",
        "version": _installed_version(),
        "state_dir": str(state_root),
        "cache_dir": str(args.cache_dir),
        "default_model": model.model_id,
        "gateway": {
            "host": args.host,
            "port": args.port,
            "base_url": f"http://{args.host}:{args.port}/v1",
            "live_local": args.live_local,
        },
        "next_commands": {
            "doctor": "MaramaRoute doctor --hardware",
            "pull": f"MaramaRoute pull {model.model_id}",
            "chat": f"MaramaRoute chat {model.model_id}",
            "serve": f"MaramaRoute serve --host {args.host} --port {args.port} --live-local",
        },
        "self_test": self_test,
    }
    config_path = state_root / "marama-route.json"
    config_path.write_text(json.dumps(config, indent=2, sort_keys=True), encoding="utf-8")
    set_alias("default", model.model_id, state_root)
    set_favorite(model.model_id, state_root)
    artifacts = {"config": str(config_path), "state_dir": str(state_root)}
    if args.agent:
        agent_result = build_agent_bridge_config(
            models,
            target=args.agent,
            base_url=f"http://{args.host}:{args.port}/v1",
            host=args.host,
            port=args.port,
            cache_dir=args.cache_dir,
            model_id=model.model_id,
        )
        agent_path = state_root / f"{args.agent}.agent.json"
        agent_path.write_text(json.dumps(agent_result, indent=2, sort_keys=True), encoding="utf-8")
        artifacts["agent_config"] = str(agent_path)
    if args.hpe:
        hpe_path = state_root / "marama-route.slurm"
        hpe_path.write_text(render_hpe_slurm_script(model_id=model.model_id), encoding="utf-8")
        artifacts["hpe_job"] = str(hpe_path)
    if args.pull:
        pull_model(models, model.model_id, cache_root=args.cache_dir)
        artifacts["pulled_model"] = model.model_id
    result = {"ok": True, "model_id": model.model_id, "artifacts": artifacts, "config": config, "self_test": self_test}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def _init_self_test(models: tuple[Any, ...], model: Any, args: argparse.Namespace) -> dict[str, Any]:
    checks = {
        "registry_loaded": {"ok": bool(models), "count": len(models), "path": str(_registry_path(args))},
        "selected_model": {"ok": True, "model_id": model.model_id, "runtime": model.runtime},
        "cache_writable": _writable_dir(args.cache_dir),
        "runtime_available": {
            "ok": importlib.util.find_spec("llama_cpp") is not None,
            "package": "llama-cpp-python",
            "needed_for": "local GGUF chat and run",
            "severity": "warning",
        },
        "huggingface_hub": {
            "ok": importlib.util.find_spec("huggingface_hub") is not None,
            "needed_for": "pull and update-registry",
        },
    }
    blocking = [item for item in checks.values() if not item.get("ok") and item.get("severity") != "warning"]
    return {"enabled": True, "ok": not blocking, "checks": checks}


def _writable_dir(path: Path) -> dict[str, Any]:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".marama-route-write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return {"ok": True, "path": str(path)}
    except OSError as exc:
        return {"ok": False, "path": str(path), "error": str(exc)}


def _model_ops(args: argparse.Namespace) -> int:
    models = load_model_registry(_registry_path(args))
    action = args.model_action
    if action in {"ls", "list", "disk"}:
        result = cache_report(models, args.cache_dir)
    elif action == "verify":
        result = verify_cache(models, args.cache_dir, deep=args.deep, write_hashes=args.write_hashes)
    elif action == "rm":
        if not args.model:
            raise ValueError("rm requires <model>")
        result = remove_cached_model(models, args.model, cache_root=args.cache_dir, dry_run=args.dry_run)
    elif action == "prune":
        result = prune_cache(models, cache_root=args.cache_dir, dry_run=args.dry_run)
    elif action == "estimate":
        if not args.model:
            raise ValueError("estimate requires <model>")
        model = _resolve_cli_model(models, args.model)
        result = estimate_model_download(model, args.cache_dir, remote=args.remote_sizes, all_files=args.all_files)
    elif action == "ps":
        result = {
            "ok": True,
            "running_process_registry": "not_persistent",
            "note": "Use `MaramaRoute serve --live-local` to start the local gateway.",
            "cache": cache_report(models, args.cache_dir),
        }
    else:
        raise ValueError(f"Unsupported model action: {action}")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok", False) else 2


def _hardware(args: argparse.Namespace) -> int:
    models = load_model_registry(_registry_path(args))
    hardware = inspect_hardware(args.cache_dir)
    result = {"ok": True, "hardware": hardware}
    if args.recommend:
        result["recommendations"] = hardware_recommendations(models, hardware, limit=args.limit)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def _alias(args: argparse.Namespace) -> int:
    models = load_model_registry(_registry_path(args))
    if args.alias_action == "list":
        result = {"ok": True, **load_aliases(args.state_dir)}
    elif args.alias_action == "set":
        if not args.name or not args.model:
            raise ValueError("alias set requires <name> <model>")
        model = _resolve_cli_model(models, args.model)
        result = set_alias(args.name, model.model_id, args.state_dir)
    elif args.alias_action == "rm":
        if not args.name:
            raise ValueError("alias rm requires <name>")
        result = delete_alias(args.name, args.state_dir)
    elif args.alias_action == "favorite":
        model_ref = args.model or args.name
        if not model_ref:
            raise ValueError("favorite requires <model>")
        model = _resolve_cli_model(models, model_ref)
        result = set_favorite(model.model_id, args.state_dir)
    else:
        raise ValueError(f"Unsupported alias action: {args.alias_action}")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def _bench(args: argparse.Namespace) -> int:
    models = load_model_registry(_registry_path(args))
    model = _resolve_cli_model(models, args.model)
    prompt = args.prompt_text or "Say kia ora in one short sentence."
    start = time.perf_counter()
    try:
        result = run_pulled_model(
            models,
            model.model_id,
            prompt=prompt,
            cache_root=args.cache_dir,
            pull=args.pull,
            max_tokens=args.max_tokens,
            dry_run=args.dry_run,
        )
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    elapsed = max(time.perf_counter() - start, 0.0001)
    text = str(result.get("response") or "")
    payload = {
        "ok": True,
        "model_id": model.model_id,
        "dry_run": args.dry_run,
        "elapsed_seconds": round(elapsed, 4),
        "characters": len(text),
        "characters_per_second": round(len(text) / elapsed, 2),
        "result": result,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _eval(args: argparse.Namespace) -> int:
    models = load_model_registry(_registry_path(args))
    scenarios = route_scenario_matrix(models)
    analytics = build_registry_analytics(models)
    result = {
        "ok": scenarios["ok"],
        "suite": args.suite,
        "analytics": analytics,
        "matrix": scenarios,
        "note": "This eval checks deterministic routing coverage. Use `bench` for local runtime timing.",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] or args.allow_blocked_exit_zero else 2


def _audit(args: argparse.Namespace) -> int:
    state_root = args.state_dir
    if args.audit_action == "list":
        result = list_audit_receipts(state_root)
    elif args.audit_action == "show":
        if not args.receipt:
            raise ValueError("audit show requires <receipt-id>")
        result = show_audit_receipt(args.receipt, state_root)
    elif args.audit_action == "export":
        path = export_audit_receipts(args.output, state_root)
        result = {"ok": True, "path": str(path)}
    elif args.audit_action == "record":
        if args.request is None:
            raise ValueError("audit record requires --request")
        models = load_model_registry(_registry_path(args))
        payload = _load_json_mapping(args.request)
        decision = SovereignModelRouter(models).route(RoutingRequest.from_payload(payload))
        route_result = {"route_decision": decision.to_dict()}
        from .platform import route_receipt

        receipt = route_receipt(payload, route_result)
        path = write_audit_receipt(receipt, state_root)
        result = {"ok": True, "path": str(path), "receipt": receipt}
    else:
        raise ValueError(f"Unsupported audit action: {args.audit_action}")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def _agent_init(args: argparse.Namespace) -> int:
    models = load_model_registry(_registry_path(args))
    model_ref = args.model or args.model_option
    model = _resolve_cli_model(models, model_ref) if model_ref else _recommended_model(models)
    target_dir = args.output_dir.resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    config = build_agent_bridge_config(
        models,
        target=args.target,
        base_url=args.base_url,
        host=args.host,
        port=args.port,
        cache_dir=args.cache_dir,
        model_id=model.model_id,
    )
    config_path = target_dir / "marama-route.agent.json"
    config_path.write_text(json.dumps(config, indent=2, sort_keys=True), encoding="utf-8")
    written = [str(config_path)]
    if args.target == "claude-code":
        claude_path = target_dir / "CLAUDE.md"
        claude_path.write_text(
            "\n".join(
                (
                    "# MaramaRoute",
                    "",
                    "Use MaramaRoute for LumynaX model selection, local chat, and local-live gateway calls.",
                    f"Default model: `{model.model_id}`",
                    f"Start gateway: `{config['commands']['start_gateway']}`",
                    f"Recommend model: `{config['commands']['recommend']}`",
                    "",
                ),
            ),
            encoding="utf-8",
        )
        written.append(str(claude_path))
    print(json.dumps({"ok": True, "target": args.target, "model_id": model.model_id, "written": written}, indent=2, sort_keys=True))
    return 0


def _agent_doctor(args: argparse.Namespace) -> int:
    models = load_model_registry(_registry_path(args))
    config = build_agent_bridge_config(
        models,
        target=args.target,
        base_url=args.base_url,
        host=args.host,
        port=args.port,
        cache_dir=args.cache_dir,
        model_id=args.model or "",
    )
    health = {"ok": True, "checked": False, "base_url": args.base_url}
    if args.health_check:
        health = _gateway_health(args.base_url)
    checks = {
        "registry": {"ok": bool(models), "count": len(models), "path": str(_registry_path(args))},
        "target": {"ok": config.get("target") in {"generic", "claude-code", "opencode", "hpe-slurm"}, "value": config.get("target")},
        "cache": {"ok": True, "path": str(args.cache_dir or default_cache_root())},
        "gateway": health,
    }
    result = {
        "ok": all(bool(item.get("ok")) for item in checks.values()),
        "product": "LumynaX MaramaRoute",
        "mode": "agent_doctor",
        "config": config,
        "checks": checks,
        "next_commands": config.get("commands", {}),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] or args.allow_warnings else 2


def _gateway_health(base_url: str) -> dict[str, Any]:
    from urllib.error import URLError
    from urllib.request import urlopen

    root = base_url.removesuffix("/v1").rstrip("/")
    url = f"{root}/health"
    try:
        with urlopen(url, timeout=2) as response:
            return {"ok": 200 <= response.status < 300, "checked": True, "url": url, "status": response.status}
    except URLError as exc:
        return {"ok": False, "checked": True, "url": url, "error": str(exc)}


def _hpe(args: argparse.Namespace) -> int:
    models = load_model_registry(_registry_path(args))
    model = _resolve_cli_model(models, args.model) if args.model else _recommended_model(models)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    gateway_config = render_hpe_gateway_config(
        model_id=model.model_id,
        backend=args.backend,
        model_runtime=model.runtime,
        backend_base_url=args.backend_base_url or f"http://127.0.0.1:{args.backend_port}/v1",
        backend_model=args.backend_model or model.model_id,
        api_key_env=args.api_key_env,
        cache_dir="$MARAMA_ROUTE_CACHE",
    )
    if args.hpe_action == "init":
        script = output_dir / "marama-route.slurm"
        script.write_text(
            render_hpe_slurm_script(
                model_id=model.model_id,
                repo_id=model.repo_id,
                model_runtime=model.runtime,
                port=args.port,
                backend=args.backend,
                backend_port=args.backend_port,
                backend_base_url=args.backend_base_url,
                backend_model=args.backend_model,
                backend_command=args.backend_command,
                api_key_env=args.api_key_env,
                vllm_args=args.vllm_args,
                gpus=args.gpus,
                memory=args.memory,
                time_limit=args.time,
                partition=args.partition,
            ),
            encoding="utf-8",
        )
        gateway = output_dir / "gateway.hpe.json"
        gateway.write_text(json.dumps(gateway_config, indent=2, sort_keys=True), encoding="utf-8")
        env = output_dir / "marama-route.env"
        env.write_text(
            "\n".join(
                (
                    "MARAMA_ROUTE_CACHE=${SCRATCH:-$HOME}/marama-route/models",
                    f"MARAMA_ROUTE_PORT={args.port}",
                    f"MARAMA_BACKEND_PORT={args.backend_port}",
                    f"MARAMA_BACKEND_BASE_URL={args.backend_base_url or f'http://127.0.0.1:{args.backend_port}/v1'}",
                    f"MARAMA_BACKEND_MODEL={args.backend_model or model.model_id}",
                    f"MARAMA_BACKEND={args.backend}",
                    "",
                ),
            ),
            encoding="utf-8",
        )
        definition = output_dir / "marama-route.def"
        definition.write_text(render_hpe_apptainer_definition(backend=args.backend), encoding="utf-8")
        readme = output_dir / "README.hpe.md"
        readme.write_text(render_hpe_readme(model_id=model.model_id, port=args.port, backend=args.backend), encoding="utf-8")
        result = {
            "ok": True,
            "written": [str(script), str(gateway), str(env), str(definition), str(readme)],
            "model_id": model.model_id,
            "repo_id": model.repo_id,
            "backend": args.backend,
            "gateway_config": gateway_config,
        }
    elif args.hpe_action == "submit":
        script = output_dir / "marama-route.slurm"
        script.write_text(
            render_hpe_slurm_script(
                model_id=model.model_id,
                repo_id=model.repo_id,
                model_runtime=model.runtime,
                port=args.port,
                backend=args.backend,
                backend_port=args.backend_port,
                backend_base_url=args.backend_base_url,
                backend_model=args.backend_model,
                backend_command=args.backend_command,
                api_key_env=args.api_key_env,
                vllm_args=args.vllm_args,
                gpus=args.gpus,
                memory=args.memory,
                time_limit=args.time,
                partition=args.partition,
            ),
            encoding="utf-8",
        )
        (output_dir / "gateway.hpe.json").write_text(json.dumps(gateway_config, indent=2, sort_keys=True), encoding="utf-8")
        command = ["sbatch", str(script)]
        if args.execute and shutil.which("sbatch"):
            completed = subprocess_run(command)
            result = {"ok": completed["returncode"] == 0, "command": command, "result": completed}
        else:
            result = {"ok": True, "command": " ".join(command), "execute": False, "script": str(script)}
    elif args.hpe_action == "plan":
        result = {
            "ok": True,
            "model_id": model.model_id,
            "repo_id": model.repo_id,
            "runtime": model.runtime,
            "backend": args.backend,
            "gateway_config": gateway_config,
            "commands": {
                "init": f"MaramaRoute hpe init {model.model_id} --backend {args.backend}",
                "submit": f"MaramaRoute hpe submit {model.model_id} --backend {args.backend}",
                "serve_api": f"MaramaRoute serve --host 0.0.0.0 --port {args.port} --config gateway.hpe.json",
                "tunnel": f"ssh -N -L {args.port}:127.0.0.1:{args.port} <user>@<login-node>",
            },
        }
    elif args.hpe_action == "tunnel":
        result = {
            "ok": True,
            "command": f"ssh -N -L {args.port}:127.0.0.1:{args.port} <user>@<login-node>",
            "base_url": f"http://127.0.0.1:{args.port}/v1",
        }
    elif args.hpe_action == "status":
        command = ["squeue", "-u", os.getenv("USER") or os.getenv("USERNAME") or ""]
        if shutil.which("squeue"):
            result = {"ok": True, "command": command, "result": subprocess_run(command)}
        else:
            result = {"ok": True, "scheduler": "slurm", "status": "squeue_not_available_on_this_machine"}
    else:
        raise ValueError(f"Unsupported HPE action: {args.hpe_action}")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok", False) else 2


def _update_registry(args: argparse.Namespace) -> int:
    output = args.output or (default_state_root() / "lumynax_model_registry.json")
    if args.dry_run:
        result = {"ok": True, "dry_run": True, "output": str(output), "repo_id": args.repo_id}
        if args.diff:
            try:
                payload, source = _download_registry_payload(args.repo_id, args.filename)
                result["source"] = source
                result["diff"] = diff_model_registry(load_model_registry(_registry_path(args)), payload)
            except Exception as exc:
                print(str(exc), file=sys.stderr)
                return 2
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    try:
        payload, downloaded = _download_registry_payload(args.repo_id, args.filename)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(downloaded, output)
    result = {"ok": True, "output": str(output), "source": downloaded}
    if args.diff:
        result["diff"] = diff_model_registry(load_model_registry(_registry_path(args)), payload)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def _download_registry_payload(repo_id: str, filename: str) -> tuple[dict[str, Any] | list[Any], str]:
    try:
        from huggingface_hub import hf_hub_download  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("huggingface-hub is required for update-registry.") from exc
    downloaded = hf_hub_download(repo_id=repo_id, filename=filename)
    payload = json.loads(Path(downloaded).read_text(encoding="utf-8-sig"))
    return payload, downloaded


def _pull(args: argparse.Namespace) -> int:
    models = load_model_registry(_registry_path(args))
    targets = _pull_targets(models, args)
    if not targets:
        print("No matching LumynaX models found for the pull request.", file=sys.stderr)
        return 2
    if args.estimate:
        estimates = [
            estimate_model_download(model, args.cache_dir, remote=args.remote_sizes, all_files=args.all_files)
            for model in targets
        ]
        output = estimates[0] if len(estimates) == 1 else {"ok": True, "count": len(estimates), "models": estimates}
        print(json.dumps(output, indent=2, sort_keys=True))
        return 0
    if len(targets) > 1 and not args.dry_run and not args.yes:
        if not sys.stdin.isatty():
            print("Batch pull needs --yes in non-interactive mode.", file=sys.stderr)
            return 2
        answer = input(f"Pull {len(targets)} models into {args.cache_dir}? [y/N] ").strip().lower()
        if answer not in {"y", "yes"}:
            print("Pull cancelled.")
            return 2

    pulled = []
    for model in targets:
        result = pull_model(
            models,
            model.model_id,
            cache_root=args.cache_dir,
            all_files=args.all_files,
            force=args.force,
            dry_run=args.dry_run,
        )
        pulled.append(result.to_dict())
    output = pulled[0] if len(pulled) == 1 else {"ok": True, "count": len(pulled), "models": pulled}
    if args.verify and not args.dry_run:
        output = {
            "ok": True,
            "pull": output,
            "verify": verify_cache(models, args.cache_dir, deep=args.deep_verify, write_hashes=args.write_hashes),
        }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


def _local(args: argparse.Namespace) -> int:
    print(json.dumps(list_pulled_models(args.cache_dir), indent=2, sort_keys=True))
    return 0


def _run(args: argparse.Namespace) -> int:
    models = load_model_registry(_registry_path(args))
    if args.model is None:
        return _conversation(args, models)
    prompt = " ".join(args.prompt).strip() if args.prompt else args.prompt_text
    if not prompt:
        return _conversation(args, models)
    model = _resolve_cli_model(models, args.model)
    if args.stream and not args.dry_run:
        return _stream_once(args, models, model, prompt)
    try:
        result = run_pulled_model(
            models,
            model.model_id,
            prompt=prompt or "Say kia ora to Aotearoa in one short sentence.",
            cache_root=args.cache_dir,
            pull=args.pull,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            context_tokens=args.context_tokens,
            threads=args.threads,
            dry_run=args.dry_run,
        )
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def _chat(args: argparse.Namespace) -> int:
    models = load_model_registry(_registry_path(args))
    prompt = " ".join(args.prompt).strip() if args.prompt else args.prompt_text
    if prompt:
        model = _resolve_cli_model(models, args.model) if args.model else _recommended_model(models)
        if args.stream and not args.dry_run:
            return _stream_once(args, models, model, prompt)
        try:
            result = run_pulled_model(
                models,
                model.model_id,
                prompt=prompt,
                cache_root=args.cache_dir,
                pull=args.pull,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
                context_tokens=args.context_tokens,
                threads=args.threads,
                dry_run=args.dry_run,
            )
        except (FileNotFoundError, RuntimeError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 2
        if args.dry_run:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print(result["response"])
        return 0
    return _conversation(args, models)


def _conversation(args: argparse.Namespace, models: tuple[Any, ...]) -> int:
    if args.dry_run:
        model = _resolve_cli_model(models, args.model) if args.model else _recommended_model(models)
        payload = {
            "ok": True,
            "mode": "conversation_dry_run",
            "model_id": model.model_id,
            "repo_id": model.repo_id,
            "cache_dir": str(model_cache_dir(model, args.cache_dir)),
            "commands": [
                "/models",
                "/all",
                "/hardware",
                "/recommended",
                "/categories",
                "/vllm",
                "/nim",
                "/nemo",
                "/search <text>",
                "/switch <text>",
                "/pull [text]",
                "/local",
                "/settings",
                "/clear",
                "/history",
                "/save <name>",
                "/load <name>",
                "/export <name> <file.md>",
                "/info",
                "/exit",
            ],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if not sys.stdin.isatty():
        print(
            "MaramaRoute chat needs an interactive terminal or a prompt.\n"
            "Try: MaramaRoute chat lumynax-coder-qwen25-05b-instruct-gguf \"Say kia ora\"",
            file=sys.stderr,
        )
        return 2

    _print_startup_guide(models, args.cache_dir, animated=True)
    try:
        model = _resolve_cli_model(models, args.model) if args.model else _prompt_for_model(models, args.cache_dir)
    except _ExitConversation:
        return 0
    session = None

    while True:
        try:
            if session is None:
                try:
                    model = _ensure_model_ready(
                        models,
                        model,
                        cache_dir=args.cache_dir,
                        auto_pull=args.pull,
                    )
                    session = load_chat_session(
                        models,
                        model.model_id,
                        cache_root=args.cache_dir,
                        pull=False,
                        max_tokens=args.max_tokens,
                        temperature=args.temperature,
                        context_tokens=args.context_tokens,
                        threads=args.threads,
                    )
                    print(_loaded_model_message(model))
                except FileNotFoundError as exc:
                    print(str(exc))
                    model = _prompt_for_model(models, args.cache_dir)
                    continue
                except RuntimeError as exc:
                    print(str(exc), file=sys.stderr)
                    return 2
            prompt = input("\n>>> ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            return 0

        if not prompt:
            continue
        command = prompt.lower()
        if command in CHAT_COMMANDS:
            return 0
        if command in {"/help", "/h", "?"}:
            _print_chat_help()
            continue
        if command == "/models":
            try:
                model = _prompt_for_model(models, args.cache_dir)
            except _ExitConversation:
                return 0
            session = None
            continue
        if command in {"/hardware", "/recommended-hardware"}:
            try:
                model = _prompt_for_model(models, args.cache_dir, hardware_only=True)
            except _ExitConversation:
                return 0
            session = None
            continue
        if command in {"/recommended", "/recommend", "/best"}:
            try:
                model = _prompt_for_model(models, args.cache_dir, show_menu=False)
            except _ExitConversation:
                return 0
            session = None
            continue
        if command == "/all":
            try:
                model = _prompt_for_model(models, args.cache_dir, include_all=True)
            except _ExitConversation:
                return 0
            session = None
            continue
        if command in {"/vllm", "/nim", "/nemo", "/nem"}:
            try:
                model = _prompt_for_model(
                    models,
                    args.cache_dir,
                    compatibility_target=_deployment_target_from_command(command),
                )
            except _ExitConversation:
                return 0
            session = None
            continue
        if command == "/catalog":
            choices = _conversation_choices(models, include_all=True)
            _print_model_picker_header(
                models,
                choices,
                query="",
                include_all=True,
                hardware_only=False,
                compatibility_target="",
                offset=0,
                shown=min(len(choices), MODEL_PICKER_PAGE_SIZE),
                hardware=None,
            )
            continue
        if command in {"/families", "/categories"}:
            _print_model_categories(models)
            continue
        if command == "/local":
            _print_local_models(args.cache_dir)
            continue
        if command == "/clear":
            if session is not None:
                session.history.clear()
            print("Conversation history cleared.")
            continue
        if command == "/history":
            for index, (user, assistant) in enumerate(session.history if session is not None else [], 1):
                print(f"{index}. user: {user}")
                print(f"   assistant: {assistant}")
            if session is not None and not session.history:
                print("No conversation history yet.")
            continue
        if command.startswith("/save "):
            name = prompt.split(maxsplit=1)[1].strip()
            path = save_session(name, model.model_id, session.history if session is not None else [])
            print(f"Saved session to {path}")
            continue
        if command.startswith("/load "):
            name = prompt.split(maxsplit=1)[1].strip()
            try:
                payload = load_session(name)
                model = _resolve_cli_model(models, str(payload.get("model_id") or model.model_id))
                session = load_chat_session(
                    models,
                    model.model_id,
                    cache_root=args.cache_dir,
                    pull=False,
                    max_tokens=args.max_tokens,
                    temperature=args.temperature,
                    context_tokens=args.context_tokens,
                    threads=args.threads,
                )
                session.history = [
                    (str(item.get("user") or ""), str(item.get("assistant") or ""))
                    for item in payload.get("history", [])
                    if isinstance(item, dict)
                ]
            except (OSError, RuntimeError, ValueError, FileNotFoundError) as exc:
                print(str(exc))
                continue
            print(f"Loaded session {name}.")
            continue
        if command.startswith("/export "):
            parts = prompt.split(maxsplit=2)
            if len(parts) < 3:
                print("Use /export <session-name> <file.md>")
                continue
            try:
                path = export_session_markdown(parts[1], Path(parts[2]))
            except (OSError, ValueError, FileNotFoundError) as exc:
                print(str(exc))
                continue
            print(f"Exported session to {path}")
            continue
        if command == "/settings":
            _print_chat_settings(model, args)
            continue
        if command == "/switch":
            try:
                model = _prompt_for_model(models, args.cache_dir)
            except _ExitConversation:
                return 0
            session = None
            continue
        if command.startswith("/switch ") or command.startswith("/use "):
            query = prompt.split(maxsplit=1)[1].strip()
            try:
                model = _resolve_cli_model(models, query)
            except ValueError as exc:
                print(str(exc))
                continue
            session = None
            print(f"Switched to {model.model_id}.")
            continue
        if command.startswith("/search ") or command.startswith("/family "):
            query = prompt.split(maxsplit=1)[1].strip()
            try:
                model = _prompt_for_model(models, args.cache_dir, initial_query=query, include_all=True)
            except _ExitConversation:
                return 0
            session = None
            continue
        if command == "/pull":
            pulled = pull_model(models, model.model_id, cache_root=args.cache_dir)
            print(f"Pulled {model.model_id} to {pulled.cache_dir}")
            session = None
            continue
        if command.startswith("/pull "):
            query = prompt.split(maxsplit=1)[1].strip()
            try:
                pulled_model = _resolve_cli_model(models, query)
                pulled = pull_model(models, pulled_model.model_id, cache_root=args.cache_dir)
            except (RuntimeError, ValueError) as exc:
                print(str(exc))
                continue
            print(f"Pulled {pulled_model.model_id} to {pulled.cache_dir}")
            model = pulled_model
            session = None
            continue
        if command == "/info":
            print(json.dumps(model.to_dict(), indent=2, sort_keys=True))
            continue

        try:
            if args.stream:
                for chunk in session.send_stream(prompt):
                    print(chunk, end="", flush=True)
                print()
                continue
            response = session.send(prompt)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        print(response)


def _stream_once(args: argparse.Namespace, models: tuple[Any, ...], model: Any, prompt: str) -> int:
    try:
        session = load_chat_session(
            models,
            model.model_id,
            cache_root=args.cache_dir,
            pull=args.pull,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            context_tokens=args.context_tokens,
            threads=args.threads,
        )
        for chunk in session.send_stream(prompt):
            print(chunk, end="", flush=True)
        print()
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


def _recommended_model(models: tuple[Any, ...]) -> Any:
    choices = _conversation_choices(models, limit=1)
    if not choices:
        raise ValueError("No runnable LumynaX models found in the registry.")
    return choices[0]


def _resolve_cli_model(models: tuple[Any, ...], model_ref: str) -> Any:
    model_ref = resolve_alias(model_ref)
    try:
        return resolve_model(models, model_ref)
    except ValueError:
        choices = _conversation_choices(models, search=model_ref, limit=1)
        if choices:
            return choices[0]
        raise


def _pull_targets(models: tuple[Any, ...], args: argparse.Namespace) -> list[Any]:
    if args.model:
        return [_resolve_cli_model(models, args.model)]

    has_filters = bool(args.search or args.family or args.runtime or args.limit)
    if not has_filters:
        if sys.stdin.isatty():
            return [_prompt_for_model(models, args.cache_dir)]
        return []

    choices = _conversation_choices(
        models,
        search=args.search,
        include_all=not args.chat_only,
        limit=None,
    )
    family = args.family.strip().lower()
    runtime = args.runtime.strip().lower()
    filtered = []
    for model in choices:
        if args.chat_only and not _is_chat_runnable(model):
            continue
        if family and family not in model.family.lower() and family not in " ".join(model.tags):
            continue
        if runtime and runtime != model.runtime.lower():
            continue
        filtered.append(model)
    return filtered[: args.limit] if args.limit > 0 else filtered


def _conversation_choices(
    models: tuple[Any, ...],
    *,
    search: str = "",
    include_all: bool = False,
    compatibility_target: str = "",
    limit: int | None = None,
) -> list[Any]:
    filtered: list[Any] = []
    query = search.strip().lower()
    for model in models:
        haystack = " ".join((model.model_id, model.repo_id, model.family, " ".join(model.tags))).lower()
        if compatibility_target:
            if not _matches_deployment_target(model, compatibility_target):
                continue
        elif not include_all and not _is_chat_runnable(model):
            continue
        if query and query not in haystack:
            continue
        filtered.append(model)
    ranked = sorted(
        filtered,
        key=lambda item: (
            "coder" in item.model_id.lower(),
            item.sovereignty_tier,
            -item.quality_rank,
            item.context_tokens,
            item.model_id,
        ),
        reverse=True,
    )
    return ranked if limit is None else ranked[:limit]


def _hardware_choices(
    models: tuple[Any, ...],
    cache_dir: Path | None,
    *,
    search: str = "",
    include_all: bool = False,
) -> tuple[list[Any], dict[str, Any]]:
    hardware = inspect_hardware(cache_dir)
    recommendations = hardware_recommendations(models, hardware, limit=len(models))
    index = {model.model_id: model for model in models}
    ranked = [index[row["model_id"]] for row in recommendations["models"] if row["model_id"] in index]
    query = search.strip().lower()
    filtered = []
    for model in ranked:
        haystack = " ".join((model.model_id, model.repo_id, model.family, " ".join(model.tags))).lower()
        if not include_all and not _is_chat_runnable(model):
            continue
        if query and query not in haystack:
            continue
        filtered.append(model)
    return filtered, hardware


def _prompt_for_model(
    models: tuple[Any, ...],
    cache_dir: Path | None,
    *,
    initial_query: str = "",
    include_all: bool = False,
    hardware_only: bool = False,
    compatibility_target: str = "",
    show_menu: bool = True,
) -> Any:
    query = initial_query
    menu_open = show_menu and not initial_query and not include_all and not hardware_only and not compatibility_target
    offset = 0
    last_hardware: dict[str, Any] | None = None
    while True:
        if menu_open:
            _print_model_picker_menu(models, cache_dir)
            raw = input(f"{_prompt_marker()} Choose option 1-9, search text, /help, or /exit: ").strip()
            if not raw:
                raw = "1"
            lowered = raw.lower()
            if lowered in CHAT_COMMANDS:
                raise _ExitConversation
            if lowered in {"/help", "/h", "?"}:
                _print_model_picker_help()
                continue
            if raw == "1" or lowered in {"/hardware", "/recommended-hardware"}:
                hardware_only = True
                include_all = False
                compatibility_target = ""
                query = ""
                offset = 0
                menu_open = False
                continue
            if raw == "2" or lowered in {"/recommended", "/recommend", "/best"}:
                hardware_only = False
                include_all = False
                compatibility_target = ""
                query = ""
                offset = 0
                menu_open = False
                continue
            if raw == "3":
                query = input(f"{_prompt_marker()} Search text: ").strip()
                include_all = True
                hardware_only = False
                compatibility_target = ""
                offset = 0
                menu_open = False
                continue
            if raw == "4" or lowered in {"/models", "/switch", "/runnable"}:
                hardware_only = False
                include_all = False
                compatibility_target = ""
                query = ""
                offset = 0
                menu_open = False
                continue
            if raw == "5" or lowered in {"/all", "/catalog"}:
                hardware_only = False
                include_all = True
                compatibility_target = ""
                query = ""
                offset = 0
                menu_open = False
                continue
            if raw == "6" or lowered == "/local":
                _print_local_models(cache_dir)
                continue
            if raw == "7" or lowered == "/vllm":
                hardware_only = False
                include_all = True
                compatibility_target = "vllm"
                query = ""
                offset = 0
                menu_open = False
                continue
            if raw == "8" or lowered == "/nim":
                hardware_only = False
                include_all = True
                compatibility_target = "nvidia_nim"
                query = ""
                offset = 0
                menu_open = False
                continue
            if raw == "9" or lowered in {"/nemo", "/nem"}:
                hardware_only = False
                include_all = True
                compatibility_target = "nvidia_nemo"
                query = ""
                offset = 0
                menu_open = False
                continue
            handled = _handle_model_picker_command(raw, models)
            if handled is not None:
                query = handled["query"]
                include_all = handled["include_all"]
                hardware_only = handled.get("hardware_only", False)
                compatibility_target = handled.get("compatibility_target", "")
                menu_open = handled.get("menu", False)
                offset = 0
            else:
                query = raw
                include_all = True
                hardware_only = False
                compatibility_target = ""
                offset = 0
                menu_open = False
            continue

        if compatibility_target:
            choices = _conversation_choices(
                models,
                search=query,
                include_all=True,
                compatibility_target=compatibility_target,
            )
            last_hardware = None
        elif hardware_only:
            choices, last_hardware = _hardware_choices(models, cache_dir, search=query, include_all=include_all)
        else:
            choices = _conversation_choices(models, search=query, include_all=include_all)
            last_hardware = None
        if not choices:
            raw = input(f"{_prompt_marker()} No match. Search again, /hardware, /all, /models, /menu, or /exit: ").strip()
            handled = _handle_model_picker_command(raw, models)
            if handled is not None:
                query = handled["query"]
                include_all = handled["include_all"]
                hardware_only = handled.get("hardware_only", False)
                compatibility_target = handled.get("compatibility_target", "")
                menu_open = handled.get("menu", False)
                offset = 0
            else:
                query = raw
            continue
        print()
        offset = min(offset, max(0, len(choices) - 1))
        page = choices[offset : offset + MODEL_PICKER_PAGE_SIZE]
        _print_model_picker_header(
            models,
            choices,
            query=query,
            include_all=include_all,
            hardware_only=hardware_only,
            compatibility_target=compatibility_target,
            offset=offset,
            shown=len(page),
            hardware=last_hardware,
        )
        for index, model in enumerate(page, offset + 1):
            cached = "local" if local_model_files(model_cache_dir(model, cache_dir)) else "not pulled"
            chat_status = _offline_capability_label(model)
            print(
                f"{index:>2}. {model.model_id} "
                f"[{model.family}, {model.runtime}, tier {model.sovereignty_tier}, {chat_status}, {cached}]",
            )
        raw = input(
            f"{_prompt_marker()} Choose {offset + 1}-{offset + len(page)}, search text, /next, /prev, /menu, or /help: ",
        ).strip()
        if not raw:
            return page[0]
        command = raw.lower()
        if command == "/next":
            if offset + MODEL_PICKER_PAGE_SIZE >= len(choices):
                print("Already at the last page.")
            else:
                offset += MODEL_PICKER_PAGE_SIZE
            continue
        if command in {"/prev", "/back"}:
            offset = max(0, offset - MODEL_PICKER_PAGE_SIZE)
            continue
        if command in {"/help", "/h", "?"}:
            _print_model_picker_help()
            continue
        handled = _handle_model_picker_command(raw, models)
        if handled is not None:
            query = handled["query"]
            include_all = handled["include_all"]
            hardware_only = handled.get("hardware_only", False)
            compatibility_target = handled.get("compatibility_target", "")
            menu_open = handled.get("menu", False)
            offset = 0
            continue
        if raw.isdigit():
            selected = int(raw)
            if 1 <= selected <= len(choices):
                return choices[selected - 1]
            print(f"Choose a number from 1 to {len(choices)}.")
            continue
        try:
            return resolve_model(tuple(choices), raw)
        except ValueError:
            query = raw
            include_all = True
            hardware_only = False
            offset = 0


def _handle_model_picker_command(raw: str, models: tuple[Any, ...]) -> dict[str, Any] | None:
    command = raw.strip().lower()
    if not command:
        return None
    if command in CHAT_COMMANDS:
        raise _ExitConversation
    if command in {"/models", "/switch", "/runnable"}:
        return {"query": "", "include_all": False, "hardware_only": False, "compatibility_target": ""}
    if command in {"/hardware", "/recommended-hardware"}:
        return {"query": "", "include_all": False, "hardware_only": True, "compatibility_target": ""}
    if command in {"/recommended", "/recommend", "/best"}:
        return {"query": "", "include_all": False, "hardware_only": False, "compatibility_target": ""}
    if command == "/menu":
        return {"query": "", "include_all": False, "hardware_only": False, "compatibility_target": "", "menu": True}
    if command == "/all":
        return {"query": "", "include_all": True, "hardware_only": False, "compatibility_target": ""}
    if command == "/catalog":
        return {"query": "", "include_all": True, "hardware_only": False, "compatibility_target": ""}
    if command in {"/vllm", "/nim", "/nemo", "/nem"}:
        return {
            "query": "",
            "include_all": True,
            "hardware_only": False,
            "compatibility_target": _deployment_target_from_command(command),
        }
    if command.startswith("/search "):
        query = command.removeprefix("/search ").strip()
        return {"query": query, "include_all": True, "hardware_only": False, "compatibility_target": ""}
    if command.startswith("/use "):
        query = command.removeprefix("/use ").strip()
        return {"query": query, "include_all": False, "hardware_only": False, "compatibility_target": ""}
    if command.startswith("/family "):
        family = command.removeprefix("/family ").strip()
        return {"query": family, "include_all": True, "hardware_only": False, "compatibility_target": ""}
    if command in {"/families", "/categories"}:
        _print_model_categories(models)
        return {"query": "", "include_all": True, "hardware_only": False, "compatibility_target": ""}
    if command == "/local":
        print("Local models are shown after a model is selected. Use `MaramaRoute local` for full JSON.")
        return {"query": "", "include_all": False, "hardware_only": False, "compatibility_target": "", "menu": True}
    if command in {"/help", "/h", "?"}:
        _print_model_picker_help()
        return {"query": "", "include_all": False, "hardware_only": False, "compatibility_target": "", "menu": True}
    if command == "/pull":
        print("Choose a model first; then /pull downloads the selected model.")
        return {"query": "", "include_all": False, "hardware_only": False, "compatibility_target": ""}
    if command.startswith("/"):
        known = ", ".join(sorted(CHAT_COMMANDS | MODEL_PICKER_COMMANDS))
        print(f"Unknown command {raw!r}. Known commands: {known}.")
        return {"query": "", "include_all": False, "hardware_only": False, "compatibility_target": "", "menu": True}
    return None


def _is_chat_runnable(model: Any) -> bool:
    runtime = model.runtime.lower()
    return "llama" in runtime or "gguf" in runtime


def _offline_capability_label(model: Any) -> str:
    runtime = model.runtime.lower()
    artifact = model.primary_artifact.lower()
    if "llama" in runtime or "gguf" in runtime or "gguf" in artifact:
        return "chat"
    if _is_transformers_smoke_test(model):
        return "smoke-test"
    if _is_transformers_text_generation(model):
        return "chat/transformers"
    return "offline-task"


def _deployment_target_from_command(command: str) -> str:
    normalized = command.strip().lower().lstrip("/").replace("-", "_")
    if normalized == "vllm":
        return "vllm"
    if normalized == "nim":
        return "nvidia_nim"
    if normalized in {"nem", "nemo"}:
        return "nvidia_nemo"
    raise ValueError(f"Unknown deployment target command: {command}")


def _deployment_statuses_for_target(target: str) -> set[str]:
    if target == "nvidia_nemo":
        return set(_DEPLOYMENT_PATHWAY_STATUSES)
    return set(_DEPLOYMENT_USABLE_STATUSES)


def _matches_deployment_target(model: Any, target: str) -> bool:
    compatibility = model_runtime_compatibility(model)
    entry = compatibility.get(target, {})
    status = str(entry.get("status") or "").lower() if isinstance(entry, dict) else ""
    return status in _deployment_statuses_for_target(target)


def _deployment_summary(models: tuple[Any, ...]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for target, label in _DEPLOYMENT_TARGET_LABELS.items():
        statuses: dict[str, int] = {}
        usable = 0
        pathway = 0
        for model in models:
            entry = model_runtime_compatibility(model).get(target, {})
            status = str(entry.get("status") or "unknown").lower() if isinstance(entry, dict) else "unknown"
            statuses[status] = statuses.get(status, 0) + 1
            if status in _DEPLOYMENT_USABLE_STATUSES:
                usable += 1
            if status in _DEPLOYMENT_PATHWAY_STATUSES:
                pathway += 1
        summary[target] = {
            "label": label,
            "usable": usable,
            "pathway": pathway,
            "statuses": dict(_top_counts(statuses, limit=max(1, len(statuses)))),
            "browse_command": (
                f"MaramaRoute compat --target {_deployment_cli_target(target)} "
                f"--status {_deployment_cli_status(target)}"
            ),
            "picker_command": f"/{_deployment_cli_target(target)}",
        }
    return summary


def _deployment_cli_target(target: str) -> str:
    if target == "nvidia_nim":
        return "nim"
    if target == "nvidia_nemo":
        return "nemo"
    return target


def _deployment_cli_status(target: str) -> str:
    if target == "nvidia_nemo":
        return "pathway"
    return "usable"


def _format_deployment_counts(deployment: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for target in ("vllm", "nvidia_nim", "nvidia_nemo"):
        entry = deployment.get(target, {})
        label = str(entry.get("label") or target)
        statuses = entry.get("statuses") if isinstance(entry.get("statuses"), dict) else {}
        status_text = _format_counts(statuses)
        if target == "nvidia_nemo":
            lines.append(f"{label}: direct {entry.get('usable', 0)}, pathway {entry.get('pathway', 0)} ({status_text})")
        else:
            lines.append(f"{label}: usable {entry.get('usable', 0)} ({status_text})")
    return lines


def _is_transformers_text_generation(model: Any) -> bool:
    runtime = model.runtime.lower()
    if "transformers" not in runtime or "multimodal" in runtime:
        return False
    if _is_transformers_smoke_test(model):
        return False
    modalities = {str(item).lower() for item in model.modalities}
    if modalities - {"text"}:
        return False
    task_tags = {
        "asr",
        "classifier",
        "detection",
        "doc-ai",
        "document-vqa",
        "embedding",
        "embedding-companion",
        "guardrail",
        "layout",
        "moderation",
        "ocr",
        "reranker",
        "retrieval",
        "safety",
        "speech",
        "tables",
        "tts",
    }
    return not (set(model.tags) & task_tags)


def _is_transformers_smoke_test(model: Any) -> bool:
    runtime = model.runtime.lower()
    if "transformers" not in runtime:
        return False
    modalities = {str(item).lower() for item in model.modalities}
    if modalities - {"text"}:
        return False
    metadata = getattr(model, "metadata", {}) or {}
    weight = metadata.get("total_weight_size")
    try:
        total_weight_size = int(weight or 0)
    except (TypeError, ValueError):
        total_weight_size = 0
    return model.model_id == "lumynax-tiny" or (0 < total_weight_size < 50_000_000)


def _loaded_model_message(model: Any) -> str:
    capability = _offline_capability_label(model)
    if capability == "smoke-test":
        return (
            f"Loaded {model.model_id} (smoke-test seed). "
            "It is usable for install/runtime checks, not useful free-form chat. "
            "Use lumynax-tiny-qwen25-05b-gguf for tiny local chat."
        )
    if capability == "offline-task":
        return (
            f"Loaded {model.model_id} (offline task model). "
            "Type /info for metadata, /categories for model groups, or /switch for chat models."
        )
    return f"Loaded {model.model_id}."


def _print_model_picker_header(
    models: tuple[Any, ...],
    choices: list[Any],
    *,
    query: str,
    include_all: bool,
    hardware_only: bool,
    compatibility_target: str,
    offset: int,
    shown: int,
    hardware: dict[str, Any] | None,
) -> None:
    total = len(models)
    runnable = sum(1 for model in models if _is_chat_runnable(model))
    if compatibility_target:
        scope = f"{_DEPLOYMENT_TARGET_LABELS.get(compatibility_target, compatibility_target)} deployment-path models"
    elif hardware_only:
        scope = "hardware-suitable local GGUF chat models"
    else:
        scope = "all AbteeXAILab HF registry entries" if include_all else "recommended local GGUF chat models"
    suffix = f" matching {query!r}" if query else ""
    print("Type /help to see commands before choosing a model.")
    print(f"LumynaX model picker: showing {offset + 1}-{offset + shown} of {len(choices)} {scope}{suffix}.")
    print(f"Registry total: {total} models. Direct local chat models: {runnable}.")
    if hardware_only and hardware is not None:
        print(f"Hardware check: {hardware.get('memory', 'unknown memory')} RAM, {hardware.get('disk_free', 'unknown disk')} free.")
    if len(choices) > offset + shown:
        print("Use /next for more results.")
    if offset > 0:
        print("Use /prev for previous results.")
    if compatibility_target:
        print("Use /vllm, /nim, /nemo, /all, or /models to change category.")
    elif not include_all and not hardware_only:
        print("Use /hardware for machine-suitable models, /all, /vllm, /nim, /nemo, or /help.")
    else:
        print("Use /models to return to recommended chat models, /family <name>, /vllm, /nim, /nemo, or /help.")


def _print_model_picker_menu(models: tuple[Any, ...], cache_dir: Path | None) -> None:
    pulled = list_pulled_models(cache_dir)
    runnable = sum(1 for model in models if _is_chat_runnable(model))
    vllm_count, nim_count, nem_count = _deployment_tag_counts(models)
    print()
    _print_box(
        "MaramaRoute model picker",
        [
            f"Registry {len(models)} | Local chat {runnable} | Pulled {pulled['count']}",
            f"Deployment paths: vLLM {vllm_count} | NIM {nim_count} | NeMo/NEM {nem_count}",
            "",
            "1  Hardware-suitable models for this machine",
            "2  Recommended local chat models",
            "3  Search all AbteeXAILab Hugging Face models",
            "4  Browse local GGUF chat models",
            "5  Browse full registry",
            "6  Show pulled local models",
            "7  Browse vLLM deployment-path models",
            "8  Browse NVIDIA NIM deployment-path models",
            "9  Browse NVIDIA NeMo/NEM deployment-path models",
            "",
            "Type /help to see all commands. Press Enter for hardware-suitable models.",
        ],
    )


def _print_startup_guide(models: tuple[Any, ...], cache_dir: Path | None, *, animated: bool = False) -> None:
    pulled = list_pulled_models(cache_dir)
    runnable = sum(1 for model in models if _is_chat_runnable(model))
    vllm_count, nim_count, nem_count = _deployment_tag_counts(models)
    if animated:
        _animate_startup()
    print()
    _print_box(
        "MaramaRoute",
        [
            "AbteeX AI Labs LumynaX model console",
            "model:     choose with /models, /hardware, /vllm, /nim, or /nem",
            f"registry:  {len(models)} models | {runnable} local chat-capable | {pulled['count']} pulled",
            "runtime:   GGUF + llama.cpp | Transformers | task-model shells",
            f"Deployment paths: vLLM {vllm_count} | NVIDIA NIM {nim_count} | NVIDIA NeMo/NEM {nem_count}",
            f"directory: {_shorten_middle(str(Path.cwd()), 86)}",
            "",
            "Start here: press Enter for hardware-suitable models, or type /help any time.",
            "Offline flow: /models -> choose -> /pull -> chat. Use /switch <text> to change.",
            "Production commands: doctor | verify --deep | serve --live-local | agent-init | hpe init",
            "MaramaRoute serve --live-local --port 8787",
        ],
    )


def _animate_startup() -> None:
    if not sys.stdout.isatty():
        return
    frames = ("[   ]", "[=  ]", "[== ]", "[===]")
    message = "Preparing local LumynaX console"
    for frame in frames:
        print(f"\r{frame} {message}", end="", flush=True)
        time.sleep(0.04)
    print("\r[OK ] Local LumynaX console ready      ")


def _deployment_tag_counts(models: tuple[Any, ...]) -> tuple[int, int, int]:
    vllm_count = 0
    nim_count = 0
    nem_count = 0
    for model in models:
        tags = {str(tag).lower() for tag in model.tags}
        if "vllm-compatible" in tags:
            vllm_count += 1
        if "nim-compatible" in tags:
            nim_count += 1
        if {"nem-compatible", "nem-pathway"} & tags:
            nem_count += 1
    return vllm_count, nim_count, nem_count


def _print_box(title: str, lines: list[str]) -> None:
    width = min(max(shutil.get_terminal_size((100, 20)).columns, 78), 150)
    inner = width - 2
    title_text = f" {title} "
    if len(title_text) > inner:
        title_text = title_text[:inner]
    if _console_supports("╭─╮│╰╯"):
        top_left, top_right, bottom_left, bottom_right, horizontal, vertical = "╭", "╮", "╰", "╯", "─", "│"
    else:
        top_left, top_right, bottom_left, bottom_right, horizontal, vertical = "+", "+", "+", "+", "-", "|"
    print(top_left + title_text + horizontal * max(0, inner - len(title_text)) + top_right)
    for line in lines:
        print(vertical + " " + _fit_line(line, inner - 2) + " " + vertical)
    print(bottom_left + horizontal * inner + bottom_right)


def _fit_line(text: str, width: int) -> str:
    if len(text) > width:
        text = _shorten_middle(text, width)
    return text + " " * max(0, width - len(text))


def _shorten_middle(text: str, width: int) -> str:
    if len(text) <= width:
        return text
    if width <= 3:
        return text[:width]
    marker = "…" if _console_supports("…") else "..."
    left = max(1, (width - len(marker)) // 2)
    right = max(1, width - left - len(marker))
    return f"{text[:left]}{marker}{text[-right:]}"


def _prompt_marker() -> str:
    return "❯" if _console_supports("❯") else ">"


def _console_supports(text: str) -> bool:
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        text.encode(encoding)
    except UnicodeEncodeError:
        return False
    return True


def _print_model_picker_help() -> None:
    print(
        "\n".join(
            (
                "Model picker commands:",
                "  /hardware          show models suitable for this machine",
                "  /recommended       show recommended local chat models",
                "  /models            browse local GGUF chat-capable models",
                "  /all               browse every bundled AbteeXAILab registry entry",
                "  /vllm              browse vLLM supported/candidate/experimental models",
                "  /nim               browse NVIDIA NIM supported/candidate/experimental models",
                "  /nemo              browse NVIDIA NeMo candidates and conversion paths",
                "  /nem               alias for /nemo",
                "  /search <text>     search model id, repo, family, or tags",
                "  /family <name>     filter by family or tag",
                "  /categories        show category/family/runtime/tag/deployment counts",
                "  /families          alias for /categories",
                "  /next              next page of results",
                "  /prev              previous page of results",
                "  /menu              return to the picker menu",
                "  /local             show pulled local models",
                "  /exit              quit",
            ),
        ),
    )


def _print_model_categories(models: tuple[Any, ...]) -> None:
    _print_category_summary(_category_summary(models, limit=18))
    print("Type a family/tag/search term, or use /vllm, /nim, /nemo, /family qwen, /all, /runnable.")


def _category_summary(models: tuple[Any, ...], *, limit: int) -> dict[str, Any]:
    families: dict[str, int] = {}
    runtimes: dict[str, int] = {}
    tags: dict[str, int] = {}
    modalities: dict[str, int] = {}
    capabilities: dict[str, int] = {}
    for model in models:
        families[model.family] = families.get(model.family, 0) + 1
        runtimes[model.runtime] = runtimes.get(model.runtime, 0) + 1
        capability = _offline_capability_label(model)
        capabilities[capability] = capabilities.get(capability, 0) + 1
        for modality in model.modalities:
            modalities[modality] = modalities.get(modality, 0) + 1
        for tag in model.tags:
            tags[tag] = tags.get(tag, 0) + 1

    safe_limit = max(1, int(limit))
    return {
        "ok": True,
        "model_count": len(models),
        "families": dict(_top_counts(families, limit=safe_limit)),
        "runtimes": dict(_top_counts(runtimes, limit=safe_limit)),
        "tags": dict(_top_counts(tags, limit=safe_limit)),
        "modalities": dict(_top_counts(modalities, limit=safe_limit)),
        "capabilities": dict(_top_counts(capabilities, limit=safe_limit)),
        "deployment_compatibility": _deployment_summary(models),
        "commands": {
            "browse_recommended": "MaramaRoute chat",
            "browse_all": "MaramaRoute catalog",
            "category_cli": "MaramaRoute categories",
            "filter_family": "MaramaRoute catalog --family qwen",
            "pull_family": "MaramaRoute pull --family qwen --limit 3 --dry-run",
            "compatibility": "MaramaRoute compat",
            "browse_vllm": "MaramaRoute compat --target vllm --status usable",
            "browse_nim": "MaramaRoute compat --target nim --status usable",
            "browse_nem_nemo": "MaramaRoute compat --target nemo --status pathway",
        },
    }


def _print_category_summary(summary: dict[str, Any]) -> None:
    print()
    print("Categories from the bundled AbteeXAILab Hugging Face registry:")
    print(f"Models: {summary['model_count']}")
    print(f"Capabilities: {_format_counts(summary['capabilities'])}")
    print(f"Families: {_format_counts(summary['families'])}")
    print(f"Runtimes: {_format_counts(summary['runtimes'])}")
    print(f"Modalities: {_format_counts(summary['modalities'])}")
    print(f"Tags: {_format_counts(summary['tags'])}")
    print("Deployment compatibility:")
    for line in _format_deployment_counts(summary.get("deployment_compatibility", {})):
        print(f"  {line}")
    print(
        "Next: MaramaRoute chat  |  MaramaRoute compat --target vllm --status usable  |  "
        "MaramaRoute compat --target nemo --status pathway",
    )


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{name} ({count})" for name, count in counts.items())


def _top_counts(counts: dict[str, int], *, limit: int) -> list[tuple[str, int]]:
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]


def _print_compatibility_table(matrix: dict[str, Any]) -> None:
    print("MaramaRoute runtime compatibility")
    print(f"Models: {matrix['model_count']}. Returned: {matrix['returned']}. Target: {matrix['target']}.")
    print("Summary:")
    for runtime, counts in matrix["summary"].items():
        count_text = ", ".join(f"{status}={count}" for status, count in counts.items())
        print(f"  {runtime}: {count_text}")
    print()
    print(f"{'model':42} {'runtime':22} {'vllm':16} {'nim':16} {'nemo':16}")
    print("-" * 112)
    for row in matrix["models"]:
        compatibility = row.get("compatibility", {})
        print(
            f"{str(row.get('model_id', ''))[:42]:42} "
            f"{str(row.get('runtime', ''))[:22]:22} "
            f"{_compat_status(compatibility.get('vllm'))[:16]:16} "
            f"{_compat_status(compatibility.get('nvidia_nim'))[:16]:16} "
            f"{_compat_status(compatibility.get('nvidia_nemo'))[:16]:16}",
        )


def _compat_status(entry: Any) -> str:
    if isinstance(entry, dict):
        return str(entry.get("status") or "")
    return ""


def _print_chat_help() -> None:
    print(
        "\n".join(
            (
                "Commands:",
                "  /hardware          choose from models suitable for this machine",
                "  /recommended       choose from recommended local chat models",
                "  /models            choose from local GGUF chat models",
                "  /all               choose from every bundled AbteeXAILab registry entry",
                "  /search <text>     search model id, repo, family, or tags",
                "  /family <name>     filter by family or category",
                "  /categories        show category/family/runtime/tag counts",
                "  /switch <text>     switch directly to a matching model",
                "  /pull [text]       pull the selected model or another matching model",
                "  /local             show pulled models",
                "  /info              show selected model metadata",
                "  /settings          show current runtime settings",
                "  /clear             clear chat history",
                "  /history           show current chat history",
                "  /save <name>       save current chat history",
                "  /load <name>       load a saved chat history",
                "  /export <n> <file> export a saved chat as markdown",
                "  /exit              quit",
            ),
        ),
    )


def _print_local_models(cache_dir: Path | None) -> None:
    local = list_pulled_models(cache_dir)
    print(f"Local cache: {local['cache_root']}")
    if not local["models"]:
        print("No models pulled yet.")
        return
    for index, item in enumerate(local["models"], 1):
        files = item.get("files") or []
        print(f"{index:>2}. {item.get('model_id')} [{item.get('runtime')}, files: {len(files)}]")


def _print_chat_settings(model: Any, args: argparse.Namespace) -> None:
    print(
        json.dumps(
            {
                "model_id": model.model_id,
                "runtime": model.runtime,
                "cache_dir": str(args.cache_dir),
                "max_tokens": args.max_tokens,
                "temperature": args.temperature,
                "context_tokens": args.context_tokens or min(model.context_tokens, 32768),
                "threads": args.threads,
            },
            indent=2,
            sort_keys=True,
        ),
    )


def _installed_version() -> str:
    for package_name in ("lumynax-marama-route", "marama-route", "tinyluminax"):
        try:
            return importlib_metadata.version(package_name)
        except importlib_metadata.PackageNotFoundError:
            continue
    return "source"


def _hf_whoami_status() -> dict[str, Any]:
    try:
        from huggingface_hub import HfApi  # type: ignore[import-not-found]

        payload = HfApi().whoami()
        return {"ok": True, "name": payload.get("name") or payload.get("fullname") or ""}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def subprocess_run(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _print_doctor(result: dict[str, Any]) -> None:
    print("MaramaRoute doctor")
    for name, check in result["checks"].items():
        mark = "ok" if check.get("ok") else "needs attention"
        detail = ""
        if name == "registry":
            detail = f" {check['count']} models, {check['chat_capable']} chat-capable"
        elif name == "cache":
            detail = f" {check['pulled_count']} pulled"
        elif name == "package" or name == "python":
            detail = f" {check['version']}"
        print(f"- {name}: {mark}{detail}")
    if not result["checks"]["llama_cpp"]["ok"]:
        print("Install local GGUF runtime: python -m pip install llama-cpp-python")
    print("Next: MaramaRoute chat  |  MaramaRoute pull qwen25-05b  |  MaramaRoute serve --port 8787")


def _ensure_model_ready(
    models: tuple[Any, ...],
    model: Any,
    *,
    cache_dir: Path | None,
    auto_pull: bool,
) -> Any:
    if local_model_files(model_cache_dir(model, cache_dir)):
        return model
    should_pull = auto_pull
    if not should_pull:
        answer = input(f"{model.model_id} is not pulled. Pull it now? [Y/n] ").strip().lower()
        should_pull = answer in {"", "y", "yes"}
    if not should_pull:
        raise FileNotFoundError(f"{model.model_id} is not available locally.")
    pull_model(models, model.model_id, cache_root=cache_dir)
    return model


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

    config_path = args.config
    if args.live_local:
        config_path = _write_live_local_gateway_config(args)
    return serve_gateway(
        registry_path=args.registry,
        config_path=config_path,
        host=args.host,
        port=args.port,
        open_browser=args.open,
        smoke=args.smoke,
    )


def _write_live_local_gateway_config(args: argparse.Namespace) -> Path:
    payload: dict[str, Any] = {}
    if args.config and args.config.exists():
        payload = _load_json_mapping(args.config)
    payload.update(
        {
            "mode": "local_live",
            "prompt_retention": payload.get("prompt_retention", "not_stored_by_default"),
            "cache_dir": str(args.cache_dir),
            "pull_missing": args.pull_missing,
            "threads": args.threads,
            "context_tokens": args.context_tokens,
        },
    )
    path = Path(tempfile.gettempdir()) / "marama-route-live-local.gateway.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="MaramaRoute",
        description="List, pull, run, and route AbteeX AI Labs LumynaX models from Hugging Face.",
    )
    subparsers = parser.add_subparsers(dest="command")
    chat_live = subparsers.add_parser(
        "chat",
        help="Start a conversational LumynaX model session.",
    )
    _add_chat_arguments(chat_live)
    chat_live.set_defaults(handler=_chat)

    route = subparsers.add_parser("route", help="Select a LumynaX model for a request.")
    route.add_argument("--registry", type=Path, default=None, help="MaramaRoute model registry JSON.")
    route.add_argument("--request", type=Path, required=True, help="Routing request JSON.")
    route.set_defaults(handler=_route)

    models = subparsers.add_parser(
        "models",
        help="Emit the full AbteeX/LumynaX Hugging Face model list.",
    )
    models.add_argument("--registry", type=Path, default=None, help="MaramaRoute model registry JSON.")
    models.add_argument("--search", default="", help="Filter by model id, repo id, family, runtime, or tag.")
    models.add_argument("--family", default="", help="Filter by family name or family tag.")
    models.add_argument("--runtime", default="", help="Filter by runtime, for example llama_cpp or transformers.")
    models.add_argument("--tag", default="", help="Filter by an exact registry tag, for example vllm-compatible.")
    models.add_argument("--limit", type=int, default=0, help="Maximum models to emit; 0 means all matches.")
    models.add_argument("--format", choices=["json", "table"], default="json")
    models.set_defaults(handler=_models)

    chat = subparsers.add_parser(
        "dry-run",
        help="Route a chat-shaped request without invoking a model backend.",
    )
    chat.add_argument("--registry", type=Path, default=None, help="MaramaRoute model registry JSON.")
    chat.add_argument("--request", type=Path, required=True, help="Chat request JSON.")
    chat.set_defaults(handler=_chat_dry_run)

    catalog = subparsers.add_parser(
        "catalog",
        help="Search and filter the MaramaRoute model catalog.",
    )
    catalog.add_argument("--registry", type=Path, default=None, help="MaramaRoute model registry JSON.")
    catalog.add_argument("--search", default="")
    catalog.add_argument("--task", default="")
    catalog.add_argument("--runtime", default="")
    catalog.add_argument("--family", default="")
    catalog.add_argument("--modality", default="")
    catalog.add_argument("--jurisdiction", default="NZ")
    catalog.add_argument("--min-context-tokens", type=int, default=0)
    catalog.add_argument("--requires-json", action=argparse.BooleanOptionalAction, default=False)
    catalog.add_argument("--requires-tools", action=argparse.BooleanOptionalAction, default=False)
    catalog.add_argument("--requires-local", action=argparse.BooleanOptionalAction, default=False)
    catalog.add_argument("--limit", type=int, default=0, help="Maximum rows; 0 means all models.")
    catalog.set_defaults(handler=_catalog)

    compat = subparsers.add_parser(
        "compat",
        help="Show vLLM, NVIDIA NIM, and NVIDIA NeMo compatibility for LumynaX models.",
    )
    compat.add_argument("model", nargs="?", help="Optional model id, repo id, or unique search fragment.")
    compat.add_argument("--registry", type=Path, default=None, help="MaramaRoute model registry JSON.")
    compat.add_argument("--target", default="", help="Runtime target: vllm, nim, nem, nemo, llama-cpp, or all.")
    compat.add_argument(
        "--status",
        default="",
        help="Filter by status such as candidate, experimental, unsupported, usable, or pathway.",
    )
    compat.add_argument("--limit", type=int, default=0, help="Maximum rows; 0 means all models.")
    compat.add_argument("--format", choices=["json", "table"], default="table")
    compat.set_defaults(handler=_compat)

    categories = subparsers.add_parser(
        "categories",
        aliases=["families"],
        help="Show model families, runtimes, tags, modalities, local capability, and deployment categories.",
    )
    categories.add_argument("--registry", type=Path, default=None, help="MaramaRoute model registry JSON.")
    categories.add_argument("--limit", type=int, default=18)
    categories.add_argument("--format", choices=["json", "table"], default="table")
    categories.set_defaults(handler=_categories)

    compare = subparsers.add_parser(
        "compare",
        help="Compare routed fit for selected model ids.",
    )
    compare.add_argument("--registry", type=Path, default=None, help="MaramaRoute model registry JSON.")
    compare.add_argument("--model", action="append", required=True, help="Model id, repeatable or comma-separated.")
    compare.add_argument("--request", type=Path, default=None, help="Optional routing request JSON.")
    compare.set_defaults(handler=_compare)

    matrix = subparsers.add_parser(
        "matrix",
        help="Run the built-in sovereign routing scenario matrix.",
    )
    matrix.add_argument("--registry", type=Path, default=None, help="MaramaRoute model registry JSON.")
    matrix.add_argument("--allow-blocked-exit-zero", action=argparse.BooleanOptionalAction, default=False)
    matrix.set_defaults(handler=_matrix)

    analytics = subparsers.add_parser("analytics", help="Summarise registry coverage.")
    analytics.add_argument("--registry", type=Path, default=None, help="MaramaRoute model registry JSON.")
    analytics.set_defaults(handler=_analytics)

    recommend = subparsers.add_parser(
        "recommend",
        help="Ask the router for the best LumynaX model from plain CLI options.",
    )
    recommend.add_argument("prompt", nargs="*", help="Prompt or task description.")
    recommend.add_argument("--prompt-text", default="", help="Prompt text, useful when avoiding shell quoting.")
    recommend.add_argument("--registry", type=Path, default=None, help="MaramaRoute model registry JSON.")
    recommend.add_argument("--task", default="", help="Task type: code, reasoning, multimodal, general.")
    recommend.add_argument("--sensitivity", default="internal", help="Data sensitivity: internal, personal, restricted.")
    recommend.add_argument("--jurisdiction", default="NZ")
    recommend.add_argument("--modality", default="text", help="Comma-separated modalities.")
    recommend.add_argument("--min-context-tokens", type=int, default=4096)
    recommend.add_argument("--requires-json", action=argparse.BooleanOptionalAction, default=False)
    recommend.add_argument("--requires-tools", action=argparse.BooleanOptionalAction, default=False)
    recommend.add_argument("--requires-local", action=argparse.BooleanOptionalAction, default=True)
    recommend.set_defaults(handler=_recommend)

    doctor = subparsers.add_parser("doctor", help="Check MaramaRoute install, registry, cache, and runtimes.")
    doctor.add_argument("--registry", type=Path, default=None, help="MaramaRoute model registry JSON.")
    doctor.add_argument("--cache-dir", type=Path, default=default_cache_root(), help="Local model cache directory.")
    doctor.add_argument("--online", action=argparse.BooleanOptionalAction, default=False)
    doctor.add_argument("--hardware", action=argparse.BooleanOptionalAction, default=False)
    doctor.add_argument("--json", action=argparse.BooleanOptionalAction, default=False)
    doctor.add_argument("--allow-warnings", action=argparse.BooleanOptionalAction, default=True)
    doctor.set_defaults(handler=_doctor)

    init = subparsers.add_parser("init", help="Create a local MaramaRoute config and starter aliases.")
    init.add_argument("model", nargs="?", help="Optional starter model id, repo id, alias, or search fragment.")
    init.add_argument("--registry", type=Path, default=None, help="MaramaRoute model registry JSON.")
    init.add_argument("--cache-dir", type=Path, default=default_cache_root(), help="Local model cache directory.")
    init.add_argument("--state-dir", type=Path, default=None, help="MaramaRoute state directory.")
    init.add_argument("--host", default="127.0.0.1")
    init.add_argument("--port", type=int, default=8787)
    init.add_argument("--live-local", action=argparse.BooleanOptionalAction, default=True)
    init.add_argument("--agent", default="", choices=["", "generic", "claude-code", "opencode", "hpe", "hpe-slurm"])
    init.add_argument("--hpe", action=argparse.BooleanOptionalAction, default=False)
    init.add_argument("--pull", action=argparse.BooleanOptionalAction, default=False)
    init.add_argument("--self-test", action=argparse.BooleanOptionalAction, default=True)
    init.set_defaults(handler=_init)

    hardware = subparsers.add_parser("hardware", help="Inspect local hardware and recommend runnable LumynaX models.")
    hardware.add_argument("--registry", type=Path, default=None, help="MaramaRoute model registry JSON.")
    hardware.add_argument("--cache-dir", type=Path, default=default_cache_root(), help="Local model cache directory.")
    hardware.add_argument("--recommend", action=argparse.BooleanOptionalAction, default=True)
    hardware.add_argument("--limit", type=int, default=8)
    hardware.set_defaults(handler=_hardware)

    model_ops = subparsers.add_parser("model", help="Manage local MaramaRoute model cache.")
    model_ops.add_argument("model_action", choices=["ls", "list", "disk", "verify", "rm", "prune", "estimate", "ps"])
    model_ops.add_argument("model", nargs="?", help="Model id, alias, repo id, or unique search fragment.")
    model_ops.add_argument("--registry", type=Path, default=None, help="MaramaRoute model registry JSON.")
    model_ops.add_argument("--cache-dir", type=Path, default=default_cache_root(), help="Local model cache directory.")
    model_ops.add_argument("--dry-run", action=argparse.BooleanOptionalAction, default=False)
    model_ops.add_argument("--deep", action=argparse.BooleanOptionalAction, default=False, help="Hash local files during verify.")
    model_ops.add_argument("--write-hashes", action=argparse.BooleanOptionalAction, default=False, help="Write a SHA256 manifest during deep verify.")
    model_ops.add_argument("--remote-sizes", action=argparse.BooleanOptionalAction, default=False, help="Fetch exact Hugging Face file sizes for estimate.")
    model_ops.add_argument("--all-files", action=argparse.BooleanOptionalAction, default=False, help="Plan or inspect all repository files where supported.")
    model_ops.set_defaults(handler=_model_ops)

    for command_name, action_name, help_text in (
        ("ls", "ls", "List pulled models and cache size."),
        ("ps", "ps", "Show local MaramaRoute runtime status."),
        ("disk", "disk", "Show model-cache disk use."),
        ("verify", "verify", "Verify pulled model files."),
        ("prune", "prune", "Remove orphaned cache directories."),
    ):
        command = subparsers.add_parser(command_name, help=help_text)
        command.add_argument("--registry", type=Path, default=None, help="MaramaRoute model registry JSON.")
        command.add_argument("--cache-dir", type=Path, default=default_cache_root(), help="Local model cache directory.")
        command.add_argument("--dry-run", action=argparse.BooleanOptionalAction, default=False)
        command.add_argument("--deep", action=argparse.BooleanOptionalAction, default=False, help="Hash local files during verify.")
        command.add_argument("--write-hashes", action=argparse.BooleanOptionalAction, default=False, help="Write a SHA256 manifest during deep verify.")
        command.add_argument("--remote-sizes", action=argparse.BooleanOptionalAction, default=False, help="Fetch exact Hugging Face file sizes for estimate.")
        command.add_argument("--all-files", action=argparse.BooleanOptionalAction, default=False, help="Plan or inspect all repository files where supported.")
        command.set_defaults(handler=_model_ops, model_action=action_name, model=None)

    rm = subparsers.add_parser("rm", help="Remove one pulled model from the local cache.")
    rm.add_argument("model", help="Model id, alias, repo id, or unique search fragment.")
    rm.add_argument("--registry", type=Path, default=None, help="MaramaRoute model registry JSON.")
    rm.add_argument("--cache-dir", type=Path, default=default_cache_root(), help="Local model cache directory.")
    rm.add_argument("--dry-run", action=argparse.BooleanOptionalAction, default=False)
    rm.set_defaults(handler=_model_ops, model_action="rm")

    alias = subparsers.add_parser("alias", help="Manage local model aliases and favorites.")
    alias.add_argument("alias_action", choices=["list", "set", "rm", "favorite"])
    alias.add_argument("name", nargs="?", help="Alias name.")
    alias.add_argument("model", nargs="?", help="Model id, repo id, or unique search fragment.")
    alias.add_argument("--registry", type=Path, default=None, help="MaramaRoute model registry JSON.")
    alias.add_argument("--state-dir", type=Path, default=None, help="MaramaRoute state directory.")
    alias.set_defaults(handler=_alias)

    favorite = subparsers.add_parser("favorite", help="Mark a LumynaX model as a favorite.")
    favorite.add_argument("model", help="Model id, repo id, or unique search fragment.")
    favorite.add_argument("--registry", type=Path, default=None, help="MaramaRoute model registry JSON.")
    favorite.add_argument("--state-dir", type=Path, default=None, help="MaramaRoute state directory.")
    favorite.set_defaults(handler=_alias, alias_action="favorite", name=None)

    bench = subparsers.add_parser("bench", help="Benchmark a pulled local GGUF model or dry-run the benchmark plan.")
    bench.add_argument("model", help="Model id, alias, repo id, or unique search fragment.")
    bench.add_argument("--registry", type=Path, default=None, help="MaramaRoute model registry JSON.")
    bench.add_argument("--cache-dir", type=Path, default=default_cache_root(), help="Local model cache directory.")
    bench.add_argument("--prompt-text", default="")
    bench.add_argument("--max-tokens", type=int, default=64)
    bench.add_argument("--pull", action=argparse.BooleanOptionalAction, default=False)
    bench.add_argument("--dry-run", action=argparse.BooleanOptionalAction, default=True)
    bench.set_defaults(handler=_bench)

    eval_cmd = subparsers.add_parser("eval", help="Run deterministic MaramaRoute routing evals.")
    eval_cmd.add_argument("--registry", type=Path, default=None, help="MaramaRoute model registry JSON.")
    eval_cmd.add_argument("--suite", default="routing")
    eval_cmd.add_argument("--allow-blocked-exit-zero", action=argparse.BooleanOptionalAction, default=False)
    eval_cmd.set_defaults(handler=_eval)

    audit = subparsers.add_parser("audit", help="List, show, export, or record routing audit receipts.")
    audit.add_argument("audit_action", choices=["list", "show", "export", "record"])
    audit.add_argument("receipt", nargs="?", help="Receipt id for `show`.")
    audit.add_argument("--registry", type=Path, default=None, help="MaramaRoute model registry JSON.")
    audit.add_argument("--request", type=Path, default=None, help="Routing request JSON for `record`.")
    audit.add_argument("--output", type=Path, default=Path("marama-route-audit.json"))
    audit.add_argument("--state-dir", type=Path, default=None, help="MaramaRoute state directory.")
    audit.set_defaults(handler=_audit)

    opencode = subparsers.add_parser(
        "opencode-config",
        help="Emit an OpenCode-compatible MaramaRoute provider config.",
    )
    opencode.add_argument("--registry", type=Path, default=None, help="MaramaRoute model registry JSON.")
    opencode.add_argument("--base-url", default="http://127.0.0.1:8787/v1")
    opencode.set_defaults(handler=_opencode_config)

    agent = subparsers.add_parser(
        "agent-config",
        aliases=["agent"],
        help="Emit command-bridge config for coding agents, local gateways, or HPE/Slurm jobs.",
    )
    agent.add_argument("--registry", type=Path, default=None, help="MaramaRoute model registry JSON.")
    agent.add_argument("--target", default="generic", choices=["generic", "claude-code", "opencode", "hpe", "hpe-slurm"])
    agent.add_argument("--model", default="", help="Default model id, repo id, or unique search fragment.")
    agent.add_argument("--base-url", default="http://127.0.0.1:8787/v1")
    agent.add_argument("--host", default="127.0.0.1")
    agent.add_argument("--port", type=int, default=8787)
    agent.add_argument("--cache-dir", type=Path, default=None)
    agent.add_argument("--output", type=Path, default=None)
    agent.set_defaults(handler=_agent_config)

    agent_init = subparsers.add_parser("agent-init", help="Write local agent workspace files for MaramaRoute.")
    agent_init.add_argument("model", nargs="?", help="Optional default model id, repo id, alias, or search fragment.")
    agent_init.add_argument("--model", dest="model_option", default="", help="Default model id, repo id, alias, or search fragment.")
    agent_init.add_argument("--registry", type=Path, default=None, help="MaramaRoute model registry JSON.")
    agent_init.add_argument("--target", default="claude-code", choices=["generic", "claude-code", "opencode", "hpe", "hpe-slurm"])
    agent_init.add_argument("--output-dir", type=Path, default=Path("."))
    agent_init.add_argument("--base-url", default="http://127.0.0.1:8787/v1")
    agent_init.add_argument("--host", default="127.0.0.1")
    agent_init.add_argument("--port", type=int, default=8787)
    agent_init.add_argument("--cache-dir", type=Path, default=default_cache_root())
    agent_init.set_defaults(handler=_agent_init)

    agent_doctor = subparsers.add_parser("agent-doctor", help="Check agent bridge config and local gateway readiness.")
    agent_doctor.add_argument("--registry", type=Path, default=None, help="MaramaRoute model registry JSON.")
    agent_doctor.add_argument("--target", default="claude-code", choices=["generic", "claude-code", "opencode", "hpe", "hpe-slurm"])
    agent_doctor.add_argument("--model", default="", help="Default model id, repo id, alias, or search fragment.")
    agent_doctor.add_argument("--base-url", default="http://127.0.0.1:8787/v1")
    agent_doctor.add_argument("--host", default="127.0.0.1")
    agent_doctor.add_argument("--port", type=int, default=8787)
    agent_doctor.add_argument("--cache-dir", type=Path, default=default_cache_root())
    agent_doctor.add_argument("--health-check", action=argparse.BooleanOptionalAction, default=False)
    agent_doctor.add_argument("--allow-warnings", action=argparse.BooleanOptionalAction, default=True)
    agent_doctor.set_defaults(handler=_agent_doctor)

    hpe = subparsers.add_parser("hpe-job", help="Emit an HPE/HPC Slurm job script for MaramaRoute.")
    hpe.add_argument("model", nargs="?", help="Model id, repo id, or unique search fragment.")
    hpe.add_argument("--registry", type=Path, default=None, help="MaramaRoute model registry JSON.")
    hpe.add_argument("--mode", choices=["serve", "pull", "run"], default="serve")
    hpe.add_argument("--prompt-text", default="Say kia ora in one sentence.")
    hpe.add_argument("--port", type=int, default=8787)
    hpe.add_argument("--backend", choices=["auto", "local-live", "vllm", "nim", "nemo", "external"], default="auto")
    hpe.add_argument("--backend-port", type=int, default=8000)
    hpe.add_argument("--backend-base-url", default="")
    hpe.add_argument("--backend-model", default="")
    hpe.add_argument("--backend-command", default="", help="Optional command to start a NIM/NeMo/external backend before MaramaRoute.")
    hpe.add_argument("--api-key-env", default="")
    hpe.add_argument("--vllm-args", default="", help="Extra vLLM serve args, for example '--tensor-parallel-size 2'.")
    hpe.add_argument("--cache-dir", default="$SCRATCH/marama-route/models")
    hpe.add_argument("--job-name", default="marama-route")
    hpe.add_argument("--partition", default="")
    hpe.add_argument("--time", default="02:00:00")
    hpe.add_argument("--cpus", type=int, default=8)
    hpe.add_argument("--memory", default="32G")
    hpe.add_argument("--gpus", type=int, default=0)
    hpe.add_argument("--output", type=Path, default=None)
    hpe.set_defaults(handler=_hpe_job)

    hpe_ops = subparsers.add_parser("hpe", help="Prepare or inspect HPE/HPC MaramaRoute workflows.")
    hpe_ops.add_argument("hpe_action", choices=["plan", "init", "submit", "tunnel", "status"])
    hpe_ops.add_argument("model", nargs="?", help="Optional model id, repo id, alias, or search fragment.")
    hpe_ops.add_argument("--registry", type=Path, default=None, help="MaramaRoute model registry JSON.")
    hpe_ops.add_argument("--output-dir", type=Path, default=Path("marama-route-hpe"))
    hpe_ops.add_argument("--port", type=int, default=8787)
    hpe_ops.add_argument("--backend", choices=["auto", "local-live", "vllm", "nim", "nemo", "external"], default="auto")
    hpe_ops.add_argument("--backend-port", type=int, default=8000)
    hpe_ops.add_argument("--backend-base-url", default="")
    hpe_ops.add_argument("--backend-model", default="")
    hpe_ops.add_argument("--backend-command", default="", help="Optional command to start a NIM/NeMo/external backend before MaramaRoute.")
    hpe_ops.add_argument("--api-key-env", default="")
    hpe_ops.add_argument("--vllm-args", default="", help="Extra vLLM serve args, for example '--tensor-parallel-size 2'.")
    hpe_ops.add_argument("--partition", default="")
    hpe_ops.add_argument("--time", default="02:00:00")
    hpe_ops.add_argument("--memory", default="32G")
    hpe_ops.add_argument("--gpus", type=int, default=0)
    hpe_ops.add_argument("--execute", action=argparse.BooleanOptionalAction, default=False)
    hpe_ops.set_defaults(handler=_hpe)

    update_registry = subparsers.add_parser("update-registry", help="Download a fresh registry JSON from Hugging Face.")
    update_registry.add_argument("--registry", type=Path, default=None, help="Local registry JSON to diff against.")
    update_registry.add_argument("--repo-id", default="AbteeXAILab/marama-route")
    update_registry.add_argument("--filename", default="configs/lumynax_model_registry.json")
    update_registry.add_argument("--output", type=Path, default=None)
    update_registry.add_argument("--dry-run", action=argparse.BooleanOptionalAction, default=True)
    update_registry.add_argument("--diff", action=argparse.BooleanOptionalAction, default=False)
    update_registry.set_defaults(handler=_update_registry)

    pull = subparsers.add_parser(
        "pull",
        help="Download a LumynaX model artifact from Hugging Face into the local MaramaRoute cache.",
    )
    pull.add_argument("model", nargs="?", help="Model id, repo id, or unique search fragment.")
    pull.add_argument("--registry", type=Path, default=None, help="MaramaRoute model registry JSON.")
    pull.add_argument("--cache-dir", type=Path, default=default_cache_root(), help="Local model cache directory.")
    pull.add_argument("--search", default="", help="Batch-pull models matching text.")
    pull.add_argument("--family", default="", help="Batch-pull models matching a family or tag.")
    pull.add_argument("--runtime", default="", help="Batch-pull models for one runtime.")
    pull.add_argument("--limit", type=int, default=0, help="Maximum models for batch pull; 0 means all matches.")
    pull.add_argument(
        "--chat-only",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Restrict batch pulls to direct local GGUF chat models.",
    )
    pull.add_argument("--yes", action=argparse.BooleanOptionalAction, default=False, help="Confirm batch pulls.")
    pull.add_argument("--all-files", action=argparse.BooleanOptionalAction, default=False)
    pull.add_argument("--force", action=argparse.BooleanOptionalAction, default=False)
    pull.add_argument("--estimate", action=argparse.BooleanOptionalAction, default=False)
    pull.add_argument("--remote-sizes", action=argparse.BooleanOptionalAction, default=False)
    pull.add_argument("--verify", action=argparse.BooleanOptionalAction, default=False)
    pull.add_argument("--deep-verify", action=argparse.BooleanOptionalAction, default=False)
    pull.add_argument("--write-hashes", action=argparse.BooleanOptionalAction, default=False)
    pull.add_argument("--dry-run", action=argparse.BooleanOptionalAction, default=False)
    pull.set_defaults(handler=_pull)

    local = subparsers.add_parser("local", help="List models already pulled into the local MaramaRoute cache.")
    local.add_argument("--cache-dir", type=Path, default=default_cache_root(), help="Local model cache directory.")
    local.set_defaults(handler=_local)

    run = subparsers.add_parser("run", help="Run or chat with a pulled LumynaX model.")
    _add_chat_arguments(run)
    run.set_defaults(handler=_run)

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
        help="Run the local MaramaRoute gateway and browser console.",
    )
    serve.add_argument("--registry", type=Path, default=None, help="MaramaRoute model registry JSON.")
    serve.add_argument("--config", type=Path, default=None, help="Gateway backend config JSON.")
    serve.add_argument("--host", type=str, default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8787)
    serve.add_argument("--open", action=argparse.BooleanOptionalAction, default=False)
    serve.add_argument("--smoke", action=argparse.BooleanOptionalAction, default=False)
    serve.add_argument("--live-local", action=argparse.BooleanOptionalAction, default=False)
    serve.add_argument("--pull-missing", action=argparse.BooleanOptionalAction, default=False)
    serve.add_argument("--cache-dir", type=Path, default=default_cache_root(), help="Local model cache directory.")
    serve.add_argument("--context-tokens", type=int, default=None)
    serve.add_argument("--threads", type=int, default=None)
    serve.set_defaults(handler=_serve)
    return parser


def _add_chat_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("model", nargs="?", help="Model id, repo id, or unique search fragment.")
    parser.add_argument("prompt", nargs="*", help="Prompt text. Omit it to enter chat mode.")
    parser.add_argument("--prompt-text", default="", help="Prompt text, useful when avoiding shell quoting.")
    parser.add_argument("--registry", type=Path, default=None, help="MaramaRoute model registry JSON.")
    parser.add_argument("--cache-dir", type=Path, default=default_cache_root(), help="Local model cache directory.")
    parser.add_argument("--pull", action=argparse.BooleanOptionalAction, default=False, help="Download before running.")
    parser.add_argument("--max-tokens", type=int, default=192)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--context-tokens", type=int, default=None)
    parser.add_argument("--threads", type=int, default=None)
    parser.add_argument("--stream", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--dry-run", action=argparse.BooleanOptionalAction, default=False)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    raw_argv = list(argv) if argv is not None else sys.argv[1:]
    if len(raw_argv) >= 2 and raw_argv[0] == "agent" and raw_argv[1] == "init":
        raw_argv = ["agent-init", *raw_argv[2:]]
    elif len(raw_argv) >= 2 and raw_argv[0] == "agent" and raw_argv[1] in {"doctor", "status", "check"}:
        raw_argv = ["agent-doctor", *raw_argv[2:]]
    elif len(raw_argv) >= 2 and raw_argv[0] == "agent" and raw_argv[1] in {"config", "export"}:
        raw_argv = ["agent-config", *raw_argv[2:]]
    args = parser.parse_args(raw_argv)
    handler = getattr(args, "handler", None)
    if handler is None:
        if argv is None and not raw_argv and sys.stdin.isatty():
            models = load_model_registry(default_registry_path())
            defaults = argparse.Namespace(
                model=None,
                registry=None,
                cache_dir=default_cache_root(),
                pull=False,
                max_tokens=192,
                temperature=0.2,
                context_tokens=None,
                threads=None,
                stream=False,
                dry_run=False,
            )
            return _conversation(defaults, models)
        parser.print_help()
        return 0
    try:
        return int(handler(args))
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
