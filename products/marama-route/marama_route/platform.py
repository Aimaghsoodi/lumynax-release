from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .compat import model_runtime_compatibility
from .gateway import build_models_response, route_chat_payload
from .registry import ModelEndpoint, RoutingRequest
from .router import SovereignModelRouter

DEFAULT_ROUTE_SCENARIOS: tuple[dict[str, Any], ...] = (
    {
        "name": "Restricted NZ code",
        "prompt": "Refactor a private New Zealand Python service and return a JSON diff plan.",
        "task_type": "code",
        "modalities": ["text"],
        "jurisdiction": "NZ",
        "data_sensitivity": "restricted",
        "min_context_tokens": 4096,
        "requires_local": True,
        "requires_json": True,
        "requires_tools": False,
        "max_fallbacks": 3,
    },
    {
        "name": "Personal memory",
        "prompt": "Summarise local operator preferences without exposing raw personal notes.",
        "task_type": "general",
        "modalities": ["text"],
        "jurisdiction": "NZ",
        "data_sensitivity": "personal",
        "min_context_tokens": 4096,
        "requires_local": True,
        "requires_json": False,
        "requires_tools": False,
        "max_fallbacks": 3,
    },
    {
        "name": "Vision document",
        "prompt": "Read a scanned table image and extract structured rows.",
        "task_type": "multimodal",
        "modalities": ["text", "image"],
        "jurisdiction": "NZ",
        "data_sensitivity": "internal",
        "min_context_tokens": 4096,
        "requires_local": False,
        "requires_json": True,
        "requires_tools": False,
        "max_fallbacks": 3,
    },
    {
        "name": "Reasoning brief",
        "prompt": "Reason through a procurement risk register and produce a concise decision memo.",
        "task_type": "reasoning",
        "modalities": ["text"],
        "jurisdiction": "NZ",
        "data_sensitivity": "internal",
        "min_context_tokens": 8192,
        "requires_local": True,
        "requires_json": False,
        "requires_tools": False,
        "max_fallbacks": 3,
    },
)


def build_registry_analytics(models: tuple[ModelEndpoint, ...]) -> dict[str, Any]:
    runtimes = Counter(model.runtime for model in models)
    families = Counter(model.family for model in models)
    modalities = Counter(modality for model in models for modality in model.modalities)
    tiers = Counter(str(model.sovereignty_tier) for model in models)
    resident_nz = sum(1 for model in models if "NZ" in model.residency)
    json_ready = sum(1 for model in models if model.supports_json)
    tool_ready = sum(1 for model in models if model.supports_tools)
    local_runtimes = sum(1 for model in models if _is_local_runtime(model.runtime))
    context_values = [model.context_tokens for model in models]
    return {
        "model_count": len(models),
        "resident_nz": resident_nz,
        "local_runtimes": local_runtimes,
        "json_ready": json_ready,
        "tool_ready": tool_ready,
        "max_context_tokens": max(context_values) if context_values else 0,
        "avg_context_tokens": round(sum(context_values) / len(context_values), 2) if context_values else 0,
        "runtimes": dict(sorted(runtimes.items())),
        "families": dict(sorted(families.items())),
        "modalities": dict(sorted(modalities.items())),
        "sovereignty_tiers": dict(sorted(tiers.items())),
        "top_models": [model_summary(model) for model in _top_models(models, limit=8)],
    }


def catalog_models(
    models: tuple[ModelEndpoint, ...],
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    filters = filters or {}
    search = str(filters.get("search") or "").strip().lower()
    runtime = str(filters.get("runtime") or "").strip().lower()
    family = str(filters.get("family") or "").strip().lower()
    modality = str(filters.get("modality") or "").strip().lower()
    task_type = str(filters.get("task_type") or "").strip().lower()
    jurisdiction = str(filters.get("jurisdiction") or "").strip().upper()
    min_context = int(filters.get("min_context_tokens") or 0)
    raw_limit = filters.get("limit")
    limit = int(raw_limit) if raw_limit not in (None, "") else 50
    requires_json = bool(filters.get("requires_json", False))
    requires_tools = bool(filters.get("requires_tools", False))
    requires_local = bool(filters.get("requires_local", False))

    filtered: list[ModelEndpoint] = []
    for model in models:
        haystack = " ".join(
            (
                model.model_id,
                model.repo_id,
                model.family,
                model.runtime,
                " ".join(model.tags),
            ),
        ).lower()
        if search and search not in haystack:
            continue
        if runtime and model.runtime.lower() != runtime:
            continue
        if family and model.family.lower() != family:
            continue
        if modality and modality not in {item.lower() for item in model.modalities}:
            continue
        if task_type and not _matches_task(model, task_type):
            continue
        if jurisdiction and jurisdiction not in model.residency:
            continue
        if min_context and model.context_tokens < min_context:
            continue
        if requires_json and not model.supports_json:
            continue
        if requires_tools and not model.supports_tools:
            continue
        if requires_local and not _is_local_runtime(model.runtime):
            continue
        filtered.append(model)

    ranked = sorted(filtered, key=_catalog_sort_key, reverse=True)
    return {
        "ok": True,
        "count": len(ranked),
        "filters": filters,
        "models": [model_summary(model) for model in (ranked if limit <= 0 else ranked[:limit])],
    }


def compare_models(
    models: tuple[ModelEndpoint, ...],
    model_ids: list[str],
    request_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    index = {model.model_id: model for model in models}
    selected = [index[model_id] for model_id in model_ids if model_id in index]
    missing = [model_id for model_id in model_ids if model_id not in index]
    request = RoutingRequest.from_payload(request_payload or DEFAULT_ROUTE_SCENARIOS[0])
    route_scores = SovereignModelRouter(tuple(selected)).route(request).scores if selected else {}
    rows = []
    for model in selected:
        row = model_summary(model)
        row["route_score"] = route_scores.get(model.model_id)
        row["operator_score"] = _operator_score(model)
        rows.append(row)
    winner = max(rows, key=lambda item: (item.get("route_score") or -1, item["operator_score"]), default=None)
    return {
        "ok": bool(rows),
        "missing": missing,
        "request": request.to_dict(),
        "winner": winner,
        "models": rows,
    }


def route_scenario_matrix(
    models: tuple[ModelEndpoint, ...],
    scenarios: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    router = SovereignModelRouter(models)
    rows = []
    for scenario in scenarios or [dict(item) for item in DEFAULT_ROUTE_SCENARIOS]:
        request = RoutingRequest.from_payload(scenario)
        decision = router.route(request)
        selected = decision.selected_model
        rows.append(
            {
                "name": scenario.get("name", request.task_type),
                "ok": selected is not None,
                "task_type": request.task_type,
                "sensitivity": request.data_sensitivity,
                "selected_model": selected.model_id if selected else None,
                "runtime": selected.runtime if selected else None,
                "fallback_count": len(decision.fallback_models),
                "rejected_count": len(decision.rejected),
                "reasons": list(decision.reasons),
            },
        )
    return {"ok": all(row["ok"] for row in rows), "scenarios": rows}


def build_opencode_provider_config(
    models: tuple[ModelEndpoint, ...],
    *,
    base_url: str = "http://127.0.0.1:8787/v1",
    provider_id: str = "abteex-marama",
) -> dict[str, Any]:
    route = SovereignModelRouter(models).route(RoutingRequest.from_payload(DEFAULT_ROUTE_SCENARIOS[0]))
    default_model = route.selected_model or (_top_models(models, limit=1)[0] if models else None)
    catalog = _top_models(models, limit=14)
    model_entries = {
        model.model_id: {
            "name": model.model_id,
            "context": model.context_tokens,
            "modalities": list(model.modalities),
            "residency": list(model.residency),
            "runtime": model.runtime,
        }
        for model in catalog
    }
    return {
        "$schema": "https://opencode.ai/config.json",
        "provider": {
            provider_id: {
                "name": "AbteeX MaramaRoute",
                "options": {
                    "baseURL": base_url,
                    "apiKey": "${ABTEEX_MARAMA_API_KEY:-local-dev}",
                },
                "models": model_entries,
            },
        },
        "model": f"{provider_id}/{default_model.model_id}" if default_model else "",
        "small_model": f"{provider_id}/{catalog[-1].model_id}" if catalog else "",
    }


def recommend_model(
    models: tuple[ModelEndpoint, ...],
    *,
    prompt: str = "",
    task_type: str = "",
    jurisdiction: str = "NZ",
    data_sensitivity: str = "internal",
    min_context_tokens: int = 4096,
    requires_local: bool = True,
    requires_json: bool = False,
    requires_tools: bool = False,
    modalities: tuple[str, ...] = ("text",),
    max_fallbacks: int = 5,
) -> dict[str, Any]:
    request = RoutingRequest.from_payload(
        {
            "prompt": prompt,
            "task_type": task_type or _infer_task_type(prompt, set(modalities)),
            "modalities": list(modalities),
            "jurisdiction": jurisdiction,
            "data_sensitivity": data_sensitivity,
            "min_context_tokens": min_context_tokens,
            "requires_local": requires_local,
            "requires_json": requires_json,
            "requires_tools": requires_tools,
            "max_fallbacks": max_fallbacks,
        },
    )
    decision = SovereignModelRouter(models).route(request)
    selected = decision.selected_model
    return {
        "ok": selected is not None,
        "request": request.to_dict(),
        "selected_model": model_summary(selected) if selected is not None else None,
        "fallback_models": [model_summary(model) for model in decision.fallback_models],
        "rejected_count": len(decision.rejected),
        "reasons": list(decision.reasons),
        "scores": dict(decision.scores),
        "next_commands": _next_model_commands(selected),
    }


def build_agent_bridge_config(
    models: tuple[ModelEndpoint, ...],
    *,
    target: str = "generic",
    base_url: str = "http://127.0.0.1:8787/v1",
    host: str = "127.0.0.1",
    port: int = 8787,
    cache_dir: Path | None = None,
    model_id: str = "",
) -> dict[str, Any]:
    normalized = target.strip().lower().replace("_", "-")
    selected = _select_export_model(models, model_id)
    cache_value = str(cache_dir) if cache_dir is not None else "${MARAMA_ROUTE_CACHE:-~/.cache/abteex-ai/marama-route/models}"
    commands = {
        "start_gateway": f"MaramaRoute serve --host {host} --port {port} --live-local",
        "health": f"curl {base_url.removesuffix('/v1')}/health",
        "list_models": "MaramaRoute catalog --limit 0",
        "recommend": "MaramaRoute recommend --task code --sensitivity restricted --prompt-text \"Describe the task\"",
        "pull": f"MaramaRoute pull {selected.model_id}" if selected is not None else "MaramaRoute pull <model-id>",
        "chat": f"MaramaRoute chat {selected.model_id}" if selected is not None else "MaramaRoute chat <model-id>",
    }
    config: dict[str, Any] = {
        "ok": True,
        "target": normalized,
        "product": "LumynaX MaramaRoute",
        "mode": "local_command_bridge",
        "base_url": base_url,
        "cache_dir": cache_value,
        "default_model": model_summary(selected) if selected is not None else None,
        "commands": commands,
        "environment": {
            "MARAMA_ROUTE_BASE_URL": base_url,
            "MARAMA_ROUTE_CACHE": cache_value,
            "ABTEEX_MARAMA_API_KEY": "local-dev",
        },
    }
    if normalized in {"claude-code", "claude"}:
        config["target"] = "claude-code"
        config["workspace_files"] = {
            "CLAUDE.md": [
                "Use MaramaRoute for LumynaX model selection and local generation.",
                f"Start the local router with `{commands['start_gateway']}` when a project needs routed model calls.",
                f"Use `{commands['recommend']}` to choose a model for sensitive local work.",
            ],
        }
        config["notes"] = [
            "This export is a command bridge. It does not replace the coding agent runtime.",
            "Keep sensitive prompts on the local MaramaRoute path when project policy requires it.",
        ]
    elif normalized in {"hpe", "hpe-slurm", "slurm", "hpc"}:
        config["target"] = "hpe-slurm"
        config["environment"].update(
            {
                "HF_HOME": "${SCRATCH:-$HOME}/.cache/huggingface",
                "MARAMA_ROUTE_CACHE": "${SCRATCH:-$HOME}/marama-route/models",
                "MARAMA_ROUTE_HOST": "0.0.0.0",
                "MARAMA_ROUTE_PORT": str(port),
                "MARAMA_BACKEND": "auto",
                "MARAMA_BACKEND_BASE_URL": "http://127.0.0.1:8000/v1",
            },
        )
        config["commands"].update(
            {
                "serve_on_compute_node": f"MaramaRoute serve --host 0.0.0.0 --port {port} --config gateway.hpe.json",
                "serve_local_live": f"MaramaRoute serve --host 0.0.0.0 --port {port} --live-local --cache-dir $MARAMA_ROUTE_CACHE",
                "pull_to_scratch": f"MaramaRoute pull {selected.model_id if selected else '<model-id>'} --cache-dir $MARAMA_ROUTE_CACHE",
            },
        )
        config["scheduler"] = {
            "type": "slurm",
            "script_command": "MaramaRoute hpe-job "
            + (selected.model_id if selected is not None else "<model-id>")
            + " --mode serve",
        }
    elif normalized == "opencode":
        config["provider_config"] = build_opencode_provider_config(models, base_url=base_url)
    return config


def render_hpe_slurm_script(
    *,
    model_id: str,
    repo_id: str = "",
    model_runtime: str = "",
    mode: str = "serve",
    prompt: str = "Say kia ora in one sentence.",
    port: int = 8787,
    backend: str = "auto",
    backend_port: int = 8000,
    backend_base_url: str = "",
    backend_model: str = "",
    backend_command: str = "",
    api_key_env: str = "",
    vllm_args: str = "",
    cache_dir: str = "$SCRATCH/marama-route/models",
    job_name: str = "marama-route",
    partition: str = "",
    time_limit: str = "02:00:00",
    cpus: int = 8,
    memory: str = "32G",
    gpus: int = 0,
) -> str:
    selected_backend = normalize_hpe_backend(backend, model_runtime=model_runtime)
    hf_model = repo_id or f"AbteeXAILab/{model_id}"
    backend_model = backend_model or model_id
    backend_base_url = backend_base_url or f"http://127.0.0.1:{backend_port}/v1"
    lines = [
        "#!/usr/bin/env bash",
        f"#SBATCH --job-name={job_name}",
        f"#SBATCH --time={time_limit}",
        f"#SBATCH --cpus-per-task={cpus}",
        f"#SBATCH --mem={memory}",
        "#SBATCH --output=marama-route-%j.out",
        "#SBATCH --error=marama-route-%j.err",
    ]
    if partition:
        lines.append(f"#SBATCH --partition={partition}")
    if gpus > 0:
        lines.append(f"#SBATCH --gres=gpu:{gpus}")
    lines.extend(
        [
            "",
            "set -euo pipefail",
            "",
            f"export MARAMA_ROUTE_CACHE=\"{cache_dir}\"",
            "export HF_HOME=\"${HF_HOME:-${SCRATCH:-$HOME}/.cache/huggingface}\"",
            f"export MARAMA_MODEL_ID={_shell_quote(model_id)}",
            f"export MARAMA_HF_MODEL={_shell_quote(hf_model)}",
            f"export MARAMA_ROUTE_PORT={port}",
            "export MARAMA_ROUTE_HOST=\"${MARAMA_ROUTE_HOST:-0.0.0.0}\"",
            f"export MARAMA_BACKEND={_shell_quote(selected_backend)}",
            f"export MARAMA_BACKEND_PORT={backend_port}",
            f"export MARAMA_BACKEND_BASE_URL=\"${{MARAMA_BACKEND_BASE_URL:-{backend_base_url}}}\"",
            f"export MARAMA_BACKEND_MODEL=\"${{MARAMA_BACKEND_MODEL:-{backend_model}}}\"",
            f"export MARAMA_BACKEND_API_KEY_ENV={_shell_quote(api_key_env)}",
            f"export MARAMA_VLLM_ARGS=\"${{MARAMA_VLLM_ARGS:-{vllm_args}}}\"",
            f"export MARAMA_BACKEND_COMMAND=\"${{MARAMA_BACKEND_COMMAND:-{backend_command}}}\"",
            "export MARAMA_GATEWAY_CONFIG=\"${MARAMA_GATEWAY_CONFIG:-$PWD/gateway.hpe.json}\"",
            "mkdir -p \"$MARAMA_ROUTE_CACHE\" \"$HF_HOME\"",
            "",
            _hpe_install_command(selected_backend),
            "",
        ],
    )
    if mode == "pull":
        lines.append(f"MaramaRoute pull {model_id} --cache-dir \"$MARAMA_ROUTE_CACHE\"")
    elif mode == "run":
        lines.append(f"MaramaRoute run {model_id} --cache-dir \"$MARAMA_ROUTE_CACHE\" --prompt-text {json.dumps(prompt)}")
    elif selected_backend in {"vllm", "nim", "nemo", "external"}:
        lines.extend(_hpe_live_backend_lines(selected_backend))
    else:
        lines.extend(
            [
                f"MaramaRoute pull {model_id} --cache-dir \"$MARAMA_ROUTE_CACHE\"",
                f"MaramaRoute serve --host 0.0.0.0 --port {port} --live-local --cache-dir \"$MARAMA_ROUTE_CACHE\"",
            ],
        )
    lines.append("")
    return "\n".join(lines)


def render_hpe_gateway_config(
    *,
    model_id: str,
    backend: str = "vllm",
    model_runtime: str = "",
    backend_base_url: str = "http://127.0.0.1:8000/v1",
    backend_model: str = "",
    api_key_env: str = "",
    cache_dir: str = "$MARAMA_ROUTE_CACHE",
) -> dict[str, Any]:
    selected_backend = normalize_hpe_backend(backend, model_runtime=model_runtime)
    if selected_backend == "local-live":
        return {
            "mode": "local_live",
            "prompt_retention": "not_stored_by_default",
            "cache_dir": cache_dir,
            "pull_missing": True,
            "backends": {},
        }
    return {
        "mode": "live",
        "prompt_retention": "not_stored_by_default",
        "default_timeout_seconds": 600,
        "cache_dir": cache_dir,
        "backends": {
            model_id: {
                "type": _hpe_backend_type(selected_backend),
                "base_url": backend_base_url,
                "model": backend_model or model_id,
                "api_key_env": api_key_env,
            },
            "*": {
                "type": _hpe_backend_type(selected_backend),
                "base_url": backend_base_url,
                "model": backend_model or model_id,
                "api_key_env": api_key_env,
            },
        },
    }


def normalize_hpe_backend(backend: str, *, model_runtime: str = "") -> str:
    normalized = (backend or "auto").strip().lower().replace("_", "-")
    runtime = model_runtime.lower()
    aliases = {
        "llama": "local-live",
        "llama-cpp": "local-live",
        "llama.cpp": "local-live",
        "local": "local-live",
        "local_live": "local-live",
        "live-local": "local-live",
        "nvidia-nim": "nim",
        "nvidia_nim": "nim",
        "nem": "nemo",
        "nvidia-nemo": "nemo",
        "nvidia_nemo": "nemo",
        "chat-compatible": "external",
        "proxy": "external",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized == "auto":
        if "llama" in runtime or "gguf" in runtime:
            return "local-live"
        return "vllm"
    if normalized not in {"local-live", "vllm", "nim", "nemo", "external"}:
        raise ValueError(f"Unsupported HPE backend: {backend}")
    return normalized


def render_hpe_apptainer_definition(*, backend: str = "auto") -> str:
    selected_backend = normalize_hpe_backend(backend, model_runtime="")
    packages = "lumynax-marama-route huggingface-hub"
    if selected_backend == "local-live":
        packages += " llama-cpp-python"
    elif selected_backend == "vllm":
        packages += " vllm"
    return "\n".join(
        (
            "Bootstrap: docker",
            "From: python:3.11-slim",
            "",
            "%post",
            "    python -m pip install --upgrade pip",
            f"    python -m pip install -U {packages}",
            "",
            "%environment",
            "    export MARAMA_ROUTE_CACHE=${MARAMA_ROUTE_CACHE:-/workspace/marama-route/models}",
            "    export HF_HOME=${HF_HOME:-/workspace/.cache/huggingface}",
            "",
            "%runscript",
            '    exec MaramaRoute "$@"',
            "",
        ),
    )


def render_hpe_readme(*, model_id: str, port: int = 8787, backend: str = "auto") -> str:
    selected_backend = normalize_hpe_backend(backend, model_runtime="")
    return "\n".join(
        (
            "# MaramaRoute HPE/HPC Workspace",
            "",
            "This folder contains a Slurm job, gateway config, environment file, and optional Apptainer definition for running MaramaRoute on a compute node.",
            "",
            f"Selected backend: `{selected_backend}`.",
            "",
            "MaramaRoute remains the public API on the compute node. The backend can be local-live, vLLM, NVIDIA NIM, NVIDIA NeMo, or any compatible `/v1/chat/completions` service.",
            "",
            "## Files",
            "",
            "- `marama-route.slurm` - starts the selected backend and the MaramaRoute gateway on the compute node.",
            "- `gateway.hpe.json` - MaramaRoute live backend config for `/v1/chat/completions` proxying.",
            "- `marama-route.env` - shared cache and port variables.",
            "- `marama-route.def` - optional Apptainer image definition for clusters that prefer containerized Python runtimes.",
            "",
            "## Typical Flow",
            "",
            "```bash",
            "sbatch marama-route.slurm",
            f"ssh -N -L {port}:127.0.0.1:{port} <user>@<login-node>",
            f"MaramaRoute agent doctor --model {model_id} --base-url http://127.0.0.1:{port}/v1",
            f"curl http://127.0.0.1:{port}/v1/models",
            "```",
            "",
            "For NIM, NeMo, or an existing cluster inference service, set `MARAMA_BACKEND_BASE_URL` or `MARAMA_BACKEND_COMMAND` before `sbatch`.",
            "",
            "## Optional Apptainer Build",
            "",
            "```bash",
            "apptainer build marama-route.sif marama-route.def",
            f"apptainer exec marama-route.sif MaramaRoute pull {model_id} --cache-dir \"$MARAMA_ROUTE_CACHE\"",
            "```",
            "",
        ),
    )


def _hpe_install_command(backend: str) -> str:
    packages = "lumynax-marama-route huggingface-hub"
    if backend == "local-live":
        packages += " llama-cpp-python"
    elif backend == "vllm":
        packages += " vllm"
    return f"python -m pip install -U {packages}"


def _hpe_backend_type(backend: str) -> str:
    return {
        "vllm": "vllm",
        "nim": "nvidia_nim",
        "nemo": "nvidia_nemo",
        "external": "chat_completions_http",
    }.get(backend, "marama_chat_http")


def _hpe_live_backend_lines(backend: str) -> list[str]:
    lines = [
        "cat > \"$MARAMA_GATEWAY_CONFIG\" <<'MARAMA_GATEWAY_JSON'",
        json.dumps(
            {
                "mode": "live",
                "prompt_retention": "not_stored_by_default",
                "default_timeout_seconds": 600,
                "cache_dir": "$MARAMA_ROUTE_CACHE",
                "backends": {
                    "$MARAMA_MODEL_ID": {
                        "type": _hpe_backend_type(backend),
                        "base_url": "$MARAMA_BACKEND_BASE_URL",
                        "model": "$MARAMA_BACKEND_MODEL",
                        "api_key_env": "$MARAMA_BACKEND_API_KEY_ENV",
                    },
                    "*": {
                        "type": _hpe_backend_type(backend),
                        "base_url": "$MARAMA_BACKEND_BASE_URL",
                        "model": "$MARAMA_BACKEND_MODEL",
                        "api_key_env": "$MARAMA_BACKEND_API_KEY_ENV",
                    },
                },
            },
            indent=2,
            sort_keys=True,
        ),
        "MARAMA_GATEWAY_JSON",
        "python - <<'PY'",
        "import json, os, pathlib",
        "path = pathlib.Path(os.environ['MARAMA_GATEWAY_CONFIG'])",
        "text = path.read_text()",
        "for key in sorted(os.environ, key=len, reverse=True):",
        "    if key.startswith('MARAMA_'):",
        "        value = os.environ[key]",
        "        text = text.replace(f'${key}', value)",
        "path.write_text(text)",
        "json.loads(path.read_text())",
        "PY",
        "",
    ]
    if backend == "vllm":
        lines.extend(
            [
                "vllm serve \"$MARAMA_HF_MODEL\" --host 127.0.0.1 --port \"$MARAMA_BACKEND_PORT\" --served-model-name \"$MARAMA_BACKEND_MODEL\" ${MARAMA_VLLM_ARGS:-} &",
                "MARAMA_BACKEND_PID=$!",
            ],
        )
    elif backend in {"nim", "nemo", "external"}:
        lines.extend(
            [
                "if [[ -n \"${MARAMA_BACKEND_COMMAND:-}\" ]]; then",
                "  eval \"$MARAMA_BACKEND_COMMAND\" &",
                "  MARAMA_BACKEND_PID=$!",
                "else",
                "  echo \"Using existing backend at $MARAMA_BACKEND_BASE_URL\"",
                "fi",
            ],
        )
    lines.extend(
        [
            "if [[ \"${MARAMA_SKIP_BACKEND_WAIT:-0}\" != \"1\" ]]; then",
            "python - <<'PY'",
            "import os, time, urllib.request",
            "url = os.environ['MARAMA_BACKEND_BASE_URL'].rstrip('/') + '/models'",
            "deadline = time.time() + int(os.environ.get('MARAMA_BACKEND_WAIT_SECONDS', '600'))",
            "while time.time() < deadline:",
            "    try:",
            "        with urllib.request.urlopen(url, timeout=5) as response:",
            "            if 200 <= response.status < 500:",
            "                print(f'Backend ready: {url}')",
            "                raise SystemExit(0)",
            "    except Exception:",
            "        time.sleep(5)",
            "raise SystemExit(f'Backend did not become ready: {url}')",
            "PY",
            "fi",
            "exec MaramaRoute serve --host \"$MARAMA_ROUTE_HOST\" --port \"$MARAMA_ROUTE_PORT\" --config \"$MARAMA_GATEWAY_CONFIG\"",
        ],
    )
    return lines


def _shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def route_receipt(payload: dict[str, Any], route_result: dict[str, Any]) -> dict[str, Any]:
    selected = route_result.get("route_decision", {}).get("selected_model")
    receipt_payload = {
        "request": payload,
        "selected_model_id": selected.get("model_id") if isinstance(selected, dict) else None,
        "rejected_count": len(route_result.get("route_decision", {}).get("rejected", [])),
    }
    digest = hashlib.sha256(
        json.dumps(receipt_payload, sort_keys=True, default=str).encode("utf-8"),
    ).hexdigest()
    return {
        "receipt_id": f"marama-{digest[:16]}",
        "request_hash": digest,
        "selected_model": receipt_payload["selected_model_id"],
        "prompt_retention": "not_stored_by_default",
        "audit_fields": [
            "request_hash",
            "selected_model",
            "fallback_models",
            "rejected_count",
            "residency",
            "runtime",
        ],
    }


def route_or_chat_payload(payload: dict[str, Any], models: tuple[ModelEndpoint, ...]) -> dict[str, Any]:
    if "messages" in payload:
        result = route_chat_payload(payload, models)
        selected = result["route_decision"]["selected_model"]
        result = {"ok": selected is not None, "mode": "chat_route_dry_run", **result}
    else:
        request = RoutingRequest.from_payload(payload)
        decision = SovereignModelRouter(models).route(request)
        result = {
            "ok": decision.selected_model is not None,
            "mode": "route",
            "routing_request": request.to_dict(),
            "route_decision": decision.to_dict(),
        }
    result["receipt"] = route_receipt(payload, result)
    return result


def build_models_api(models: tuple[ModelEndpoint, ...]) -> dict[str, Any]:
    response = build_models_response(models)
    response["analytics"] = build_registry_analytics(models)
    return response


def model_summary(model: ModelEndpoint) -> dict[str, Any]:
    return {
        "model_id": model.model_id,
        "repo_id": model.repo_id,
        "family": model.family,
        "runtime": model.runtime,
        "modalities": list(model.modalities),
        "context_tokens": model.context_tokens,
        "residency": list(model.residency),
        "license_id": model.license_id,
        "active_params_b": model.active_params_b,
        "total_params_b": model.total_params_b,
        "quality_rank": model.quality_rank,
        "cost_rank": model.cost_rank,
        "sovereignty_tier": model.sovereignty_tier,
        "supports_json": model.supports_json,
        "supports_tools": model.supports_tools,
        "tags": list(model.tags),
        "runtime_compatibility": model_runtime_compatibility(model),
        "operator_score": _operator_score(model),
    }


def scenario_presets() -> list[dict[str, Any]]:
    return [dict(item) for item in DEFAULT_ROUTE_SCENARIOS]


def _next_model_commands(model: ModelEndpoint | None) -> dict[str, str]:
    if model is None:
        return {}
    return {
        "pull": f"MaramaRoute pull {model.model_id}",
        "chat": f"MaramaRoute chat {model.model_id}",
        "run": f"MaramaRoute run {model.model_id} \"Say kia ora\"",
        "inspect": f"MaramaRoute catalog --search {model.model_id} --limit 1",
    }


def _select_export_model(models: tuple[ModelEndpoint, ...], model_id: str) -> ModelEndpoint | None:
    if model_id:
        for model in models:
            if model.model_id == model_id or model.repo_id == model_id:
                return model
        lowered = model_id.lower()
        matches = [model for model in models if lowered in model.model_id.lower() or lowered in model.repo_id.lower()]
        if matches:
            return sorted(matches, key=_catalog_sort_key, reverse=True)[0]
    top = _top_models(models, limit=1)
    return top[0] if top else None


def _top_models(models: tuple[ModelEndpoint, ...], *, limit: int) -> list[ModelEndpoint]:
    return sorted(models, key=_catalog_sort_key, reverse=True)[:limit]


def _catalog_sort_key(model: ModelEndpoint) -> tuple[float, int, str]:
    return (_operator_score(model), model.context_tokens, model.model_id)


def _operator_score(model: ModelEndpoint) -> float:
    score = 0.0
    if "NZ" in model.residency:
        score += 25
    if _is_local_runtime(model.runtime):
        score += 15
    score += model.sovereignty_tier * 10
    score += max(0, 10 - model.quality_rank) * 3
    score -= model.cost_rank
    if model.supports_json:
        score += 5
    if model.supports_tools:
        score += 5
    if model.context_tokens >= 32768:
        score += 6
    elif model.context_tokens >= 8192:
        score += 3
    return round(score, 2)


def _matches_task(model: ModelEndpoint, task_type: str) -> bool:
    tags = set(model.tags)
    if task_type in tags or task_type in model.family.lower() or task_type in model.model_id.lower():
        return True
    if task_type == "code":
        return "coder" in tags or "coder" in model.model_id.lower()
    if task_type == "multimodal":
        return "image" in model.modalities or "multimodal" in tags
    return False


def _is_local_runtime(runtime: str) -> bool:
    value = runtime.lower()
    return value in {"llama_cpp", "gguf", "transformers", "sentence_transformers"} or "local" in value


def _infer_task_type(prompt: str, modalities: set[str]) -> str:
    prompt_lower = prompt.lower()
    if "image" in modalities or "vision" in modalities:
        return "multimodal"
    code_markers = (
        "refactor",
        "diff",
        "unit test",
        "python",
        "typescript",
        "javascript",
        "repository",
        "function",
        "class ",
        "stack trace",
    )
    if any(marker in prompt_lower for marker in code_markers):
        return "code"
    if "reason" in prompt_lower or "prove" in prompt_lower:
        return "reasoning"
    return "general"
