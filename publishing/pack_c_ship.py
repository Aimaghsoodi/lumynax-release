"""
Pack C — Document & Retrieval Stack (8 models).
OCR + doc-understanding + layout + table + modern embedders.
"""
from __future__ import annotations
import json, os, sys, time
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, r"S:\hf-publish")
from huggingface_hub import HfApi
import generate_cards_v6 as G
from add_8_more_models import build_and_push
from pack_a_ship import mirror_files, log as _log, free_gb, hum

TOKEN = os.environ["HF_TOKEN"]
api = HfApi(token=TOKEN)
LOG = Path(r"S:\hf-publish\pack_c_progress.log")
REG_PATH = G.REGISTRY_PATH
REG_LOCAL = Path(r"S:\hf-publish\marama-route\configs\lumynax_model_registry.json")

def log(m: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    LOG.open("a", encoding="utf-8").write(line + "\n")

SPECS: List[Dict[str, Any]] = [
    {
        "model_id": "lumynax-doc-nougat-base", "repo_id": "AbteeXAILab/lumynax-doc-nougat-base",
        "title": "LumynaX Doc Nougat Base (academic PDF -> markdown)",
        "family": "nougat", "runtime": "transformers", "modalities": ["text","vision"],
        "context_tokens": 4096, "jurisdiction": "NZ", "residency": ["NZ","AU","global"],
        "license_id": "cc-by-4.0", "quantization": "fp32 safetensors",
        "primary_artifact": "model.safetensors",
        "active_params_b": None, "total_params_b": 0.35,
        "quality_rank": 2, "cost_rank": 1, "sovereignty_tier": 3,
        "supports_tools": False, "supports_json": True,
        "tags": ["doc-ai","ocr","nougat","pdf","markdown"],
        "metadata": {"upstream_repo":"facebook/nougat-base","release_version":"v0.1.0","package_state":"weights_mirrored","public_status":"public and non-gated","validation_status":"scaffold_verified"},
        "_upstream": ("facebook/nougat-base","cc-by-4.0","nougat","Meta Nougat"),
        "_kind": "transformers_text", "_gguf_mirror": None,
        "_mirror": {"source":"facebook/nougat-base","patterns":["*.safetensors","*.bin","config.json","tokenizer*","preprocessor_config.json","special_tokens_map.json","generation_config.json"]},
    },
    {
        "model_id": "lumynax-doc-donut-base", "repo_id": "AbteeXAILab/lumynax-doc-donut-base",
        "title": "LumynaX Doc Donut Base (document understanding)",
        "family": "donut", "runtime": "transformers", "modalities": ["text","vision"],
        "context_tokens": 1536, "jurisdiction": "NZ", "residency": ["NZ","AU","global"],
        "license_id": "mit", "quantization": "fp32 safetensors",
        "primary_artifact": "model.safetensors",
        "active_params_b": None, "total_params_b": 0.2,
        "quality_rank": 2, "cost_rank": 1, "sovereignty_tier": 3,
        "supports_tools": False, "supports_json": True,
        "tags": ["doc-ai","donut","document-vqa"],
        "metadata": {"upstream_repo":"naver-clova-ix/donut-base","release_version":"v0.1.0","package_state":"weights_mirrored","public_status":"public and non-gated","validation_status":"scaffold_verified"},
        "_upstream": ("naver-clova-ix/donut-base","mit","donut","NAVER Donut"),
        "_kind": "transformers_text", "_gguf_mirror": None,
        "_mirror": {"source":"naver-clova-ix/donut-base","patterns":["*.safetensors","*.bin","config.json","tokenizer*","preprocessor_config.json","special_tokens_map.json","generation_config.json","added_tokens.json","sentencepiece*"]},
    },
    {
        "model_id": "lumynax-ocr-trocr-large-printed", "repo_id": "AbteeXAILab/lumynax-ocr-trocr-large-printed",
        "title": "LumynaX OCR TrOCR Large Printed",
        "family": "trocr", "runtime": "transformers", "modalities": ["text","vision"],
        "context_tokens": 512, "jurisdiction": "NZ", "residency": ["NZ","AU","global"],
        "license_id": "mit", "quantization": "fp32 safetensors",
        "primary_artifact": "model.safetensors",
        "active_params_b": None, "total_params_b": 0.55,
        "quality_rank": 2, "cost_rank": 2, "sovereignty_tier": 3,
        "supports_tools": False, "supports_json": False,
        "tags": ["ocr","printed","trocr"],
        "metadata": {"upstream_repo":"microsoft/trocr-large-printed","release_version":"v0.1.0","package_state":"weights_mirrored","public_status":"public and non-gated","validation_status":"scaffold_verified"},
        "_upstream": ("microsoft/trocr-large-printed","mit","trocr","Microsoft TrOCR"),
        "_kind": "transformers_text", "_gguf_mirror": None,
        "_mirror": {"source":"microsoft/trocr-large-printed","patterns":["*.safetensors","*.bin","config.json","tokenizer*","preprocessor_config.json","special_tokens_map.json","generation_config.json","added_tokens.json","sentencepiece*","vocab.json","merges.txt"]},
    },
    {
        "model_id": "lumynax-ocr-trocr-large-handwritten", "repo_id": "AbteeXAILab/lumynax-ocr-trocr-large-handwritten",
        "title": "LumynaX OCR TrOCR Large Handwritten",
        "family": "trocr", "runtime": "transformers", "modalities": ["text","vision"],
        "context_tokens": 512, "jurisdiction": "NZ", "residency": ["NZ","AU","global"],
        "license_id": "mit", "quantization": "fp32 safetensors",
        "primary_artifact": "model.safetensors",
        "active_params_b": None, "total_params_b": 0.55,
        "quality_rank": 2, "cost_rank": 2, "sovereignty_tier": 3,
        "supports_tools": False, "supports_json": False,
        "tags": ["ocr","handwritten","trocr"],
        "metadata": {"upstream_repo":"microsoft/trocr-large-handwritten","release_version":"v0.1.0","package_state":"weights_mirrored","public_status":"public and non-gated","validation_status":"scaffold_verified"},
        "_upstream": ("microsoft/trocr-large-handwritten","mit","trocr","Microsoft TrOCR"),
        "_kind": "transformers_text", "_gguf_mirror": None,
        "_mirror": {"source":"microsoft/trocr-large-handwritten","patterns":["*.safetensors","*.bin","config.json","tokenizer*","preprocessor_config.json","special_tokens_map.json","generation_config.json","added_tokens.json","sentencepiece*","vocab.json","merges.txt"]},
    },
    {
        "model_id": "lumynax-doc-layoutlmv3-base", "repo_id": "AbteeXAILab/lumynax-doc-layoutlmv3-base",
        "title": "LumynaX Doc LayoutLMv3 Base (document layout+text)",
        "family": "layoutlm", "runtime": "transformers", "modalities": ["text","vision"],
        "context_tokens": 512, "jurisdiction": "NZ", "residency": ["NZ","AU","global"],
        "license_id": "cc-by-nc-4.0", "quantization": "fp32 safetensors",
        "primary_artifact": "model.safetensors",
        "active_params_b": None, "total_params_b": 0.13,
        "quality_rank": 2, "cost_rank": 1, "sovereignty_tier": 3,
        "supports_tools": False, "supports_json": True,
        "tags": ["doc-ai","layout","layoutlm"],
        "metadata": {"upstream_repo":"microsoft/layoutlmv3-base","release_version":"v0.1.0","package_state":"weights_mirrored","public_status":"public and non-gated","validation_status":"scaffold_verified"},
        "_upstream": ("microsoft/layoutlmv3-base","cc-by-nc-4.0","layoutlm","Microsoft LayoutLMv3"),
        "_kind": "transformers_text", "_gguf_mirror": None,
        "_mirror": {"source":"microsoft/layoutlmv3-base","patterns":["*.safetensors","*.bin","config.json","tokenizer*","preprocessor_config.json","special_tokens_map.json","added_tokens.json","vocab.json","merges.txt","sentencepiece*"]},
    },
    {
        "model_id": "lumynax-doc-table-transformer-detection", "repo_id": "AbteeXAILab/lumynax-doc-table-transformer-detection",
        "title": "LumynaX Doc Table Transformer (detection)",
        "family": "table-transformer", "runtime": "transformers", "modalities": ["vision"],
        "context_tokens": 0, "jurisdiction": "NZ", "residency": ["NZ","AU","global"],
        "license_id": "mit", "quantization": "fp32 safetensors",
        "primary_artifact": "model.safetensors",
        "active_params_b": None, "total_params_b": 0.029,
        "quality_rank": 2, "cost_rank": 1, "sovereignty_tier": 3,
        "supports_tools": False, "supports_json": True,
        "tags": ["doc-ai","tables","detection","detr"],
        "metadata": {"upstream_repo":"microsoft/table-transformer-detection","release_version":"v0.1.0","package_state":"weights_mirrored","public_status":"public and non-gated","validation_status":"scaffold_verified"},
        "_upstream": ("microsoft/table-transformer-detection","mit","detr","Microsoft Table Transformer"),
        "_kind": "transformers_text", "_gguf_mirror": None,
        "_mirror": {"source":"microsoft/table-transformer-detection","patterns":["*.safetensors","*.bin","config.json","preprocessor_config.json"]},
    },
    {
        "model_id": "lumynax-embed-nomic-v2-moe", "repo_id": "AbteeXAILab/lumynax-embed-nomic-v2-moe",
        "title": "LumynaX Embed Nomic v2 MoE (modern retrieval)",
        "family": "nomic", "runtime": "python_embedding", "modalities": ["text"],
        "context_tokens": 512, "jurisdiction": "NZ", "residency": ["NZ","AU","global"],
        "license_id": "apache-2.0", "quantization": "fp32 safetensors",
        "primary_artifact": "model.safetensors",
        "active_params_b": 0.305, "total_params_b": 0.475,
        "quality_rank": 1, "cost_rank": 1, "sovereignty_tier": 3,
        "supports_tools": False, "supports_json": True,
        "tags": ["embedding","retrieval","nomic","moe","modern"],
        "metadata": {"upstream_repo":"nomic-ai/nomic-embed-text-v2-moe","release_version":"v0.1.0","package_state":"weights_mirrored","public_status":"public and non-gated","validation_status":"scaffold_verified"},
        "_upstream": ("nomic-ai/nomic-embed-text-v2-moe","apache-2.0","embedding","Nomic Embed v2 MoE"),
        "_kind": "transformers_text", "_gguf_mirror": None,
        "_mirror": {"source":"nomic-ai/nomic-embed-text-v2-moe","patterns":["*.safetensors","*.bin","config.json","tokenizer*","sentencepiece*","special_tokens_map.json","modules.json","1_Pooling/*","sentence_bert_config.json","configuration*.py","modeling*.py"]},
    },
    {
        "model_id": "lumynax-embed-granite-278m-multilingual", "repo_id": "AbteeXAILab/lumynax-embed-granite-278m-multilingual",
        "title": "LumynaX Embed IBM Granite 278M Multilingual",
        "family": "granite", "runtime": "python_embedding", "modalities": ["text"],
        "context_tokens": 512, "jurisdiction": "NZ", "residency": ["NZ","AU","global"],
        "license_id": "apache-2.0", "quantization": "fp32 safetensors",
        "primary_artifact": "model.safetensors",
        "active_params_b": None, "total_params_b": 0.278,
        "quality_rank": 2, "cost_rank": 1, "sovereignty_tier": 3,
        "supports_tools": False, "supports_json": True,
        "tags": ["embedding","retrieval","granite","multilingual","ibm"],
        "metadata": {"upstream_repo":"ibm-granite/granite-embedding-278m-multilingual","release_version":"v0.1.0","package_state":"weights_mirrored","public_status":"public and non-gated","validation_status":"scaffold_verified"},
        "_upstream": ("ibm-granite/granite-embedding-278m-multilingual","apache-2.0","embedding","IBM Granite Embed"),
        "_kind": "transformers_text", "_gguf_mirror": None,
        "_mirror": {"source":"ibm-granite/granite-embedding-278m-multilingual","patterns":["*.safetensors","*.bin","config.json","tokenizer*","sentencepiece*","special_tokens_map.json","modules.json","1_Pooling/*","sentence_bert_config.json"]},
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
                    commit_message=f"chore(registry): add Pack C document & retrieval stack (+{added})")


def main():
    log(f"=== Pack C start === free local: {free_gb():.1f} GB ===")
    for s in SPECS:
        log(f"\n--- scaffold {s['repo_id']}")
        log(f"  scaffold: {build_and_push(s)}")
    update_registry()
    for s in sorted(SPECS, key=lambda x: x.get("total_params_b") or 0):
        log(f"\n=== mirror {s['repo_id']}  <-  {s['_mirror']['source']}")
        try:
            mirror_files(s["repo_id"], s["_mirror"]["source"], s["_mirror"]["patterns"])
        except Exception as e:
            log(f"  MIRROR FAIL: {e}")
    log("\n=== Pack C end ===")


if __name__ == "__main__":
    main()
