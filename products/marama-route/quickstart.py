"""Quickstart smoke for LumynaX MaramaRoute."""
from __future__ import annotations

import json
from pathlib import Path

from marama_route.cli import main


ROOT = Path(__file__).resolve().parent


def run(args: list[str]) -> int:
    print("\n$ python -m marama_route.cli " + " ".join(args))
    return main(args)


if __name__ == "__main__":
    checks = [
        [
            "route",
            "--registry",
            str(ROOT / "configs" / "lumynax_model_registry.json"),
            "--request",
            str(ROOT / "examples" / "request.code-restricted.json"),
        ],
        [
            "models",
            "--registry",
            str(ROOT / "configs" / "lumynax_model_registry.json"),
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
            "catalog",
            "--registry",
            str(ROOT / "configs" / "lumynax_model_registry.json"),
            "--task",
            "code",
            "--limit",
            "3",
        ],
        [
            "matrix",
            "--registry",
            str(ROOT / "configs" / "lumynax_model_registry.json"),
        ],
        [
            "chat",
            "qwen25-05b",
            "--dry-run",
        ],
        [
            "pull",
            "qwen25-05b",
            "--registry",
            str(ROOT / "configs" / "lumynax_model_registry.json"),
            "--estimate",
        ],
        [
            "agent",
            "doctor",
            "--registry",
            str(ROOT / "configs" / "lumynax_model_registry.json"),
            "--model",
            "qwen25-7b",
        ],
        [
            "dry-run",
            "--registry",
            str(ROOT / "configs" / "lumynax_model_registry.json"),
            "--request",
            str(ROOT / "examples" / "request.chat-code.json"),
        ],
    ]
    exits = [run(item) for item in checks]
    print(json.dumps({"checks": len(exits), "passed": all(code == 0 for code in exits)}, indent=2))
    raise SystemExit(0 if all(code == 0 for code in exits) else 1)
