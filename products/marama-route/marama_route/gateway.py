from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from .registry import ModelEndpoint, RoutingRequest
from .router import RouteDecision, SovereignModelRouter


def routing_request_from_chat_payload(payload: dict[str, Any]) -> RoutingRequest:
    """Translate an OpenAI-compatible chat request into a routing request."""

    route_options = _mapping(
        payload.get("route")
        or payload.get("routing")
        or _mapping(payload.get("metadata")).get("marama_route"),
    )
    prompt, modalities = _prompt_and_modalities(payload)
    tools = payload.get("tools")
    response_format = _mapping(payload.get("response_format"))
    task_type = str(route_options.get("task_type") or _infer_task_type(prompt, modalities))

    return RoutingRequest.from_payload(
        {
            "prompt": prompt,
            "task_type": task_type,
            "modalities": sorted(modalities),
            "jurisdiction": route_options.get("jurisdiction", "NZ"),
            "data_sensitivity": route_options.get("data_sensitivity", "internal"),
            "min_context_tokens": route_options.get("min_context_tokens", 4096),
            "requires_local": route_options.get("requires_local", True),
            "requires_tools": bool(tools) or bool(route_options.get("requires_tools")),
            "requires_json": _requires_json(response_format, route_options),
            "license_allowlist": route_options.get("license_allowlist", ()),
            "max_fallbacks": route_options.get("max_fallbacks", 3),
            "metadata": {
                "requested_model": payload.get("model", "auto"),
                "source_protocol": "openai_chat_completions",
            },
        },
    )


def build_models_response(models: tuple[ModelEndpoint, ...]) -> dict[str, Any]:
    """Return an OpenAI-compatible `/v1/models` listing."""

    return {
        "object": "list",
        "data": [
            {
                "id": model.model_id,
                "object": "model",
                "created": 0,
                "owned_by": model.repo_id.split("/", maxsplit=1)[0],
                "metadata": {
                    "repo_id": model.repo_id,
                    "runtime": model.runtime,
                    "modalities": list(model.modalities),
                    "context_tokens": model.context_tokens,
                    "residency": list(model.residency),
                    "sovereignty_tier": model.sovereignty_tier,
                    "supports_tools": model.supports_tools,
                    "supports_json": model.supports_json,
                    "tags": list(model.tags),
                },
            }
            for model in models
        ],
    }


def build_chat_route_response(
    payload: dict[str, Any],
    decision: RouteDecision,
) -> dict[str, Any]:
    """Return a dry-run chat response with route metadata and no generated text."""

    selected = decision.selected_model
    created = int(time.time())
    request_hash = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8"),
    ).hexdigest()
    model_id = selected.model_id if selected is not None else str(payload.get("model", ""))

    return {
        "id": f"marama-route-{request_hash[:16]}",
        "object": "chat.completion",
        "created": created,
        "model": model_id,
        "choices": [
            {
                "index": 0,
                "finish_reason": "route_only",
                "message": {
                    "role": "assistant",
                    "content": "",
                },
            },
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
        "marama_route": {
            "dry_run": True,
            "selected_model": selected.to_dict() if selected is not None else None,
            "fallback_models": [model.to_dict() for model in decision.fallback_models],
            "rejected_count": len(decision.rejected),
            "reasons": list(decision.reasons),
            "scores": dict(decision.scores),
            "request_hash": request_hash,
        },
    }


def route_chat_payload(
    payload: dict[str, Any],
    models: tuple[ModelEndpoint, ...],
) -> dict[str, Any]:
    request = routing_request_from_chat_payload(payload)
    decision = SovereignModelRouter(models).route(request)
    return {
        "routing_request": request.to_dict(),
        "route_decision": decision.to_dict(),
        "chat_completion_response": build_chat_route_response(payload, decision),
    }


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _requires_json(
    response_format: dict[str, Any],
    route_options: dict[str, Any],
) -> bool:
    if bool(route_options.get("requires_json")):
        return True
    response_type = str(response_format.get("type", "")).lower()
    return response_type in {"json_object", "json_schema"}


def _prompt_and_modalities(payload: dict[str, Any]) -> tuple[str, set[str]]:
    modalities = {"text"}
    pieces: list[str] = []
    messages = payload.get("messages")
    if isinstance(messages, list):
        for message in messages:
            if not isinstance(message, dict):
                continue
            content = message.get("content")
            text, content_modalities = _content_text_and_modalities(content)
            pieces.append(text)
            modalities.update(content_modalities)
    elif isinstance(payload.get("prompt"), str):
        pieces.append(str(payload["prompt"]))
    return "\n".join(piece for piece in pieces if piece), modalities


def _content_text_and_modalities(content: object) -> tuple[str, set[str]]:
    if isinstance(content, str):
        return content, {"text"}
    if not isinstance(content, list):
        return "", {"text"}

    pieces: list[str] = []
    modalities = {"text"}
    for part in content:
        if not isinstance(part, dict):
            continue
        part_type = str(part.get("type", "")).lower()
        if part_type in {"text", "input_text"}:
            pieces.append(str(part.get("text", "")))
        elif part_type in {"image", "image_url", "input_image"}:
            modalities.add("image")
        elif part_type in {"audio", "input_audio"}:
            modalities.add("audio")
    return "\n".join(piece for piece in pieces if piece), modalities


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
