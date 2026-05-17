"""Quickstart for AbteeX SovereignCode.

Runs the two example policy evaluations and prints structured decisions and audit records.
"""
from __future__ import annotations

import json
from pathlib import Path

from sovereigncode import build_audit_record, evaluate, load_capsule, load_policy, load_request


ROOT = Path(__file__).parent
EXAMPLES = ROOT / "examples"
CONFIGS = ROOT / "configs"


def run(label: str, capsule_path: Path, request_path: Path) -> None:
    capsule = load_capsule(capsule_path)
    request = load_request(request_path)
    policy = load_policy(CONFIGS / "default_policy.yaml")
    decision = evaluate(capsule, request, policy)
    audit = build_audit_record(capsule, request, decision.to_dict())
    print(f"\n=== {label} ===")
    print(json.dumps({"decision": decision.to_dict(), "audit": audit.to_dict()}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    run("ALLOWED local edit", EXAMPLES / "capsule.restricted-nz-code.json", EXAMPLES / "request.allowed-local-edit.json")
    run("DENIED training",   EXAMPLES / "capsule.restricted-nz-code.json", EXAMPLES / "request.denied-training.json")
