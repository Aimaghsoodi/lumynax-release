"""Audit ledger primitives.

Every policy decision creates a record. Records are hash-stable, append-only,
and chainable for tamper-evident exports.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def request_hash(request: Dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(request).encode("utf-8")).hexdigest()


@dataclass
class AuditRecord:
    capsule_id: str
    actor: str
    purpose: str
    action: str
    model_id: str
    decision: str
    reasons: List[str]
    obligations: List[str]
    request_hash: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def build_audit_record(capsule: Dict[str, Any], request: Dict[str, Any], decision_dict: Dict[str, Any]) -> AuditRecord:
    return AuditRecord(
        capsule_id=str(capsule.get("capsule_id", "")),
        actor=str(request.get("actor", "")),
        purpose=str(request.get("purpose", "")),
        action=str(request.get("action", "")),
        model_id=str(request.get("model_id", "")),
        decision=str(decision_dict.get("decision", "")),
        reasons=list(decision_dict.get("reasons", [])),
        obligations=list(decision_dict.get("obligations", [])),
        request_hash=request_hash(request),
    )
