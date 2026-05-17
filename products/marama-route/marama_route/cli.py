"""MaramaRoute CLI: deterministic sovereign routing."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .router import load_registry, load_request, route


def main() -> int:
    parser = argparse.ArgumentParser(prog="marama-route", description="LumynaX MaramaRoute — sovereign model router.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("route", help="Route a request against the registry.")
    r.add_argument("--registry", required=True, help="Path to registry JSON.")
    r.add_argument("--request", required=True, help="Path to request JSON.")
    r.add_argument("--full", action="store_true", help="Print the full decision including rejected models.")

    args = parser.parse_args()

    if args.cmd == "route":
        registry = load_registry(args.registry)
        request = load_request(args.request)
        decision = route(registry, request)
        out = decision.to_dict()
        if not args.full:
            out.pop("rejected", None)
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0 if decision.selected else 3

    return 1


if __name__ == "__main__":
    sys.exit(main())
