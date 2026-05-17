"""
Pack B — Frontier Round 2 (8 models).
Non-gated frontier dense + MoE + multimodal + reasoning + fully-open.
"""
from __future__ import annotations
import json, os, sys, time
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, r"S:\hf-publish")
from huggingface_hub import HfApi
import generate_cards_v6 as G
from add_8_more_models import build_and_push
from pack_a_ship import mirror_files, free_gb, hum

TOKEN = os.environ["HF_TOKEN"]
api = HfApi(token=TOKEN)
LOG = Path(r"S:\hf-publish\pack_b_progress.log")
REG_PATH = G.REGISTRY_PATH
REG_LOCAL = Path(r"S:\hf-publish\marama-route\configs\lumynax_model_registry.json")

def log(m: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    LOG.open("a", encoding="utf-8").write(line + "\n")

SPECS: List[Dict[str, Any]] = [
    {
        "model_id": "lumynax-frontier-qwen25-72b-instruct-gguf", "repo_id": "AbteeXAILab/lumynax-frontier-qwen25-72b-instruct-gguf",
        "title": "LumynaX Frontier Qwen2.5 72B Instruct GGUF",
        "family": "qwen", "runtime": "llama_cpp", "modalities": ["text"],
        "context_tokens": 131072, "jurisdiction": "NZ", "residency": ["NZ","AU","global"],
        "license_id": "other", "quantization": "Q4_K_M GGUF",
        "primary_artifact": "Qwen2.5-72B-Instruct-Q4_K_M.gguf",
        "active_params_b": None, "total_params_b": 72,
        "quality_rank": 1, "cost_rank": 4, "sovereignty_tier": 3,
        "supports_tools": True, "supports_json": True,
        "tags": ["frontier","dense","qwen","gguf","tools","long-context"],
        "metadata": {"upstream_repo":"Qwen/Qwen2.5-72B-Instruct","release_version":"v0.1.0","package_state":"weights_mirrored","public_status":"public and non-gated","validation_status":"scaffold_verified"},
        "_upstream": ("Qwen/Qwen2.5-72B-Instruct","other","chatml","Qwen2.5"),
        "_kind": "gguf", "_gguf_mirror": "bartowski/Qwen2.5-72B-Instruct-GGUF", "_gguf_filename": "Qwen2.5-72B-Instruct-Q4_K_M.gguf",
        "_mirror": {"source":"bartowski/Qwen2.5-72B-Instruct-GGUF","patterns":["Qwen2.5-72B-Instruct-Q4_K_M.gguf"]},
    },
    {
        "model_id": "lumynax-frontier-olmo2-32b-instruct", "repo_id": "AbteeXAILab/lumynax-frontier-olmo2-32b-instruct",
        "title": "LumynaX Frontier OLMo-2 32B Instruct (fully open)",
        "family": "olmo", "runtime": "transformers", "modalities": ["text"],
        "context_tokens": 4096, "jurisdiction": "NZ", "residency": ["NZ","AU","global"],
        "license_id": "apache-2.0", "quantization": "bf16 safetensors",
        "primary_artifact": "model.safetensors (sharded)",
        "active_params_b": None, "total_params_b": 32,
        "quality_rank": 1, "cost_rank": 4, "sovereignty_tier": 2,
        "supports_tools": True, "supports_json": True,
        "tags": ["frontier","fully-open","olmo","allenai","apache"],
        "metadata": {"upstream_repo":"allenai/OLMo-2-0325-32B-Instruct","release_version":"v0.1.0","package_state":"weights_mirrored","public_status":"public and non-gated","validation_status":"scaffold_verified"},
        "_upstream": ("allenai/OLMo-2-0325-32B-Instruct","apache-2.0","olmo","AllenAI OLMo-2"),
        "_kind": "transformers_text", "_gguf_mirror": None,
        "_mirror": {"source":"allenai/OLMo-2-0325-32B-Instruct","patterns":["model-*.safetensors","model.safetensors","model.safetensors.index.json","pytorch_model*.bin","pytorch_model.bin.index.json","config.json","tokenizer*","special_tokens_map.json","added_tokens.json","generation_config.json"]},
    },
    {
        "model_id": "lumynax-chat-yi-15-34b-gguf", "repo_id": "AbteeXAILab/lumynax-chat-yi-15-34b-gguf",
        "title": "LumynaX Chat Yi-1.5 34B GGUF (multilingual)",
        "family": "yi", "runtime": "llama_cpp", "modalities": ["text"],
        "context_tokens": 32768, "jurisdiction": "NZ", "residency": ["NZ"],
        "license_id": "apache-2.0", "quantization": "Q4_K_M GGUF",
        "primary_artifact": "Yi-1.5-34B-Chat-Q4_K_M.gguf",
        "active_params_b": None, "total_params_b": 34,
        "quality_rank": 2, "cost_rank": 3, "sovereignty_tier": 3,
        "supports_tools": True, "supports_json": True,
        "tags": ["chat","yi","multilingual","gguf"],
        "metadata": {"upstream_repo":"01-ai/Yi-1.5-34B-Chat","release_version":"v0.1.0","package_state":"weights_mirrored","public_status":"public and non-gated","validation_status":"scaffold_verified"},
        "_upstream": ("01-ai/Yi-1.5-34B-Chat","apache-2.0","chatml","01-ai Yi"),
        "_kind": "gguf", "_gguf_mirror": "bartowski/Yi-1.5-34B-Chat-GGUF", "_gguf_filename": "Yi-1.5-34B-Chat-Q4_K_M.gguf",
        "_mirror": {"source":"bartowski/Yi-1.5-34B-Chat-GGUF","patterns":["Yi-1.5-34B-Chat-Q4_K_M.gguf"]},
    },
    {
        "model_id": "lumynax-reasoning-internlm3-8b-gguf", "repo_id": "AbteeXAILab/lumynax-reasoning-internlm3-8b-gguf",
        "title": "LumynaX Reasoning InternLM3 8B Instruct GGUF",
        "family": "internlm", "runtime": "llama_cpp", "modalities": ["text"],
        "context_tokens": 32768, "jurisdiction": "NZ", "residency": ["NZ"],
        "license_id": "apache-2.0", "quantization": "Q4_K_M GGUF",
        "primary_artifact": "internlm3-8b-instruct-Q4_K_M.gguf",
        "active_params_b": None, "total_params_b": 8,
        "quality_rank": 2, "cost_rank": 2, "sovereignty_tier": 3,
        "supports_tools": True, "supports_json": True,
        "tags": ["reasoning","internlm","chat","gguf"],
        "metadata": {"upstream_repo":"internlm/internlm3-8b-instruct","release_version":"v0.1.0","package_state":"weights_mirrored","public_status":"public and non-gated","validation_status":"scaffold_verified"},
        "_upstream": ("internlm/internlm3-8b-instruct","apache-2.0","chatml","InternLM"),
        "_kind": "gguf", "_gguf_mirror": "bartowski/internlm3-8b-instruct-GGUF", "_gguf_filename": "internlm3-8b-instruct-Q4_K_M.gguf",
        "_mirror": {"source":"bartowski/internlm3-8b-instruct-GGUF","patterns":["internlm3-8b-instruct-Q4_K_M.gguf"]},
    },
    {
        "model_id": "lumynax-multimodal-aria-25b-moe", "repo_id": "AbteeXAILab/lumynax-multimodal-aria-25b-moe",
        "title": "LumynaX Multimodal Aria 25B/3.5B MoE",
        "family": "aria", "runtime": "transformers_multimodal", "modalities": ["text","vision"],
        "context_tokens": 65536, "jurisdiction": "NZ", "residency": ["NZ","AU","global"],
        "license_id": "apache-2.0", "quantization": "bf16 safetensors",
        "primary_artifact": "model.safetensors (sharded)",
        "active_params_b": 3.5, "total_params_b": 25,
        "quality_rank": 2, "cost_rank": 3, "sovereignty_tier": 2,
        "supports_tools": True, "supports_json": True,
        "tags": ["multimodal","vision","moe","aria","apache"],
        "metadata": {"upstream_repo":"rhymes-ai/Aria","release_version":"v0.1.0","package_state":"weights_mirrored","public_status":"public and non-gated","validation_status":"scaffold_verified"},
        "_upstream": ("rhymes-ai/Aria","apache-2.0","aria","Rhymes Aria"),
        "_kind": "transformers_multimodal", "_gguf_mirror": None,
        "_mirror": {"source":"rhymes-ai/Aria","patterns":["model-*.safetensors","model.safetensors.index.json","config.json","tokenizer*","special_tokens_map.json","added_tokens.json","generation_config.json","preprocessor_config.json","configuration*.py","modeling*.py","processing*.py","vision_processor*.py"]},
    },
    {
        "model_id": "lumynax-multimodal-llava-next-34b", "repo_id": "AbteeXAILab/lumynax-multimodal-llava-next-34b",
        "title": "LumynaX Multimodal LLaVA-Next 34B",
        "family": "llava", "runtime": "transformers_multimodal", "modalities": ["text","vision"],
        "context_tokens": 4096, "jurisdiction": "NZ", "residency": ["NZ","AU","global"],
        "license_id": "apache-2.0", "quantization": "bf16 safetensors",
        "primary_artifact": "model.safetensors (sharded)",
        "active_params_b": None, "total_params_b": 34,
        "quality_rank": 2, "cost_rank": 4, "sovereignty_tier": 2,
        "supports_tools": False, "supports_json": True,
        "tags": ["multimodal","vision","llava","yi-based"],
        "metadata": {"upstream_repo":"liuhaotian/llava-v1.6-34b","release_version":"v0.1.0","package_state":"weights_mirrored","public_status":"public and non-gated","validation_status":"scaffold_verified"},
        "_upstream": ("liuhaotian/llava-v1.6-34b","apache-2.0","llava","liuhaotian LLaVA-Next"),
        "_kind": "transformers_multimodal", "_gguf_mirror": None,
        "_mirror": {"source":"liuhaotian/llava-v1.6-34b","patterns":["model-*.safetensors","model.safetensors","model.safetensors.index.json","pytorch_model*.bin","pytorch_model.bin.index.json","config.json","tokenizer*","special_tokens_map.json","added_tokens.json","generation_config.json","preprocessor_config.json"]},
    },
    {
        "model_id": "lumynax-reasoning-qwq-32b-gguf", "repo_id": "AbteeXAILab/lumynax-reasoning-qwq-32b-gguf",
        "title": "LumynaX Reasoning QwQ-32B GGUF",
        "family": "qwen", "runtime": "llama_cpp", "modalities": ["text"],
        "context_tokens": 131072, "jurisdiction": "NZ", "residency": ["NZ"],
        "license_id": "apache-2.0", "quantization": "Q4_K_M GGUF",
        "primary_artifact": "qwq-32b-q4_k_m.gguf",
        "active_params_b": None, "total_params_b": 32,
        "quality_rank": 1, "cost_rank": 3, "sovereignty_tier": 3,
        "supports_tools": True, "supports_json": True,
        "tags": ["reasoning","qwq","qwen","gguf","chain-of-thought"],
        "metadata": {"upstream_repo":"Qwen/QwQ-32B","release_version":"v0.1.0","package_state":"weights_mirrored","public_status":"public and non-gated","validation_status":"scaffold_verified"},
        "_upstream": ("Qwen/QwQ-32B","apache-2.0","chatml","Qwen QwQ reasoning"),
        "_kind": "gguf", "_gguf_mirror": "Qwen/QwQ-32B-GGUF", "_gguf_filename": "qwq-32b-q4_k_m.gguf",
        "_mirror": {"source":"Qwen/QwQ-32B-GGUF","patterns":["qwq-32b-q4_k_m.gguf"]},
    },
    {
        "model_id": "lumynax-frontier-phi-4-14b-gguf", "repo_id": "AbteeXAILab/lumynax-frontier-phi-4-14b-gguf",
        "title": "LumynaX Frontier Phi-4 14B GGUF",
        "family": "phi", "runtime": "llama_cpp", "modalities": ["text"],
        "context_tokens": 16384, "jurisdiction": "NZ", "residency": ["NZ"],
        "license_id": "mit", "quantization": "Q4_K_M GGUF",
        "primary_artifact": "phi-4-Q4_K_M.gguf",
        "active_params_b": None, "total_params_b": 14,
        "quality_rank": 2, "cost_rank": 2, "sovereignty_tier": 3,
        "supports_tools": True, "supports_json": True,
        "tags": ["frontier","phi","microsoft","gguf","efficient"],
        "metadata": {"upstream_repo":"microsoft/phi-4","release_version":"v0.1.0","package_state":"weights_mirrored","public_status":"public and non-gated","validation_status":"scaffold_verified"},
        "_upstream": ("microsoft/phi-4","mit","chatml","Microsoft Phi-4"),
        "_kind": "gguf", "_gguf_mirror": "unsloth/phi-4-GGUF", "_gguf_filename": "phi-4-Q4_K_M.gguf",
        "_mirror": {"source":"unsloth/phi-4-GGUF","patterns":["phi-4-Q4_K_M.gguf"]},
    },
]

_orig = G.infer_upstream
_p = {s["model_id"]: s["_upstream"] for s in SPECS}
def _patched(mid, family):
    if mid in _p: return _p[mid]
    return _orig(mid, family)
G.infer_upstream = _patched


def update_registry():
    reg = json.loads(REG_PATH.read_text(encoding="utf-8"))
    existing = {m["repo_id"] for m in reg["models"]}
    added = 0
    for s in SPECS:
        if s["repo_id"] in existing: continue
        reg["models"].append({k:v for k,v in s.items() if not k.startswith("_")})
        added += 1
    reg["model_count"] = len(reg["models"])
    REG_PATH.write_text(json.dumps(reg, indent=2), encoding="utf-8")
    REG_LOCAL.write_text(json.dumps(reg, indent=2), encoding="utf-8")
    log(f"registry: +{added}, total {reg['model_count']}")
    api.upload_file(path_or_fileobj=str(REG_PATH), path_in_repo="configs/lumynax_model_registry.json",
                    repo_id="AbteeXAILab/marama-route", repo_type="model", token=TOKEN,
                    commit_message=f"chore(registry): add Pack B frontier round 2 (+{added})")


def main():
    log(f"=== Pack B start === free local: {free_gb():.1f} GB ===")
    for s in SPECS:
        log(f"\n--- scaffold {s['repo_id']}")
        log(f"  scaffold: {build_and_push(s)}")
    update_registry()
    # smallest first
    for s in sorted(SPECS, key=lambda x: x.get("total_params_b") or 0):
        log(f"\n=== mirror {s['repo_id']}  <-  {s['_mirror']['source']}")
        try:
            mirror_files(s["repo_id"], s["_mirror"]["source"], s["_mirror"]["patterns"])
        except Exception as e:
            log(f"  MIRROR FAIL: {e}")
    log("\n=== Pack B end ===")


if __name__ == "__main__":
    main()
