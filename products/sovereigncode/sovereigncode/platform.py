from __future__ import annotations

from typing import Any

from .audit import build_audit_record
from .policy import DataCapsule, SovereignRequest, SovereigntyPolicyEngine

TOOL_SCENARIOS: tuple[dict[str, Any], ...] = (
    {
        "name": "Read workspace",
        "action": "read_context",
        "tool_name": "workspace_reader",
        "writes_files": False,
        "exports_data": False,
        "trains_model": False,
        "human_approved": False,
    },
    {
        "name": "Write file",
        "action": "write_file",
        "tool_name": "file_editor",
        "writes_files": True,
        "exports_data": False,
        "trains_model": False,
        "human_approved": False,
    },
    {
        "name": "Approved shell",
        "action": "execute_shell",
        "tool_name": "test_runner",
        "writes_files": False,
        "exports_data": False,
        "trains_model": False,
        "human_approved": True,
    },
    {
        "name": "Network export",
        "action": "network_export",
        "tool_name": "external_api",
        "writes_files": False,
        "exports_data": True,
        "trains_model": False,
        "human_approved": True,
    },
    {
        "name": "Model training",
        "action": "train_model",
        "tool_name": "trainer",
        "writes_files": False,
        "exports_data": False,
        "trains_model": True,
        "human_approved": True,
    },
    {
        "name": "Publish commit",
        "action": "commit",
        "tool_name": "git",
        "writes_files": False,
        "exports_data": True,
        "trains_model": False,
        "human_approved": True,
    },
)


def build_policy_matrix(
    capsule_payload: dict[str, Any],
    request_payload: dict[str, Any],
    scenarios: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    capsule = DataCapsule.from_payload(capsule_payload)
    engine = SovereigntyPolicyEngine()
    rows = []
    for scenario in scenarios or [dict(item) for item in TOOL_SCENARIOS]:
        merged = dict(request_payload)
        merged.update({key: value for key, value in scenario.items() if key != "name"})
        request = SovereignRequest.from_payload(merged)
        decision = engine.evaluate(capsule, request)
        audit = build_audit_record(capsule, request, decision)
        rows.append(
            {
                "name": scenario.get("name", request.action),
                "allowed": decision.allowed,
                "action": request.action,
                "tool_name": request.tool_name,
                "writes_files": request.writes_files,
                "exports_data": request.exports_data,
                "trains_model": request.trains_model,
                "human_approved": request.human_approved,
                "reason_count": len(decision.reasons),
                "obligation_count": len(decision.obligations),
                "reasons": list(decision.reasons),
                "obligations": list(decision.obligations),
                "audit_hash": audit.request_hash,
            },
        )
    return {
        "ok": True,
        "capsule_id": capsule.capsule_id,
        "rows": rows,
        "allowed_count": sum(1 for row in rows if row["allowed"]),
        "blocked_count": sum(1 for row in rows if not row["allowed"]),
    }


def check_tool_request(
    capsule_payload: dict[str, Any],
    request_payload: dict[str, Any],
    tool_payload: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(request_payload)
    merged.update(tool_payload)
    capsule = DataCapsule.from_payload(capsule_payload)
    request = SovereignRequest.from_payload(merged)
    decision = SovereigntyPolicyEngine().evaluate(capsule, request)
    audit = build_audit_record(capsule, request, decision)
    return {
        "ok": decision.allowed,
        "tool_name": request.tool_name,
        "action": request.action,
        "decision": decision.to_dict(),
        "audit_record": audit.to_dict(),
        "operator_gate": build_operator_gate(decision.to_dict(), request.to_dict()),
    }


def build_operator_gate(decision: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    destructive = bool(
        request.get("writes_files")
        or request.get("exports_data")
        or request.get("trains_model")
        or request.get("action") in {"execute_shell", "publish", "commit", "network_export"}
    )
    return {
        "requires_human_review": destructive or not decision.get("allowed", False),
        "requires_visible_diff": bool(request.get("writes_files")),
        "requires_export_manifest": bool(request.get("exports_data")),
        "requires_training_consent": bool(request.get("trains_model")),
        "next_gate": _next_gate(decision, request),
    }


def build_turn_brief(plan: dict[str, Any]) -> dict[str, Any]:
    route = plan.get("route_decision") or {}
    selected = route.get("selected_model") or {}
    grants = plan.get("tool_grants") or []
    blocked_grants = [grant for grant in grants if not grant.get("allowed")]
    return {
        "allowed": bool(plan.get("allowed")),
        "selected_model": selected.get("model_id"),
        "runtime": selected.get("runtime"),
        "tool_grants": len(grants),
        "blocked_tool_grants": len(blocked_grants),
        "obligation_count": len(plan.get("obligations") or []),
        "blocked_reasons": plan.get("blocked_reasons") or [],
        "operator_checklist": build_operator_checklist(plan),
    }


def build_operator_checklist(plan: dict[str, Any]) -> list[dict[str, Any]]:
    allowed = bool(plan.get("allowed"))
    obligations = set(plan.get("obligations") or [])
    route = plan.get("route_decision") or {}
    selected = route.get("selected_model")
    return [
        {
            "item": "policy_decision",
            "status": "pass" if allowed else "blocked",
            "detail": "Data Capsule policy permits the request" if allowed else "Policy blocked the request",
        },
        {
            "item": "model_route",
            "status": "pass" if selected else "blocked",
            "detail": selected.get("model_id") if isinstance(selected, dict) else "No eligible model",
        },
        {
            "item": "audit_record",
            "status": "required",
            "detail": "Immutable audit record must be persisted before external effects",
        },
        {
            "item": "visible_diff",
            "status": "required" if "show_diff_before_write_or_commit" in obligations else "not_required",
            "detail": "Show file diff before writes or commits",
        },
        {
            "item": "resident_runtime",
            "status": "required" if "route_only_to_resident_runtime" in obligations else "not_required",
            "detail": "Route high-impact data only to approved resident runtime",
        },
    ]


def build_opencode_workspace_config(
    *,
    base_url: str = "http://127.0.0.1:8787/v1",
    provider_id: str = "abteex-marama",
    model: str = "lumynax-infused-qwen3-coder-30b-a3b-gguf",
) -> dict[str, Any]:
    return {
        "$schema": "https://opencode.ai/config.json",
        "provider": {
            provider_id: {
                "name": "AbteeX SovereignCode via MaramaRoute",
                "npm": "@ai-sdk/openai-compatible",
                "options": {
                    "baseURL": base_url,
                    "apiKey": "${ABTEEX_MARAMA_API_KEY:-local-dev}",
                },
                "models": {
                    model: {
                        "name": model,
                        "attachment": False,
                        "reasoning": True,
                    },
                },
            },
        },
        "model": f"{provider_id}/{model}",
        "sovereigncode": {
            "capsule_file": "products/abx-sovereigncode/examples/capsule.restricted-nz-code.json",
            "audit_ledger": ".sovereigncode/audit.jsonl",
            "require_human_review_for": ["write_files", "execute_shell", "network_export", "commit"],
        },
    }


def build_capsule_summary(capsule_payload: dict[str, Any]) -> dict[str, Any]:
    capsule = DataCapsule.from_payload(capsule_payload)
    return {
        "capsule_id": capsule.capsule_id,
        "jurisdiction": capsule.jurisdiction,
        "sensitivity": capsule.sensitivity,
        "resident_regions": list(capsule.resident_regions),
        "allowed_purposes": list(capsule.allowed_purposes),
        "denied_purposes": list(capsule.denied_purposes),
        "retention_days": capsule.retention_days,
        "export_allowed": capsule.export_allowed,
        "training_allowed": capsule.training_allowed,
        "personal_detail_level": capsule.personal_detail_level,
        "risk_flags": _capsule_risk_flags(capsule),
    }


def tool_scenarios() -> list[dict[str, Any]]:
    return [dict(item) for item in TOOL_SCENARIOS]


def _capsule_risk_flags(capsule: DataCapsule) -> list[str]:
    flags = []
    if capsule.sensitivity in {"personal", "restricted", "health", "iwi", "taonga"}:
        flags.append("high_impact_sensitivity")
    if not capsule.export_allowed:
        flags.append("export_blocked")
    if not capsule.training_allowed:
        flags.append("training_blocked")
    if capsule.retention_days <= 14:
        flags.append("short_retention")
    if capsule.personal_detail_level not in {"none", "anonymous"}:
        flags.append("personal_detail_controls")
    return flags


def _next_gate(decision: dict[str, Any], request: dict[str, Any]) -> str:
    if not decision.get("allowed", False):
        return "revise_request_or_capsule"
    if request.get("writes_files"):
        return "show_diff_before_write"
    if request.get("exports_data"):
        return "attach_export_manifest"
    if request.get("trains_model"):
        return "attach_training_consent"
    if request.get("action") in {"execute_shell", "commit"}:
        return "human_approval"
    return "execute_with_audit"
