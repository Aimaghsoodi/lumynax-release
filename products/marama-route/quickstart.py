"""Quickstart for LumynaX MaramaRoute."""
from __future__ import annotations

import json
from pathlib import Path

from marama_route import load_registry, load_request, route


ROOT = Path(__file__).parent


def run(label: str, request_path: Path) -> None:
    registry = load_registry(ROOT / "configs" / "lumynax_model_registry.json")
    request = load_request(request_path)
    decision = route(registry, request)
    print(f"\n=== {label} ===")
    out = decision.to_dict()
    # Trim rejected list for quickstart readability.
    out["rejected"] = out["rejected"][:3] + ([f"... {len(out['rejected']) - 3} more"] if len(out["rejected"]) > 3 else [])
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    run("Restricted NZ code", ROOT / "examples" / "request.code-restricted.json")
    run("Public multimodal",  ROOT / "examples" / "request.multimodal-public.json")
