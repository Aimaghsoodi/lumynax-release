"""Validate canonical metadata for the LumynaX legacy model archive."""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "models"
REGISTRY = ROOT / "registry" / "legacy_model_metadata.json"


def main() -> None:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    records = {item["repo_id"].split("/", 1)[1]: item for item in registry["models"]}
    packages = {
        path.name: path
        for path in MODELS.iterdir()
        if (path / "release_export_manifest.json").is_file()
    }
    errors = []
    if registry.get("schema_version") != 1 or registry.get("status") != "legacy":
        errors.append("registry schema or lifecycle is invalid")
    if records.keys() != packages.keys():
        errors.append("registry and package sets differ")
    for name, package in sorted(packages.items()):
        record = records.get(name, {})
        manifest = json.loads((package / "release_export_manifest.json").read_text(encoding="utf-8"))
        source = (manifest.get("upstream") or manifest.get("upstream_model") or {}).get("repo_id")
        infusion = manifest.get("lumynax_infusion") or {}
        lifecycle = manifest.get("lifecycle") or {}
        licensing = manifest.get("licensing") or {}
        expected_method = "routed" if source else "native"
        if manifest.get("lumynax_manifest_version") != 3:
            errors.append(f"{name}: manifest version")
        if lifecycle != {
            "status": "legacy",
            "maintenance": "unmaintained",
            "production_recommended": False,
        }:
            errors.append(f"{name}: lifecycle")
        if infusion.get("core_role") != "primary_intelligence_model":
            errors.append(f"{name}: core role")
        if infusion.get("method") != expected_method or infusion.get("infused_model") != source:
            errors.append(f"{name}: infusion lineage")
        if infusion.get("weight_composition_applied") is not False:
            errors.append(f"{name}: unsupported weight-composition claim")
        if record.get("base_model") != source or record.get("infusion_method") != expected_method:
            errors.append(f"{name}: canonical registry lineage")
        if not record.get("pipeline_tag") or not record.get("license"):
            errors.append(f"{name}: canonical technical metadata")
        if licensing.get("id") != record.get("license"):
            errors.append(f"{name}: licence metadata")
        readme = (package / "README.md").read_text(encoding="utf-8")
        for required in (
            "Outdated research artifact",
            "not recommended for production",
            "LumynaX Core is the core intelligence model",
        ):
            if required not in readme:
                errors.append(f"{name}: README missing {required!r}")
        space = package / "hf_space" / "README.md"
        if space.is_file():
            text = space.read_text(encoding="utf-8")
            match = re.match(r"\A---\s*\n(.*?)\n---", text, re.DOTALL)
            metadata = yaml.safe_load(match.group(1)) if match else {}
            if "outdated" not in metadata.get("tags", []):
                errors.append(f"{name}: Space lifecycle tag")
            if len(metadata.get("short_description", "")) > 60:
                errors.append(f"{name}: Space short description")
    if errors:
        print("Legacy metadata validation failed:\n- " + "\n- ".join(errors))
        raise SystemExit(1)
    print(f"Legacy metadata verified: {len(packages)} packages.")


if __name__ == "__main__":
    main()
