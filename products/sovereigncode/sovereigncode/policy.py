"""Deterministic Data Capsule policy decision point (PDP).

Answers, for every sensitive action: can this actor, for this purpose, in this
region, using this model/tool, touch this capsule?

Returns one of three outcomes: allow, deny, or allow_with_obligations.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None


@dataclass
class Decision:
    allowed: bool
    decision: str  # "allow" | "deny" | "allow_with_obligations"
    reasons: List[str] = field(default_factory=list)
    obligations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "decision": self.decision,
            "reasons": list(self.reasons),
            "obligations": list(self.obligations),
        }


def _load_yaml_or_json(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml", ".yml"):
        if yaml is None:
            raise RuntimeError("pyyaml is required to load YAML policies. `pip install pyyaml`.")
        return yaml.safe_load(text)
    return json.loads(text)


def load_capsule(path: str | Path) -> Dict[str, Any]:
    return _load_yaml_or_json(Path(path))


def load_request(path: str | Path) -> Dict[str, Any]:
    return _load_yaml_or_json(Path(path))


def load_policy(path: str | Path) -> Dict[str, Any]:
    return _load_yaml_or_json(Path(path))


def evaluate(capsule: Dict[str, Any], request: Dict[str, Any], policy: Dict[str, Any]) -> Decision:
    reasons: List[str] = []
    obligations: List[str] = list(policy.get("default_obligations", []))

    purpose = request.get("purpose")
    if purpose in capsule.get("denied_purposes", []):
        reasons.append(f"purpose `{purpose}` is in capsule.denied_purposes")
        return Decision(False, "deny", reasons, obligations)

    allowed_purposes = capsule.get("allowed_purposes", [])
    if allowed_purposes and purpose not in allowed_purposes:
        reasons.append(f"purpose `{purpose}` is not in capsule.allowed_purposes")
        return Decision(False, "deny", reasons, obligations)

    region = request.get("region")
    resident_regions = capsule.get("resident_regions", [])
    if region and resident_regions and region not in resident_regions:
        reasons.append(f"region `{region}` is not in capsule.resident_regions `{resident_regions}`")
        return Decision(False, "deny", reasons, obligations)

    sensitivity = str(capsule.get("sensitivity", "")).lower()
    high_sensitivity = set(map(str.lower, policy.get("high_impact_sensitivity", [])))
    is_high = sensitivity in high_sensitivity
    requires_local = (
        policy.get("remote_model_rule", {}).get("restricted_data_requires_local_or_lumynax")
        and is_high
    )
    model_id = str(request.get("model_id", "")).lower()
    if requires_local and not (model_id.startswith("local/") or "lumynax" in model_id):
        reasons.append("restricted data requires a local or LumynaX-governed model")
        return Decision(False, "deny", reasons, obligations)

    if request.get("trains_model"):
        rule = policy.get("training_rule", {})
        if rule.get("requires_capsule_training_allowed") and not capsule.get("training_allowed", False):
            reasons.append("training_rule requires capsule.training_allowed = true")
            return Decision(False, "deny", reasons, obligations)

    if request.get("exports_data"):
        rule = policy.get("export_rule", {})
        if rule.get("requires_capsule_export_allowed") and not capsule.get("export_allowed", False):
            reasons.append("export_rule requires capsule.export_allowed = true")
            return Decision(False, "deny", reasons, obligations)

    denied_without_approval = set(policy.get("denied_without_human_approval", []))
    action = request.get("action")
    if action in denied_without_approval and not request.get("human_approved", False):
        reasons.append(f"action `{action}` requires human approval")
        return Decision(False, "deny", reasons, obligations)

    if request.get("writes_files"):
        obligations.append("show_diff_before_write_or_commit")
    if is_high:
        obligations.append("route_to_local_or_lumynax_model")

    obligations = sorted(set(obligations))
    reasons.append(f"capsule {capsule.get('capsule_id')} permits purpose `{purpose}` in region `{region}`")
    return Decision(True, "allow_with_obligations" if obligations else "allow", reasons, obligations)
