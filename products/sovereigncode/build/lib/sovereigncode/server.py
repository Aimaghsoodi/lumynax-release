from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

try:  # repo package
    from tinyluminax.products._ui_server import serve_dashboard
except ModuleNotFoundError:  # standalone HF package
    from ._ui_server import serve_dashboard

try:  # repo package
    from tinyluminax.products.marama_route import RoutingRequest, load_model_registry
except ModuleNotFoundError:  # standalone HF package
    from marama_route import RoutingRequest, load_model_registry

from .audit import build_audit_record
from .ledger import AuditLedger, default_ledger_path
from .planner import plan_coding_turn
from .platform import (
    build_capsule_summary,
    build_policy_matrix,
    build_turn_brief,
    check_tool_request,
)
from .policy import DataCapsule, SovereignRequest, SovereigntyPolicyEngine
from .ui import (
    PRODUCT_NAME,
    build_dashboard_html,
    build_dashboard_state,
    default_capsule_path,
    default_registry_path,
    default_request_path,
    default_route_request_path,
    handle_api_request,
)


def handle_service_request(
    method: str,
    path: str,
    payload: dict[str, Any] | None,
    *,
    capsule_path: Path,
    request_path: Path,
    route_request_path: Path,
    registry_path: Path,
    ledger_path: Path,
    state: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    ledger = AuditLedger(ledger_path)
    service_state = state or build_dashboard_state(capsule_path, request_path, route_request_path, registry_path)

    if path.startswith("/api/"):
        return handle_api_request(method, path, payload, registry_path, service_state)
    if method == "GET" and path in {"/health", "/v1/health"}:
        return 200, _health_payload(ledger, service_state)
    if method == "GET" and path == "/v1/audit":
        return 200, {"ok": True, "ledger_path": str(ledger.path), "records": ledger.tail()}
    if method == "GET" and path == "/v1/capsule-summary":
        return 200, {"ok": True, "summary": build_capsule_summary(service_state["capsule"])}
    if method == "POST" and path == "/v1/evaluate":
        result = evaluate_payload(payload or {}, service_state, ledger)
        return (200 if result["decision"]["allowed"] else 422), result
    if method == "POST" and path == "/v1/plan-turn":
        result = plan_turn_payload(payload or {}, service_state, ledger)
        return (200 if result["allowed"] else 422), result
    if method == "POST" and path == "/v1/tool-check":
        result = tool_check_payload(payload or {}, service_state, ledger)
        return (200 if result["ok"] else 422), result
    if method == "POST" and path == "/v1/policy-matrix":
        return 200, policy_matrix_payload(payload or {}, service_state, ledger)
    if method == "POST" and path == "/v1/capsule-summary":
        capsule_payload = _mapping(payload, "capsule") or service_state["capsule"]
        return 200, {"ok": True, "summary": build_capsule_summary(capsule_payload)}
    return 404, {"ok": False, "error": "not_found"}


def evaluate_payload(
    payload: dict[str, Any],
    state: dict[str, Any],
    ledger: AuditLedger,
) -> dict[str, Any]:
    capsule = DataCapsule.from_payload(_mapping(payload, "capsule") or state["capsule"])
    request = SovereignRequest.from_payload(_mapping(payload, "request") or state["request"])
    decision = SovereigntyPolicyEngine().evaluate(capsule, request)
    audit = build_audit_record(capsule, request, decision).to_dict()
    ledger_record = ledger.append(
        "policy_evaluate",
        {
            "capsule_id": capsule.capsule_id,
            "request": request.to_dict(),
            "decision": decision.to_dict(),
            "audit_record": audit,
        },
    )
    return {
        "ok": decision.allowed,
        "decision": decision.to_dict(),
        "audit_record": audit,
        "ledger_record": ledger_record,
    }


def plan_turn_payload(
    payload: dict[str, Any],
    state: dict[str, Any],
    ledger: AuditLedger,
) -> dict[str, Any]:
    capsule = DataCapsule.from_payload(_mapping(payload, "capsule") or state["capsule"])
    request = SovereignRequest.from_payload(_mapping(payload, "request") or state["request"])
    route_request = RoutingRequest.from_payload(_mapping(payload, "route_request") or state["route_request"])
    models = load_model_registry(Path(str(payload.get("registry_path") or state["registry_path"])))
    plan = plan_coding_turn(capsule, request, route_request, models)
    result = plan.to_dict()
    result["turn_brief"] = build_turn_brief(result)
    result["ledger_record"] = ledger.append(
        "plan_turn",
        {
            "capsule_id": capsule.capsule_id,
            "allowed": plan.allowed,
            "policy_decision": result["policy_decision"],
            "route_decision": result["route_decision"],
            "audit_record": result["audit_record"],
            "turn_brief": result["turn_brief"],
        },
    )
    result["ok"] = plan.allowed
    return result


def tool_check_payload(
    payload: dict[str, Any],
    state: dict[str, Any],
    ledger: AuditLedger,
) -> dict[str, Any]:
    tool_payload = _mapping(payload, "tool") or {
        "tool_name": payload.get("tool_name", "workspace_reader"),
        "action": payload.get("action", "read_context"),
        "writes_files": bool(payload.get("writes_files", False)),
        "exports_data": bool(payload.get("exports_data", False)),
        "trains_model": bool(payload.get("trains_model", False)),
        "human_approved": bool(payload.get("human_approved", False)),
    }
    result = check_tool_request(
        _mapping(payload, "capsule") or state["capsule"],
        _mapping(payload, "request") or state["request"],
        tool_payload,
    )
    result["ledger_record"] = ledger.append(
        "tool_check",
        {
            "tool": tool_payload,
            "decision": result["decision"],
            "audit_record": result["audit_record"],
            "operator_gate": result["operator_gate"],
        },
    )
    return result


def policy_matrix_payload(
    payload: dict[str, Any],
    state: dict[str, Any],
    ledger: AuditLedger,
) -> dict[str, Any]:
    scenarios = payload.get("scenarios") if isinstance(payload.get("scenarios"), list) else None
    result = build_policy_matrix(
        _mapping(payload, "capsule") or state["capsule"],
        _mapping(payload, "request") or state["request"],
        scenarios,
    )
    result["ledger_record"] = ledger.append(
        "policy_matrix",
        {
            "capsule_id": result["capsule_id"],
            "allowed_count": result["allowed_count"],
            "blocked_count": result["blocked_count"],
        },
    )
    return result


def smoke_service(
    *,
    capsule_path: Path | None = None,
    request_path: Path | None = None,
    route_request_path: Path | None = None,
    registry_path: Path | None = None,
    ledger_path: Path | None = None,
) -> dict[str, Any]:
    resolved_capsule = capsule_path or default_capsule_path()
    resolved_request = request_path or default_request_path()
    resolved_route_request = route_request_path or default_route_request_path()
    resolved_registry = registry_path or default_registry_path()
    resolved_ledger = ledger_path or _temporary_ledger_path()
    state = build_dashboard_state(resolved_capsule, resolved_request, resolved_route_request, resolved_registry)

    health_status, health = handle_service_request(
        "GET",
        "/health",
        None,
        capsule_path=resolved_capsule,
        request_path=resolved_request,
        route_request_path=resolved_route_request,
        registry_path=resolved_registry,
        ledger_path=resolved_ledger,
        state=state,
    )
    evaluate_status, evaluate = handle_service_request(
        "POST",
        "/v1/evaluate",
        {},
        capsule_path=resolved_capsule,
        request_path=resolved_request,
        route_request_path=resolved_route_request,
        registry_path=resolved_registry,
        ledger_path=resolved_ledger,
        state=state,
    )
    plan_status, plan = handle_service_request(
        "POST",
        "/v1/plan-turn",
        {},
        capsule_path=resolved_capsule,
        request_path=resolved_request,
        route_request_path=resolved_route_request,
        registry_path=resolved_registry,
        ledger_path=resolved_ledger,
        state=state,
    )
    tool_status, tool = handle_service_request(
        "POST",
        "/v1/tool-check",
        {"tool_name": "workspace_reader", "action": "read_context"},
        capsule_path=resolved_capsule,
        request_path=resolved_request,
        route_request_path=resolved_route_request,
        registry_path=resolved_registry,
        ledger_path=resolved_ledger,
        state=state,
    )
    audit_status, audit = handle_service_request(
        "GET",
        "/v1/audit",
        None,
        capsule_path=resolved_capsule,
        request_path=resolved_request,
        route_request_path=resolved_route_request,
        registry_path=resolved_registry,
        ledger_path=resolved_ledger,
        state=state,
    )

    if (health_status, evaluate_status, plan_status, tool_status, audit_status) != (200, 200, 200, 200, 200):
        raise RuntimeError("SovereignCode service smoke failed")
    if not evaluate["decision"]["allowed"] or not plan["allowed"] or not tool["ok"]:
        raise RuntimeError("SovereignCode service smoke did not allow the governed local request")
    return {
        "ok": True,
        "product": PRODUCT_NAME,
        "capsule_id": state["capsule"]["capsule_id"],
        "selected_model": plan["turn_brief"]["selected_model"],
        "ledger_path": str(resolved_ledger),
        "ledger_records": len(audit["records"]),
        "tool_next_gate": tool["operator_gate"]["next_gate"],
    }


def serve_service(
    *,
    capsule_path: Path | None = None,
    request_path: Path | None = None,
    route_request_path: Path | None = None,
    registry_path: Path | None = None,
    ledger_path: Path | None = None,
    host: str = "127.0.0.1",
    port: int = 8788,
    open_browser: bool = False,
    smoke: bool = False,
) -> int:
    resolved_capsule = capsule_path or default_capsule_path()
    resolved_request = request_path or default_request_path()
    resolved_route_request = route_request_path or default_route_request_path()
    resolved_registry = registry_path or default_registry_path()
    resolved_ledger = ledger_path or default_ledger_path()
    if smoke:
        print(
            json.dumps(
                smoke_service(
                    capsule_path=resolved_capsule,
                    request_path=resolved_request,
                    route_request_path=resolved_route_request,
                    registry_path=resolved_registry,
                    ledger_path=ledger_path,
                ),
                indent=2,
                sort_keys=True,
            ),
        )
        return 0

    state = build_dashboard_state(resolved_capsule, resolved_request, resolved_route_request, resolved_registry)
    html = build_dashboard_html(state)
    return serve_dashboard(
        product_name=f"{PRODUCT_NAME} Service",
        html=html,
        api_handler=lambda method, path, request_payload: handle_service_request(
            method,
            path,
            request_payload,
            capsule_path=resolved_capsule,
            request_path=resolved_request,
            route_request_path=resolved_route_request,
            registry_path=resolved_registry,
            ledger_path=resolved_ledger,
            state=state,
        ),
        host=host,
        port=port,
        open_browser=open_browser,
        api_path_prefixes=("/api/", "/v1/"),
        api_exact_paths=("/health",),
    )


def _health_payload(ledger: AuditLedger, state: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "product": PRODUCT_NAME,
        "capsule_id": state["capsule"]["capsule_id"],
        "ledger_path": str(ledger.path),
        "ledger_records": len(ledger.tail()),
        "service": "policy_api_audit_ledger",
    }


def _mapping(payload: dict[str, Any] | None, key: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    value = payload.get(key)
    return dict(value) if isinstance(value, dict) else {}


def _temporary_ledger_path() -> Path:
    handle, raw_path = tempfile.mkstemp(prefix="sovereigncode-smoke-", suffix=".audit.jsonl")
    os.close(handle)
    path = Path(raw_path)
    path.unlink(missing_ok=True)
    return path
