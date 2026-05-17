from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .policy import DataCapsule, PolicyDecision, SovereignRequest


@dataclass(frozen=True, slots=True)
class AuditRecord:
    timestamp: str
    capsule_id: str
    actor: str
    purpose: str
    action: str
    model_id: str
    allowed: bool
    reasons: tuple[str, ...]
    obligations: tuple[str, ...]
    audit_tags: tuple[str, ...]
    request_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "capsule_id": self.capsule_id,
            "actor": self.actor,
            "purpose": self.purpose,
            "action": self.action,
            "model_id": self.model_id,
            "allowed": self.allowed,
            "reasons": list(self.reasons),
            "obligations": list(self.obligations),
            "audit_tags": list(self.audit_tags),
            "request_hash": self.request_hash,
        }


def build_audit_record(
    capsule: DataCapsule,
    request: SovereignRequest,
    decision: PolicyDecision,
) -> AuditRecord:
    digest = hashlib.sha256(
        repr((capsule.to_dict(), request.to_dict(), decision.to_dict())).encode("utf-8"),
    ).hexdigest()
    return AuditRecord(
        timestamp=datetime.now(UTC).isoformat(),
        capsule_id=capsule.capsule_id,
        actor=request.actor,
        purpose=request.purpose,
        action=request.action,
        model_id=request.model_id,
        allowed=decision.allowed,
        reasons=decision.reasons,
        obligations=decision.obligations,
        audit_tags=decision.audit_tags,
        request_hash=digest,
    )
