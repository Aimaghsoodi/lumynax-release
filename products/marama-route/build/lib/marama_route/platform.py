from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any

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
    limit = int(filters.get("limit") or 50)
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
        "models": [model_summary(model) for model in ranked[:limit]],
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
                "npm": "@ai-sdk/openai-compatible",
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
        result = {"ok": selected is not None, "mode": "openai_chat_dry_run", **result}
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
        "operator_score": _operator_score(model),
    }


def scenario_presets() -> list[dict[str, Any]]:
    return [dict(item) for item in DEFAULT_ROUTE_SCENARIOS]


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
