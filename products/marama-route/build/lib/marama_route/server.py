from __future__ import annotations

import json
import os
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

try:  # repo package
    from tinyluminax.products._ui_server import serve_dashboard
except ModuleNotFoundError:  # standalone HF package
    from ._ui_server import serve_dashboard

from .gateway import route_chat_payload
from .platform import build_models_api, route_or_chat_payload, route_receipt
from .registry import load_model_registry
from .ui import (
    PRODUCT_NAME,
    build_dashboard_state,
    build_expanded_dashboard_html,
    default_openai_chat_request_path,
    default_registry_path,
    handle_api_request,
    load_json_mapping,
)

PACKAGE_ROOT = Path(__file__).resolve().parent
PACKAGE_PARENT = PACKAGE_ROOT.parent

DEFAULT_GATEWAY_CONFIG: dict[str, Any] = {
    "mode": "route_only",
    "prompt_retention": "not_stored_by_default",
    "default_timeout_seconds": 120,
    "backends": {},
}


def default_gateway_config_path() -> Path:
    candidates = [
        Path.cwd() / "products" / "lumynax-marama-route" / "configs" / "gateway.local.json",
        Path.cwd() / "configs" / "gateway.local.json",
        PACKAGE_ROOT / "configs" / "gateway.local.json",
        PACKAGE_PARENT / "configs" / "gateway.local.json",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def default_route_request_path() -> Path:
    candidates = [
        Path.cwd() / "products" / "lumynax-marama-route" / "examples" / "request.code-restricted.json",
        Path.cwd() / "examples" / "request.code-restricted.json",
        PACKAGE_ROOT / "examples" / "request.code-restricted.json",
        PACKAGE_PARENT / "examples" / "request.code-restricted.json",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def load_gateway_config(path: Path | None = None) -> dict[str, Any]:
    config = dict(DEFAULT_GATEWAY_CONFIG)
    config["backends"] = dict(DEFAULT_GATEWAY_CONFIG["backends"])
    resolved = path or default_gateway_config_path()
    if resolved.exists():
        payload = json.loads(resolved.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, dict):
            raise ValueError(f"Expected gateway config object in {resolved}")
        config.update(payload)
        config["backends"] = dict(payload.get("backends") or {})
    config["config_path"] = str(resolved)
    return config


def handle_gateway_request(
    method: str,
    path: str,
    payload: dict[str, Any] | None,
    registry_path: Path,
    config_path: Path | None = None,
) -> tuple[int, dict[str, Any]]:
    models = load_model_registry(registry_path)
    config = load_gateway_config(config_path)

    if path.startswith("/api/"):
        return handle_api_request(method, path, payload, registry_path)
    if method == "GET" and path in {"/health", "/v1/health"}:
        return 200, {
            "ok": True,
            "product": PRODUCT_NAME,
            "mode": config["mode"],
            "model_count": len(models),
            "configured_backends": len(config.get("backends") or {}),
            "prompt_retention": config.get("prompt_retention", "not_stored_by_default"),
        }
    if method == "GET" and path == "/v1/models":
        return 200, build_models_api(models)
    if method == "POST" and path == "/v1/route" and payload is not None:
        result = route_or_chat_payload(payload, models)
        return (200 if result["ok"] else 422), result
    if method == "POST" and path == "/v1/chat/completions" and payload is not None:
        return chat_completion_gateway(payload, models, config)
    return 404, {"ok": False, "error": "not_found"}


def chat_completion_gateway(
    payload: dict[str, Any],
    models: tuple[Any, ...],
    config: dict[str, Any],
) -> tuple[int, dict[str, Any]]:
    route_result = route_chat_payload(payload, models)
    decision = route_result["route_decision"]
    selected = decision.get("selected_model")
    if not isinstance(selected, dict):
        return 422, {"ok": False, "error": "no_eligible_model", **route_result}

    receipt = route_receipt(payload, route_result)
    dry_run = bool(
        payload.get("dry_run")
        or payload.get("marama_route_dry_run")
        or config.get("mode", "route_only") == "route_only"
    )
    if dry_run:
        response = dict(route_result["chat_completion_response"])
        response["marama_route"] = dict(response["marama_route"])
        response["marama_route"].update(
            {
                "backend_mode": "route_only",
                "receipt": receipt,
                "prompt_retention": config.get("prompt_retention", "not_stored_by_default"),
            },
        )
        return 200, response

    backend = _backend_for_model(selected["model_id"], config)
    if backend is None:
        return 424, {
            "ok": False,
            "error": "backend_not_configured",
            "message": "Routing succeeded, but no live backend is configured for the selected model.",
            "selected_model": selected["model_id"],
            "required_config": {
                "mode": "live",
                "backends": {
                    selected["model_id"]: {
                        "type": "openai_compatible",
                        "base_url": "http://127.0.0.1:8000/v1",
                        "api_key_env": "OPTIONAL_ENV_NAME",
                    },
                },
            },
            "receipt": receipt,
            **route_result,
        }
    return _proxy_openai_chat_completion(payload, selected, backend, config, route_result, receipt)


def smoke_gateway(
    *,
    registry_path: Path | None = None,
    config_path: Path | None = None,
) -> dict[str, Any]:
    resolved_registry = registry_path or default_registry_path()
    resolved_config = config_path or _temporary_route_only_config()
    route_payload = load_json_mapping(default_route_request_path())
    chat_payload = load_json_mapping(default_openai_chat_request_path())
    chat_payload["dry_run"] = True

    health_status, health = handle_gateway_request("GET", "/health", None, resolved_registry, resolved_config)
    models_status, models = handle_gateway_request("GET", "/v1/models", None, resolved_registry, resolved_config)
    route_status, route = handle_gateway_request("POST", "/v1/route", route_payload, resolved_registry, resolved_config)
    chat_status, chat = handle_gateway_request(
        "POST",
        "/v1/chat/completions",
        chat_payload,
        resolved_registry,
        resolved_config,
    )

    if health_status != 200 or models_status != 200 or route_status != 200 or chat_status != 200:
        raise RuntimeError("MaramaRoute gateway smoke failed")
    if chat.get("object") != "chat.completion" or chat["marama_route"]["selected_model"] is None:
        raise RuntimeError("MaramaRoute gateway did not return a routed chat response")
    return {
        "ok": True,
        "product": PRODUCT_NAME,
        "mode": health["mode"],
        "model_count": health["model_count"],
        "route_selected_model": route["route_decision"]["selected_model"]["model_id"],
        "chat_selected_model": chat["marama_route"]["selected_model"]["model_id"],
        "configured_backends": health["configured_backends"],
    }


def serve_gateway(
    *,
    registry_path: Path | None = None,
    config_path: Path | None = None,
    host: str = "127.0.0.1",
    port: int = 8787,
    open_browser: bool = False,
    smoke: bool = False,
) -> int:
    resolved_registry = registry_path or default_registry_path()
    if smoke:
        print(json.dumps(smoke_gateway(registry_path=resolved_registry, config_path=config_path), indent=2, sort_keys=True))
        return 0

    html = build_expanded_dashboard_html(build_dashboard_state(resolved_registry))
    return serve_dashboard(
        product_name=f"{PRODUCT_NAME} Gateway",
        html=html,
        api_handler=lambda method, path, request_payload: handle_gateway_request(
            method,
            path,
            request_payload,
            resolved_registry,
            config_path,
        ),
        host=host,
        port=port,
        open_browser=open_browser,
        api_path_prefixes=("/api/", "/v1/"),
        api_exact_paths=("/health",),
    )


def _backend_for_model(model_id: str, config: dict[str, Any]) -> dict[str, Any] | None:
    backends = config.get("backends")
    if not isinstance(backends, dict):
        return None
    backend = backends.get(model_id) or backends.get("*")
    return dict(backend) if isinstance(backend, dict) else None


def _proxy_openai_chat_completion(
    payload: dict[str, Any],
    selected: dict[str, Any],
    backend: dict[str, Any],
    config: dict[str, Any],
    route_result: dict[str, Any],
    receipt: dict[str, Any],
) -> tuple[int, dict[str, Any]]:
    if str(backend.get("type") or "openai_compatible") != "openai_compatible":
        return 424, {"ok": False, "error": "unsupported_backend_type", "backend": backend}

    base_url = str(backend.get("base_url") or "").rstrip("/")
    if not base_url:
        return 424, {"ok": False, "error": "backend_base_url_missing", "selected_model": selected["model_id"]}
    endpoint = f"{base_url}/chat/completions"
    upstream_payload = dict(payload)
    upstream_payload["model"] = str(backend.get("model") or selected["model_id"])
    for key in ("route", "routing", "dry_run", "marama_route_dry_run"):
        upstream_payload.pop(key, None)

    headers = {"Content-Type": "application/json"}
    api_key_env = str(backend.get("api_key_env") or "")
    if api_key_env and os.getenv(api_key_env):
        headers["Authorization"] = f"Bearer {os.environ[api_key_env]}"
    headers.update({str(key): str(value) for key, value in dict(backend.get("headers") or {}).items()})

    timeout = float(backend.get("timeout_seconds") or config.get("default_timeout_seconds") or 120)
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(upstream_payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - operator-configured local/remote backend
            body = response.read().decode("utf-8")
            payload_out = json.loads(body)
            if not isinstance(payload_out, dict):
                raise ValueError("upstream response was not a JSON object")
            payload_out["marama_route"] = {
                "dry_run": False,
                "selected_model": selected,
                "fallback_models": route_result["route_decision"]["fallback_models"],
                "rejected_count": len(route_result["route_decision"]["rejected"]),
                "receipt": receipt,
                "backend_base_url": base_url,
                "prompt_retention": config.get("prompt_retention", "not_stored_by_default"),
            }
            return int(response.status), payload_out
    except urllib.error.HTTPError as exc:
        return exc.code, {
            "ok": False,
            "error": "backend_http_error",
            "status": exc.code,
            "body": exc.read().decode("utf-8", errors="replace"),
            "receipt": receipt,
            **route_result,
        }
    except Exception as exc:
        return 502, {
            "ok": False,
            "error": "backend_unavailable",
            "message": str(exc),
            "receipt": receipt,
            **route_result,
        }


def _temporary_route_only_config() -> Path:
    path = Path(tempfile.gettempdir()) / "marama-route-smoke.gateway.json"
    path.write_text(json.dumps(DEFAULT_GATEWAY_CONFIG, indent=2, sort_keys=True), encoding="utf-8")
    return path
