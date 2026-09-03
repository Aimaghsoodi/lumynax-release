"""Canonical maintenance pipeline for the archived LumynaX model packs.

Run ``python publishing/maintain_legacy_archive.py --write`` to regenerate the
minimal package cards, remove retired diagrams, and refresh documentation and
manifest checksums. Run with ``--check`` in CI to reject drift.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "models"
OBSOLETE_SVGS = {
    "lumynax-capability.svg",
    "lumynax-overview.svg",
    "lumynax-release-map.svg",
    "lumynax-release-overview.svg",
    "lumynax-runtime-flow.svg",
}
CHECKSUM = re.compile(r"^([0-9a-f]{64})\s{2}(.+)$")


def upstream(manifest: dict) -> dict:
    return manifest.get("upstream") or manifest.get("upstream_model") or {}


def title(manifest: dict, fallback: str) -> str:
    return manifest.get("title") or manifest.get("model_title") or fallback


def runtime(manifest: dict) -> str:
    value = manifest.get("runtime")
    if isinstance(value, dict):
        value = value.get("preferred_backend") or value.get("delivery_mode")
    names = {
        "llama_cpp": "llama.cpp",
        "transformers": "Transformers",
        "transformers_multimodal": "Transformers multimodal",
        "native": "Native runtime",
    }
    return names.get(str(value), str(value or "See manifest").replace("_", " "))


def architecture(native: bool) -> str:
    if native:
        return """## How the model fits

**LumynaX Core is the core intelligence model.** It governs the inference path, applying sovereignty controls, context, agentic planning, and inference optimisation around execution.

```text
Prompt  →  LumynaX Core  →  Native LumynaX model  →  Response
```

This is a LumynaX-native release rather than an infused open-source model pack. Its release manifest does not identify external source-model weights.
"""
    return """## How infusion works

**LumynaX Core is the core intelligence model.** It governs the inference path and integrates selected open-source models as specialised execution layers.

```text
Prompt  →  LumynaX Core  →  Infused model / MoE experts  →  LumynaX Core  →  Response
```

**LumynaX infusion** is the controlled composition of LumynaX Core with a compatible open-source model. Depending on the model family and deployment objective, the integration can operate in two ways:

- **Routed infusion** — LumynaX Core directs inference through the selected model without modifying its weights.
- **MoE infusion** — when required by the architecture, compatible model weights can be composed as specialised experts within a Mixture-of-Experts design.

In both cases, LumynaX Core remains the primary intelligence and orchestration layer, applying sovereignty controls, context, agentic planning, and inference optimisation around model execution. Infusion does not automatically imply a weight merge; each release manifest records the method used by that pack.
"""


def model_card(manifest: dict, name: str) -> str:
    source = upstream(manifest).get("repo_id")
    native = not bool(source)
    version = manifest.get("version") or manifest.get("release_version") or "See manifest"
    if source:
        rows = [
            ("Infused model", f"[`{source}`](https://huggingface.co/{source})"),
            ("Infusion method", "Routed runtime and identity integration"),
            ("Weight composition", "None — this pack preserves the source-model weights"),
            ("Runtime", runtime(manifest)),
            ("Release", version),
            ("Status", "Outdated and retained for research provenance only"),
        ]
        note = "This package predates the current LumynaX Core implementation. Its included identity, runtime, or deployment wrappers are historical release components—not the complete modern LumynaX pipeline."
    else:
        rows = [
            ("Model lineage", "LumynaX-native"),
            ("External infused model", "Not applicable"),
            ("Runtime", runtime(manifest)),
            ("Release", version),
            ("Status", "Outdated and retained for research provenance only"),
        ]
        note = "This native model predates the current LumynaX Core implementation. It is a historical release artifact—not the complete modern LumynaX pipeline."
    table = "\n".join(f"| **{key}** | {value} |" for key, value in rows)
    return f"""# {title(manifest, name)}

> **Legacy release · Outdated research artifact**

This repository documents an early LumynaX experiment. It is no longer maintained, is not recommended for production, and does not represent the current capabilities, architecture, or safety standards of AbteeX AI Labs.

{architecture(native)}
## This release

| | |
|---|---|
{table}

{note}

## Archive access

The code and artifacts remain available for reproducibility. Before evaluation, verify [`checksums.sha256`](checksums.sha256), inspect [`release_export_manifest.json`](release_export_manifest.json), and review [`LICENSE.txt`](LICENSE.txt).

- [Model card and artifacts on Hugging Face](https://huggingface.co/AbteeXAILab/{name})
- [AbteeX AI Labs](https://abteex.com)
- [LumynaX](https://lumynax.com)
- [Contact](mailto:aimaghsoodi@abteex.com)

---

**AbteeX AI Labs · Aotearoa New Zealand**
"""


def split_frontmatter(text: str) -> tuple[dict, str]:
    match = re.match(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", text, re.DOTALL)
    if not match:
        return {}, text
    return yaml.safe_load(match.group(1)) or {}, text[match.end() :]


def space_card(manifest: dict, name: str, current: str) -> str:
    metadata, _ = split_frontmatter(current)
    metadata["short_description"] = "Legacy LumynaX demo. Outdated; not for production."
    tags = metadata.get("tags") if isinstance(metadata.get("tags"), list) else []
    for tag in ("legacy", "outdated"):
        if tag not in tags:
            tags.append(tag)
    metadata["tags"] = tags
    frontmatter = yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True, width=1000).strip()
    native = not bool(upstream(manifest).get("repo_id"))
    return f"""---
{frontmatter}
---

# {title(manifest, name)} · Legacy demo

> **Outdated research interface · Not for production**

This Space scaffold belongs to [`AbteeXAILab/{name}`](https://huggingface.co/AbteeXAILab/{name}). It is no longer maintained and does not represent the current LumynaX Core experience.

{architecture(native)}
This interface exposes only the historical package runtime. Consult the model pack's `release_export_manifest.json` for its recorded infusion method, weights, runtime, and provenance.

- [Model artifacts](https://huggingface.co/AbteeXAILab/{name})
- [AbteeX AI Labs](https://abteex.com)
- [Contact](mailto:aimaghsoodi@abteex.com)
"""


def refresh_checksums(package: Path) -> str:
    path = package / "checksums.sha256"
    output = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = CHECKSUM.match(line)
        if not match:
            output.append(line)
            continue
        old_hash, relative = match.groups()
        relative = relative.replace("\\", "/")
        target = package / relative
        if relative.startswith("docs/") and relative.endswith(".svg") and not target.exists():
            continue
        if relative in {"README.md", "hf_space/README.md", "release_export_manifest.json"} and target.is_file():
            old_hash = hashlib.sha256(target.read_bytes()).hexdigest()
        output.append(f"{old_hash}  {relative}")
    return "\n".join(output) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write == args.check:
        parser.error("choose exactly one of --write or --check")
    drift = []
    packages = [path for path in sorted(MODELS.iterdir()) if (path / "release_export_manifest.json").is_file()]
    for package in packages:
        name = package.name
        manifest = json.loads((package / "release_export_manifest.json").read_text(encoding="utf-8"))
        lifecycle = manifest.get("lifecycle") or {}
        infusion = manifest.get("lumynax_infusion") or {}
        if manifest.get("lumynax_manifest_version") != 3 or lifecycle.get("status") != "legacy":
            drift.append(f"{name}: manifest schema")
        source = upstream(manifest).get("repo_id")
        expected_method = "routed" if source else "native"
        if infusion.get("method") != expected_method or infusion.get("infused_model") != source:
            drift.append(f"{name}: infusion metadata")
        desired = model_card(manifest, name)
        readme = package / "README.md"
        if readme.read_text(encoding="utf-8").rstrip() != desired.rstrip():
            drift.append(f"{name}: README")
            if args.write:
                readme.write_text(desired, encoding="utf-8", newline="\n")
        space = package / "hf_space" / "README.md"
        if space.is_file():
            desired_space = space_card(manifest, name, space.read_text(encoding="utf-8"))
            if space.read_text(encoding="utf-8").rstrip() != desired_space.rstrip():
                drift.append(f"{name}: Space README")
                if args.write:
                    space.write_text(desired_space, encoding="utf-8", newline="\n")
        for svg in (package / "docs").glob("*.svg"):
            if svg.name in OBSOLETE_SVGS:
                drift.append(f"{name}: obsolete diagram {svg.name}")
                if args.write:
                    svg.unlink()
        desired_checksums = refresh_checksums(package)
        checksums = package / "checksums.sha256"
        if checksums.read_text(encoding="utf-8") != desired_checksums:
            drift.append(f"{name}: checksums")
            if args.write:
                checksums.write_text(desired_checksums, encoding="utf-8", newline="\n")
    if args.write:
        print(f"Updated {len(packages)} packages ({len(drift)} corrected items).")
    elif drift:
        print("Legacy archive drift detected:\n- " + "\n- ".join(drift))
        raise SystemExit(1)
    else:
        print(f"Legacy archive verified: {len(packages)} packages.")


if __name__ == "__main__":
    main()
