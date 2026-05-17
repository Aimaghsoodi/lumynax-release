"""Quickstart smoke for AbteeX SovereignCode."""
from __future__ import annotations

import json
from pathlib import Path

from sovereigncode.cli import main


ROOT = Path(__file__).resolve().parent


def run(args: list[str]) -> int:
    print("\n$ python -m sovereigncode.cli " + " ".join(args))
    return main(args)


if __name__ == "__main__":
    checks = [
        [
            "evaluate",
            "--capsule",
            str(ROOT / "examples" / "capsule.restricted-nz-code.json"),
            "--request",
            str(ROOT / "examples" / "request.allowed-local-edit.json"),
        ],
        [
            "ui",
            "--smoke",
        ],
        [
            "serve",
            "--smoke",
        ],
        [
            "policy-matrix",
            "--capsule",
            str(ROOT / "examples" / "capsule.restricted-nz-code.json"),
            "--request",
            str(ROOT / "examples" / "request.allowed-local-edit.json"),
        ],
        [
            "tool-check",
            "--capsule",
            str(ROOT / "examples" / "capsule.restricted-nz-code.json"),
            "--request",
            str(ROOT / "examples" / "request.allowed-local-edit.json"),
            "--tool-name",
            "workspace_reader",
            "--action",
            "read_context",
        ],
        [
            "plan-turn",
            "--capsule",
            str(ROOT / "examples" / "capsule.restricted-nz-code.json"),
            "--request",
            str(ROOT / "examples" / "request.allowed-local-edit.json"),
            "--route-request",
            str(ROOT / "examples" / "request.code-restricted.json"),
            "--registry",
            str(ROOT / "configs" / "lumynax_model_registry.json"),
        ],
    ]
    exits = [run(item) for item in checks]
    print(json.dumps({"checks": len(exits), "passed": all(code == 0 for code in exits)}, indent=2))
    raise SystemExit(0 if all(code == 0 for code in exits) else 1)
