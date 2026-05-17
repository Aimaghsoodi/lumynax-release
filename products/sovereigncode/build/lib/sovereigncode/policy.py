from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

HIGH_IMPACT_SENSITIVITY = frozenset({"personal", "restricted", "health", "iwi", "taonga"})
DESTRUCTIVE_ACTIONS = frozenset({"delete_file", "execute_shell", "network_export", "publish", "commit"})
PERSONAL_DETAIL_LEVELS = {
    "none": 0,
    "anonymous": 1,
    "pseudonymous": 2,
    "identifiable": 3,
    "sensitive_identifiable": 4,
}


def _tuple_of_text(value: object, *, default: tuple[str, ...] = ()) -> tuple[str, ...]:
    if value in (None, ""):
        return default
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (list, tuple, set)):
        return tuple(str(item).strip() for item in value if str(item).strip())
    return (str(value).strip(),)


def _normal(value: str) -> str:
    return value.strip().lower().replace(" ", "_").replace("-", "_")


def _personal_detail_rank(value: str) -> int:
    return PERSONAL_DETAIL_LEVELS.get(_normal(value), 0)


@dataclass(frozen=True, slots=True)
class DataCapsule:
    """Policy wrapper for a governed data subject, dataset, or workspace."""

    capsule_id: str
    subject_id: str
    jurisdiction: str = "NZ"
    sensitivity: str = "internal"
    allowed_purposes: tuple[str, ...] = ("inference", "coding_assistance")
    denied_purposes: tuple[str, ...] = ()
    resident_regions: tuple[str, ...] = ("NZ",)
    data_classes: tuple[str, ...] = ("source_code",)
    retention_days: int = 30
    export_allowed: bool = False
    training_allowed: bool = False
    personal_detail_level: str = "none"
    consent_scopes: tuple[str, ...] = ()
    data_subject_rights: tuple[str, ...] = (
        "access",
        "correction",
        "deletion_request",
        "processing_objection",
    )
    revoked: bool = False
    schema_context: str = "https://schema.org"
    consent_record: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> DataCapsule:
        return cls(
            capsule_id=str(payload.get("capsule_id") or payload.get("id") or ""),
            subject_id=str(payload.get("subject_id") or payload.get("subject") or ""),
            jurisdiction=str(payload.get("jurisdiction") or "NZ"),
            sensitivity=_normal(str(payload.get("sensitivity") or "internal")),
            allowed_purposes=tuple(_normal(item) for item in _tuple_of_text(payload.get("allowed_purposes"), default=("inference",))),
            denied_purposes=tuple(_normal(item) for item in _tuple_of_text(payload.get("denied_purposes"))),
            resident_regions=tuple(str(item).upper() for item in _tuple_of_text(payload.get("resident_regions"), default=("NZ",))),
            data_classes=tuple(_normal(item) for item in _tuple_of_text(payload.get("data_classes"), default=("source_code",))),
            retention_days=int(payload.get("retention_days") or 30),
            export_allowed=bool(payload.get("export_allowed", False)),
            training_allowed=bool(payload.get("training_allowed", False)),
            personal_detail_level=_normal(
                str(payload.get("personal_detail_level") or "none"),
            ),
            consent_scopes=tuple(
                _normal(item) for item in _tuple_of_text(payload.get("consent_scopes"))
            ),
            data_subject_rights=tuple(
                _normal(item)
                for item in _tuple_of_text(
                    payload.get("data_subject_rights"),
                    default=(
                        "access",
                        "correction",
                        "deletion_request",
                        "processing_objection",
                    ),
                )
            ),
            revoked=bool(payload.get("revoked", False)),
            schema_context=str(payload.get("schema_context") or "https://schema.org"),
            consent_record=str(payload.get("consent_record") or ""),
            metadata=dict(payload.get("metadata") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "capsule_id": self.capsule_id,
            "subject_id": self.subject_id,
            "jurisdiction": self.jurisdiction,
            "sensitivity": self.sensitivity,
            "allowed_purposes": list(self.allowed_purposes),
            "denied_purposes": list(self.denied_purposes),
            "resident_regions": list(self.resident_regions),
            "data_classes": list(self.data_classes),
            "retention_days": self.retention_days,
            "export_allowed": self.export_allowed,
            "training_allowed": self.training_allowed,
            "personal_detail_level": self.personal_detail_level,
            "consent_scopes": list(self.consent_scopes),
            "data_subject_rights": list(self.data_subject_rights),
            "revoked": self.revoked,
            "schema_context": self.schema_context,
            "consent_record": self.consent_record,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class SovereignRequest:
    actor: str
    purpose: str
    action: str
    region: str = "NZ"
    model_id: str = "local/lumynax"
    data_classes: tuple[str, ...] = ("source_code",)
    tool_name: str = ""
    writes_files: bool = False
    exports_data: bool = False
    trains_model: bool = False
    human_approved: bool = False
    personal_detail_level: str = "none"
    consent_scope: str = ""
    requested_retention_days: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> SovereignRequest:
        return cls(
            actor=str(payload.get("actor") or "unknown"),
            purpose=_normal(str(payload.get("purpose") or "inference")),
            action=_normal(str(payload.get("action") or "read_context")),
            region=str(payload.get("region") or "NZ").upper(),
            model_id=str(payload.get("model_id") or "local/lumynax"),
            data_classes=tuple(_normal(item) for item in _tuple_of_text(payload.get("data_classes"), default=("source_code",))),
            tool_name=str(payload.get("tool_name") or ""),
            writes_files=bool(payload.get("writes_files", False)),
            exports_data=bool(payload.get("exports_data", False)),
            trains_model=bool(payload.get("trains_model", False)),
            human_approved=bool(payload.get("human_approved", False)),
            personal_detail_level=_normal(
                str(payload.get("personal_detail_level") or "none"),
            ),
            consent_scope=_normal(str(payload.get("consent_scope") or "")),
            requested_retention_days=(
                int(payload["requested_retention_days"])
                if payload.get("requested_retention_days") is not None
                else None
            ),
            metadata=dict(payload.get("metadata") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "actor": self.actor,
            "purpose": self.purpose,
            "action": self.action,
            "region": self.region,
            "model_id": self.model_id,
            "data_classes": list(self.data_classes),
            "tool_name": self.tool_name,
            "writes_files": self.writes_files,
            "exports_data": self.exports_data,
            "trains_model": self.trains_model,
            "human_approved": self.human_approved,
            "personal_detail_level": self.personal_detail_level,
            "consent_scope": self.consent_scope,
            "requested_retention_days": self.requested_retention_days,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    allowed: bool
    reasons: tuple[str, ...]
    obligations: tuple[str, ...]
    audit_tags: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reasons": list(self.reasons),
            "obligations": list(self.obligations),
            "audit_tags": list(self.audit_tags),
        }


class SovereigntyPolicyEngine:
    """Deterministic policy decision point for AbteeX SovereignCode."""

    def evaluate(self, capsule: DataCapsule, request: SovereignRequest) -> PolicyDecision:
        reasons: list[str] = []
        obligations: list[str] = [
            "write_immutable_audit_record",
            f"retain_trace_no_more_than_{capsule.retention_days}_days",
            "preserve_capsule_id_in_agent_trace",
        ]
        audit_tags: list[str] = [
            f"jurisdiction:{capsule.jurisdiction.upper()}",
            f"sensitivity:{capsule.sensitivity}",
            f"purpose:{request.purpose}",
        ]

        if capsule.revoked:
            reasons.append("capsule consent has been revoked")
        if request.purpose in capsule.denied_purposes:
            reasons.append(f"purpose `{request.purpose}` is explicitly denied")
        if request.purpose not in capsule.allowed_purposes:
            reasons.append(f"purpose `{request.purpose}` is not in allowed_purposes")
        if request.region.upper() not in capsule.resident_regions:
            reasons.append(f"request region `{request.region}` is outside resident_regions")
        if request.trains_model and not capsule.training_allowed:
            reasons.append("model training is not allowed for this capsule")
        if request.exports_data and not capsule.export_allowed:
            reasons.append("data export is not allowed for this capsule")
        if request.requested_retention_days and request.requested_retention_days > capsule.retention_days:
            reasons.append("requested retention exceeds capsule retention_days")
        if not set(request.data_classes).issubset(set(capsule.data_classes)):
            reasons.append("request data_classes exceed capsule data_classes")
        if _personal_detail_rank(request.personal_detail_level) > _personal_detail_rank(
            capsule.personal_detail_level,
        ):
            reasons.append("requested personal_detail_level exceeds capsule consent")
        if (
            request.consent_scope
            and capsule.consent_scopes
            and request.consent_scope not in capsule.consent_scopes
        ):
            reasons.append("request consent_scope is not covered by the capsule")

        model_is_lumynax_or_local = any(
            marker in request.model_id.lower()
            for marker in ("lumynax", "local", "llama.cpp", "gguf")
        )
        if capsule.sensitivity in HIGH_IMPACT_SENSITIVITY and not model_is_lumynax_or_local:
            reasons.append("high-impact data requires a local or LumynaX-governed model")

        if request.action in DESTRUCTIVE_ACTIONS and not request.human_approved:
            reasons.append(f"action `{request.action}` requires human approval")

        if request.writes_files:
            obligations.append("show_diff_before_write_or_commit")
        if request.exports_data:
            obligations.append("attach_export_manifest_and_recipient")
        if request.trains_model:
            obligations.append("attach_training_consent_record")
        if capsule.sensitivity in HIGH_IMPACT_SENSITIVITY:
            obligations.extend(
                (
                    "redact_unneeded_personal_data",
                    "route_only_to_resident_runtime",
                    "require_human_review_for_external_effects",
                ),
            )
        if "personal" in capsule.data_classes or capsule.sensitivity == "personal":
            obligations.extend(
                (
                    "honour_data_subject_access_and_correction",
                    "minimise_personal_detail_in_prompt",
                    "keep_personal_trace_inside_capsule_retention",
                ),
            )

        allowed = not reasons
        if not allowed:
            audit_tags.append("decision:deny")
        else:
            audit_tags.append("decision:allow")
        return PolicyDecision(
            allowed=allowed,
            reasons=tuple(reasons),
            obligations=tuple(dict.fromkeys(obligations)),
            audit_tags=tuple(dict.fromkeys(audit_tags)),
        )
