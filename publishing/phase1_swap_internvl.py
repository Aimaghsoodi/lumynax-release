"""Phase 1: drop Llama-4-Scout (gated), create InternVL3-78B in its place,
fix Qwen2.5-VL + DBRX scaffold pointers to working mirrors, refresh registry."""
import json, os, sys, time
from pathlib import Path
sys.path.insert(0, r"S:\hf-publish")
from huggingface_hub import HfApi
from add_8_more_models import (
    NEW_MODELS, build_and_push, _gen_quickstart, _gen_requirements,
    _gen_manifest, _gen_modelfile, _checksums, SPACE_APP, SPACE_README,
    LICENSE_BLURB, VERSION_TXT, UPLOAD_TO_HF_MD, OUT,
)
import generate_cards_v6 as G

TOKEN = os.environ["HF_TOKEN"]
api = HfApi(token=TOKEN)
REG_PATH = G.REGISTRY_PATH
REG_LOCAL = Path(r"S:\hf-publish\marama-route\configs\lumynax_model_registry.json")

# 1) Delete gated Llama-4-Scout scaffold
SCOUT = "AbteeXAILab/lumynax-multimodal-llama4-scout-109b-instruct"
try:
    api.delete_repo(SCOUT, repo_type="model", token=TOKEN)
    print(f"deleted {SCOUT}")
except Exception as e:
    print(f"delete {SCOUT}: {e}")

# 2) Build new InternVL3-78B spec
INTERNVL = {
    "model_id": "lumynax-multimodal-internvl3-78b-instruct",
    "repo_id": "AbteeXAILab/lumynax-multimodal-internvl3-78b-instruct",
    "title": "LumynaX Multimodal InternVL3 78B Instruct",
    "family": "internvl",
    "runtime": "transformers_multimodal",
    "modalities": ["text", "vision"],
    "context_tokens": 32768,
    "jurisdiction": "NZ",
    "residency": ["NZ", "AU", "global"],
    "license_id": "mit",
    "quantization": "bf16 (safetensors mirror) — community GGUF when available",
    "primary_artifact": "model.safetensors (33 shards)",
    "active_params_b": None,
    "total_params_b": 78,
    "quality_rank": 2,
    "cost_rank": 4,
    "sovereignty_tier": 2,
    "supports_tools": True,
    "supports_json": True,
    "tags": ["multimodal", "vision", "internvl", "opengvlab", "image-text-to-text"],
    "metadata": {
        "upstream_repo": "OpenGVLab/InternVL3-78B-Instruct",
        "release_version": "v0.1.0",
        "package_state": "weights_mirrored_safetensors",
        "public_status": "public and non-gated",
        "validation_status": "scaffold_verified",
    },
    "_upstream": ("OpenGVLab/InternVL3-78B-Instruct", "mit", "internvl", "OpenGVLab InternVL3 upstream"),
    "_kind": "transformers_multimodal",
    "_gguf_mirror": None,
}

# Patch infer_upstream
_orig = G.infer_upstream
def _patched(mid, family):
    if mid == INTERNVL["model_id"]: return INTERNVL["_upstream"]
    if "internvl" in mid: return INTERNVL["_upstream"]
    return _orig(mid, family)
G.infer_upstream = _patched

# Build & push scaffold
print("\nBuilding InternVL3-78B scaffold...")
result = build_and_push(INTERNVL)
print("scaffold push:", result)

# 3) Update registry: remove llama4-scout, add internvl
reg = json.loads(REG_PATH.read_text(encoding="utf-8"))
reg["models"] = [m for m in reg["models"] if m["repo_id"] != SCOUT]
# strip _-prefixed keys before storing
internvl_clean = {k:v for k,v in INTERNVL.items() if not k.startswith("_")}
if not any(m["repo_id"] == INTERNVL["repo_id"] for m in reg["models"]):
    reg["models"].append(internvl_clean)
reg["model_count"] = len(reg["models"])
REG_PATH.write_text(json.dumps(reg, indent=2), encoding="utf-8")
REG_LOCAL.write_text(json.dumps(reg, indent=2), encoding="utf-8")
print(f"registry updated: {reg['model_count']} models")

# 4) Re-push scaffold for DBRX + Qwen2.5-VL with working mirror pointers
FIXED = []
for spec in NEW_MODELS:
    if "dbrx" in spec["model_id"]:
        spec["_gguf_mirror"] = "mradermacher/dbrx-instruct-i1-GGUF"
        spec["_gguf_filename"] = "*i1-IQ3_M*.gguf"
        spec["quantization"] = "IQ3_M imatrix (community best non-Q2; ~45 GB)"
        spec["primary_artifact"] = "dbrx-instruct.i1-IQ3_M.gguf"
        FIXED.append(spec)
    elif "qwen25-vl-72b" in spec["model_id"]:
        spec["_gguf_mirror"] = "ggml-org/Qwen2.5-VL-72B-Instruct-GGUF"
        spec["_gguf_filename"] = "Qwen2.5-VL-72B-Instruct-Q4_K_M.gguf"
        spec["_mmproj"] = "mmproj-Qwen2.5-VL-72B-Instruct-f16.gguf"
        FIXED.append(spec)

for spec in FIXED:
    print(f"\nRe-pushing fixed scaffold for {spec['repo_id']}...")
    result = build_and_push(spec)
    print(" ", result)

# Re-upload registry to marama-route
api.upload_file(
    path_or_fileobj=str(REG_PATH),
    path_in_repo="configs/lumynax_model_registry.json",
    repo_id="AbteeXAILab/marama-route",
    repo_type="model",
    token=TOKEN,
    commit_message="chore(registry): swap gated Llama-4-Scout for InternVL3-78B; fix DBRX/Qwen2.5-VL mirror pointers",
)
print("\nregistry pushed to marama-route.")
print("phase 1 done.")
