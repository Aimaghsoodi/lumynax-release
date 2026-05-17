from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from marama_route import (
    ModelEndpoint,
    RouteDecision,
    RoutingRequest,
    SovereignModelRouter,
)

from .audit import AuditRecord, build_audit_record
from .policy import (
    DataCapsule,
    PolicyDecision,
    SovereignRequest,
    SovereigntyPolicyEngine,
)


@dataclass(frozen=True, slots=True)
class ToolGrant:
    tool: str
    allowed: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool": self.tool,
            "allowed": self.allowed,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class SovereignCodingTurnPlan:
    allowed: bool
    policy_decision: PolicyDecision
    audit_record: AuditRecord
    route_decision: RouteDecision | None
    tool_grants: tuple[ToolGrant, ...]
    obligations: tuple[str, ...]
    blocked_reasons: tuple[str, ...]
    integration_targets: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "policy_decision": self.policy_decision.to_dict(),
            "audit_record": self.audit_record.to_dict(),
            "route_decision": (
                self.route_decision.to_dict() if self.route_decision is not None else None
            ),
            "tool_grants": [grant.to_dict() for grant in self.tool_grants],
            "obligations": list(self.obligations),
            "blocked_reasons": list(self.blocked_reasons),
            "integration_targets": list(self.integration_targets),
        }


def plan_coding_turn(
    capsule: DataCapsule,
    request: SovereignRequest,
    routing_request: RoutingRequest,
    models: tuple[ModelEndpoint, ...],
) -> SovereignCodingTurnPlan:
    """Plan one governed coding-agent turn against policy and model routing."""

    policy_decision = SovereigntyPolicyEngine().evaluate(capsule, request)
    audit_record = build_audit_record(capsule, request, policy_decision)
    route_decision: RouteDecision | None = None
    blocked_reasons = list(policy_decision.reasons)

    if policy_decision.allowed:
        route_decision = SovereignModelRouter(models).route(routing_request)
        if route_decision.selected_model is None:
            blocked_reasons.extend(route_decision.reasons)

    tool_grants = _build_tool_grants(request, policy_decision)
    allowed = policy_decision.allowed and route_decision is not None
    allowed = allowed and route_decision.selected_model is not None

    return SovereignCodingTurnPlan(
        allowed=allowed,
        policy_decision=policy_decision,
        audit_record=audit_record,
        route_decision=route_decision,
        tool_grants=tool_grants,
        obligations=policy_decision.obligations,
        blocked_reasons=tuple(dict.fromkeys(blocked_reasons)),
        integration_targets=(
            "opencode_openai_compatible_provider",
            "openrouter_style_gateway",
            "local_cli_agent",
        ),
    )


def _build_tool_grants(
    request: SovereignRequest,
    decision: PolicyDecision,
) -> tuple[ToolGrant, ...]:
    if not decision.allowed:
        return (
            ToolGrant("read_workspace", False, "blocked by policy decision"),
            ToolGrant("write_files", False, "blocked by policy decision"),
            ToolGrant("execute_shell", False, "blocked by policy decision"),
            ToolGrant("network_export", False, "blocked by policy decision"),
        )

    return (
        ToolGrant("read_workspace", True, "policy allows governed context read"),
        ToolGrant(
            "write_files",
            request.writes_files,
            "allowed only with visible diff and audit obligation",
        ),
        ToolGrant(
            "execute_shell",
            request.action == "execute_shell" and request.human_approved,
            "requires explicit human approval",
        ),
        ToolGrant(
            "network_export",
            request.exports_data and request.human_approved,
            "requires export permission, manifest, and approval",
        ),
    )
