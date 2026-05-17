"""SovereignCode CLI: evaluate a request against a capsule and policy."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .audit import build_audit_record
from .policy import evaluate, load_capsule, load_policy, load_request


DEFAULT_POLICY = Path(__file__).parent.parent / "configs" / "default_policy.yaml"


def main() -> int:
    parser = argparse.ArgumentParser(prog="sovereigncode", description="AbteeX SovereignCode — Data Capsule policy evaluator.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    ev = sub.add_parser("evaluate", help="Evaluate a request against a capsule.")
    ev.add_argument("--capsule", required=True, help="Path to capsule JSON.")
    ev.add_argument("--request", required=True, help="Path to request JSON.")
    ev.add_argument("--policy", default=str(DEFAULT_POLICY), help="Path to policy YAML (default: configs/default_policy.yaml).")
    ev.add_argument("--allow-denied-exit-zero", action="store_true", help="Exit 0 even when the decision is deny (useful for examples).")

    args = parser.parse_args()

    if args.cmd == "evaluate":
        capsule = load_capsule(args.capsule)
        request = load_request(args.request)
        policy = load_policy(args.policy)
        decision = evaluate(capsule, request, policy)
        audit = build_audit_record(capsule, request, decision.to_dict())
        out = {
            "decision": decision.to_dict(),
            "audit": audit.to_dict(),
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
        if not decision.allowed and not args.allow_denied_exit_zero:
            return 2
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
