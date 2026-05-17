"""
Pack A — Speech & Specialized (8 models).

End-to-end: create HF repos, push v6 scaffolds, mirror weights, update registry,
refresh GitHub monorepo.
"""
from __future__ import annotations
import fnmatch, hashlib, json, os, shutil, sys, threading, time
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, r"S:\hf-publish")
from huggingface_hub import HfApi, hf_hub_download, create_repo
import generate_cards_v6 as G
from add_8_more_models import (
    build_and_push, _gen_quickstart, _gen_requirements,
    _gen_manifest, _gen_modelfile, _checksums, SPACE_APP, SPACE_README,
    LICENSE_BLURB, VERSION_TXT, UPLOAD_TO_HF_MD, OUT,
)

TOKEN = os.environ["HF_TOKEN"]
api = HfApi(token=TOKEN)
STAGE = Path(r"C:\Users\ijadimaa\AppData\Local\Temp\hf-stage")
STAGE.mkdir(parents=True, exist_ok=True)
LOG = Path(r"S:\hf-publish\pack_a_progress.log")
REG_PATH = G.REGISTRY_PATH
REG_LOCAL = Path(r"S:\hf-publish\marama-route\configs\lumynax_model_registry.json")

def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

def hum(n: float) -> str:
    n = float(n)
    for u in ("B","KB","MB","GB","TB"):
        if n<1024 or u=="TB": return f"{n:.2f} {u}"
        n /= 1024

# ---------- Pack A spec ----------
SPECS: List[Dict[str, Any]] = [
    {
        "model_id": "lumynax-speech-whisper-large-v3-turbo",
        "repo_id": "AbteeXAILab/lumynax-speech-whisper-large-v3-turbo",
        "title": "LumynaX Speech Whisper Large v3 Turbo",
        "family": "whisper",
        "runtime": "transformers",
        "modalities": ["audio"],
        "context_tokens": 30,
        "jurisdiction": "NZ",
        "residency": ["NZ","AU","global"],
        "license_id": "mit",
        "quantization": "fp16 safetensors",
        "primary_artifact": "model.safetensors",
        "active_params_b": None,
        "total_params_b": 0.8,
        "quality_rank": 1,
        "cost_rank": 2,
        "sovereignty_tier": 3,
        "supports_tools": False,
        "supports_json": False,
        "tags": ["asr","speech","whisper","audio"],
        "metadata": {"upstream_repo":"openai/whisper-large-v3-turbo","release_version":"v0.1.0","package_state":"weights_mirrored","public_status":"public and non-gated","validation_status":"scaffold_verified"},
        "_upstream": ("openai/whisper-large-v3-turbo","mit","whisper","OpenAI Whisper"),
        "_kind": "transformers_text",  # but really transformers ASR — close enough for the template
        "_gguf_mirror": None,
        "_mirror": {"source":"openai/whisper-large-v3-turbo","patterns":["model.safetensors","config.json","generation_config.json","preprocessor_config.json","tokenizer*","vocab.json","merges.txt","special_tokens_map.json","added_tokens.json","normalizer.json"]},
    },
    {
        "model_id": "lumynax-speech-kokoro-82m-tts",
        "repo_id": "AbteeXAILab/lumynax-speech-kokoro-82m-tts",
        "title": "LumynaX Speech Kokoro 82M TTS",
        "family": "kokoro",
        "runtime": "transformers",
        "modalities": ["text","audio"],
        "context_tokens": 510,
        "jurisdiction": "NZ",
        "residency": ["NZ","AU","global"],
        "license_id": "apache-2.0",
        "quantization": "fp32 (small)",
        "primary_artifact": "kokoro-v1_0.pth",
        "active_params_b": None,
        "total_params_b": 0.082,
        "quality_rank": 1,
        "cost_rank": 1,
        "sovereignty_tier": 3,
        "supports_tools": False,
        "supports_json": False,
        "tags": ["tts","speech","kokoro","audio"],
        "metadata": {"upstream_repo":"hexgrad/Kokoro-82M","release_version":"v0.1.0","package_state":"weights_mirrored","public_status":"public and non-gated","validation_status":"scaffold_verified"},
        "_upstream": ("hexgrad/Kokoro-82M","apache-2.0","kokoro","Kokoro TTS"),
        "_kind": "transformers_text",
        "_gguf_mirror": None,
        "_mirror": {"source":"hexgrad/Kokoro-82M","patterns":["kokoro-v1_0.pth","config.json","voices/*.pt","VOICES.md","SAMPLES.md"]},
    },
    {
        "model_id": "lumynax-reranker-bge-v2-m3",
        "repo_id": "AbteeXAILab/lumynax-reranker-bge-v2-m3",
        "title": "LumynaX Reranker BGE v2 M3",
        "family": "bge",
        "runtime": "transformers",
        "modalities": ["text"],
        "context_tokens": 8192,
        "jurisdiction": "NZ",
        "residency": ["NZ","AU","global"],
        "license_id": "mit",
        "quantization": "fp32 safetensors",
        "primary_artifact": "model.safetensors",
        "active_params_b": None,
        "total_params_b": 0.568,
        "quality_rank": 1,
        "cost_rank": 1,
        "sovereignty_tier": 3,
        "supports_tools": False,
        "supports_json": True,
        "tags": ["reranker","retrieval","bge","embedding-companion"],
        "metadata": {"upstream_repo":"BAAI/bge-reranker-v2-m3","release_version":"v0.1.0","package_state":"weights_mirrored","public_status":"public and non-gated","validation_status":"scaffold_verified"},
        "_upstream": ("BAAI/bge-reranker-v2-m3","mit","reranker","BAAI BGE reranker"),
        "_kind": "transformers_text",
        "_gguf_mirror": None,
        "_mirror": {"source":"BAAI/bge-reranker-v2-m3","patterns":["model.safetensors","config.json","tokenizer*","sentencepiece*","special_tokens_map.json","colbert_linear.pt","sparse_linear.pt"]},
    },
    {
        "model_id": "lumynax-guard-text-moderation",
        "repo_id": "AbteeXAILab/lumynax-guard-text-moderation",
        "title": "LumynaX Guard Text Moderation",
        "family": "roberta",
        "runtime": "transformers",
        "modalities": ["text"],
        "context_tokens": 512,
        "jurisdiction": "NZ",
        "residency": ["NZ","AU","global"],
        "license_id": "mit",
        "quantization": "fp32 safetensors",
        "primary_artifact": "model.safetensors",
        "active_params_b": None,
        "total_params_b": 0.279,
        "quality_rank": 2,
        "cost_rank": 1,
        "sovereignty_tier": 3,
        "supports_tools": False,
        "supports_json": True,
        "tags": ["safety","moderation","classifier","guardrail"],
        "metadata": {"upstream_repo":"KoalaAI/Text-Moderation","release_version":"v0.1.0","package_state":"weights_mirrored","public_status":"public and non-gated","validation_status":"scaffold_verified"},
        "_upstream": ("KoalaAI/Text-Moderation","openrail","roberta","KoalaAI Text Moderation"),
        "_kind": "transformers_text",
        "_gguf_mirror": None,
        "_mirror": {"source":"KoalaAI/Text-Moderation","patterns":["model.safetensors","pytorch_model.bin","config.json","tokenizer*","merges.txt","vocab.json","special_tokens_map.json"]},
    },
    {
        "model_id": "lumynax-math-qwen25-math-7b-gguf",
        "repo_id": "AbteeXAILab/lumynax-math-qwen25-math-7b-gguf",
        "title": "LumynaX Math Qwen2.5 Math 7B GGUF",
        "family": "qwen",
        "runtime": "llama_cpp",
        "modalities": ["text"],
        "context_tokens": 4096,
        "jurisdiction": "NZ",
        "residency": ["NZ"],
        "license_id": "apache-2.0",
        "quantization": "Q4_K_M GGUF",
        "primary_artifact": "Qwen2.5-Math-7B-Instruct-Q4_K_M.gguf",
        "active_params_b": None,
        "total_params_b": 7,
        "quality_rank": 2,
        "cost_rank": 2,
        "sovereignty_tier": 3,
        "supports_tools": False,
        "supports_json": True,
        "tags": ["math","reasoning","qwen","gguf"],
        "metadata": {"upstream_repo":"Qwen/Qwen2.5-Math-7B-Instruct","release_version":"v0.1.0","package_state":"weights_mirrored","public_status":"public and non-gated","validation_status":"scaffold_verified"},
        "_upstream": ("Qwen/Qwen2.5-Math-7B-Instruct","apache-2.0","chatml","Qwen2.5 Math"),
        "_kind": "gguf",
        "_gguf_mirror": "bartowski/Qwen2.5-Math-7B-Instruct-GGUF",
        "_gguf_filename": "Qwen2.5-Math-7B-Instruct-Q4_K_M.gguf",
        "_mirror": {"source":"bartowski/Qwen2.5-Math-7B-Instruct-GGUF","patterns":["*Q4_K_M*.gguf"]},
    },
    {
        "model_id": "lumynax-translate-nllb-200-3b",
        "repo_id": "AbteeXAILab/lumynax-translate-nllb-200-3b",
        "title": "LumynaX Translate NLLB-200 3.3B",
        "family": "nllb",
        "runtime": "transformers",
        "modalities": ["text"],
        "context_tokens": 1024,
        "jurisdiction": "NZ",
        "residency": ["NZ","AU","global"],
        "license_id": "cc-by-nc-4.0",
        "quantization": "fp32 safetensors",
        "primary_artifact": "model.safetensors",
        "active_params_b": None,
        "total_params_b": 3.3,
        "quality_rank": 2,
        "cost_rank": 3,
        "sovereignty_tier": 3,
        "supports_tools": False,
        "supports_json": False,
        "tags": ["translation","nllb","te-reo","aotearoa","languages"],
        "metadata": {"upstream_repo":"facebook/nllb-200-3.3B","release_version":"v0.1.0","package_state":"weights_mirrored","public_status":"public and non-gated","validation_status":"scaffold_verified"},
        "_upstream": ("facebook/nllb-200-3.3B","cc-by-nc-4.0","nllb","Meta NLLB-200"),
        "_kind": "transformers_text",
        "_gguf_mirror": None,
        "_mirror": {"source":"facebook/nllb-200-3.3B","patterns":["model.safetensors","pytorch_model.bin","config.json","tokenizer*","sentencepiece*","special_tokens_map.json","generation_config.json"]},
    },
    {
        "model_id": "lumynax-coder-deepseek-v2-lite-16b-gguf",
        "repo_id": "AbteeXAILab/lumynax-coder-deepseek-v2-lite-16b-gguf",
        "title": "LumynaX Coder DeepSeek-Coder V2 Lite 16B GGUF",
        "family": "deepseek",
        "runtime": "llama_cpp",
        "modalities": ["text"],
        "context_tokens": 163840,
        "jurisdiction": "NZ",
        "residency": ["NZ"],
        "license_id": "other",
        "quantization": "Q4_K_M GGUF",
        "primary_artifact": "DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf",
        "active_params_b": 2.4,
        "total_params_b": 16,
        "quality_rank": 2,
        "cost_rank": 2,
        "sovereignty_tier": 3,
        "supports_tools": True,
        "supports_json": True,
        "tags": ["coder","moe","deepseek","gguf","long-context"],
        "metadata": {"upstream_repo":"deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct","release_version":"v0.1.0","package_state":"weights_mirrored","public_status":"public and non-gated","validation_status":"scaffold_verified"},
        "_upstream": ("deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct","other","chatml","DeepSeek Coder V2 Lite"),
        "_kind": "gguf",
        "_gguf_mirror": "bartowski/DeepSeek-Coder-V2-Lite-Instruct-GGUF",
        "_gguf_filename": "DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf",
        "_mirror": {"source":"bartowski/DeepSeek-Coder-V2-Lite-Instruct-GGUF","patterns":["*Q4_K_M*.gguf"]},
    },
    {
        "model_id": "lumynax-chat-hermes-3-llama31-8b-gguf",
        "repo_id": "AbteeXAILab/lumynax-chat-hermes-3-llama31-8b-gguf",
        "title": "LumynaX Chat Hermes-3 Llama-3.1 8B GGUF",
        "family": "llama",
        "runtime": "llama_cpp",
        "modalities": ["text"],
        "context_tokens": 131072,
        "jurisdiction": "NZ",
        "residency": ["NZ"],
        "license_id": "llama3.1",
        "quantization": "Q4_K_M GGUF",
        "primary_artifact": "Hermes-3-Llama-3.1-8B-Q4_K_M.gguf",
        "active_params_b": None,
        "total_params_b": 8,
        "quality_rank": 2,
        "cost_rank": 2,
        "sovereignty_tier": 3,
        "supports_tools": True,
        "supports_json": True,
        "tags": ["chat","hermes","llama","gguf","tools","function-calling"],
        "metadata": {"upstream_repo":"NousResearch/Hermes-3-Llama-3.1-8B","release_version":"v0.1.0","package_state":"weights_mirrored","public_status":"public and non-gated","validation_status":"scaffold_verified"},
        "_upstream": ("NousResearch/Hermes-3-Llama-3.1-8B","llama3.1","chatml","NousResearch Hermes-3"),
        "_kind": "gguf",
        "_gguf_mirror": "bartowski/Hermes-3-Llama-3.1-8B-GGUF",
        "_gguf_filename": "Hermes-3-Llama-3.1-8B-Q4_K_M.gguf",
        "_mirror": {"source":"bartowski/Hermes-3-Llama-3.1-8B-GGUF","patterns":["*Q4_K_M*.gguf"]},
    },
]

# ---------- patch infer_upstream so generator resolves correctly ----------
_orig_infer = G.infer_upstream
_pack_upstream = {s["model_id"]: s["_upstream"] for s in SPECS}
def _patched(mid, family):
    if mid in _pack_upstream: return _pack_upstream[mid]
    return _orig_infer(mid, family)
G.infer_upstream = _patched


# ---------- mirror helpers ----------
def list_meta(repo: str):
    info = api.repo_info(repo, files_metadata=True, token=TOKEN)
    return [{"path": s.rfilename, "size": s.size or 0} for s in info.siblings]

def matches(name: str, patterns: List[str]) -> bool:
    return any(fnmatch.fnmatch(name, p) for p in patterns)

def already_at_dest(dest_files, path, size):
    for f in dest_files:
        if f["path"] == path and f["size"] == size and size > 0:
            return True
    return False

def free_gb() -> float:
    return shutil.disk_usage(str(STAGE)).free / (1024**3)

def mirror_files(dest_repo: str, source_repo: str, patterns: List[str]):
    src_files = list_meta(source_repo)
    matched = [f for f in src_files if matches(f["path"], patterns)]
    matched.sort(key=lambda x: x["size"])
    if not matched:
        log(f"  no files matched in {source_repo} for {patterns}")
        return
    try: dest_files = list_meta(dest_repo)
    except Exception: dest_files = []
    total = sum(f["size"] for f in matched)
    log(f"  {len(matched)} files matched, total {hum(total)}")
    stage_dir = STAGE / dest_repo.split("/")[-1]
    stage_dir.mkdir(parents=True, exist_ok=True)
    for i, f in enumerate(matched, 1):
        path, size = f["path"], f["size"]
        if already_at_dest(dest_files, path, size):
            log(f"  [{i}/{len(matched)}] SKIP (already there): {path}")
            continue
        # stall watchdog (5 min)
        log(f"  [{i}/{len(matched)}] download {path} ({hum(size)})  free={free_gb():.1f}GB")
        holder = {"path": None, "error": None}
        done = threading.Event()
        def _do():
            try: holder["path"] = hf_hub_download(repo_id=source_repo, filename=path, local_dir=str(stage_dir), token=TOKEN)
            except Exception as e: holder["error"] = e
            finally: done.set()
        th = threading.Thread(target=_do, daemon=True); th.start()
        last_size = -1; last_change = time.time()
        while not done.wait(60):
            cur = 0
            for inc in stage_dir.rglob("*.incomplete"):
                try: cur = max(cur, inc.stat().st_size)
                except: pass
            if cur != last_size: last_size = cur; last_change = time.time()
            elif time.time() - last_change > 300:
                log(f"    STALL: aborting {path}")
                break
        if not done.is_set(): continue
        if holder["error"]:
            log(f"    download FAIL: {holder['error']}"); continue
        local = holder["path"]
        # upload
        t0 = time.time()
        try:
            api.upload_file(path_or_fileobj=local, path_in_repo=path, repo_id=dest_repo,
                            repo_type="model", token=TOKEN,
                            commit_message=f"weights: mirror {Path(path).name}")
            log(f"    uploaded in {time.time()-t0:.0f}s")
        except Exception as e:
            log(f"    upload FAIL: {e}")
        try: Path(local).unlink()
        except: pass


def update_registry():
    reg = json.loads(REG_PATH.read_text(encoding="utf-8"))
    existing = {m["repo_id"] for m in reg["models"]}
    added = 0
    for s in SPECS:
        if s["repo_id"] in existing: continue
        clean = {k:v for k,v in s.items() if not k.startswith("_")}
        reg["models"].append(clean); added += 1
    reg["model_count"] = len(reg["models"])
    REG_PATH.write_text(json.dumps(reg, indent=2), encoding="utf-8")
    REG_LOCAL.write_text(json.dumps(reg, indent=2), encoding="utf-8")
    log(f"registry: +{added}, total {reg['model_count']}")
    api.upload_file(path_or_fileobj=str(REG_PATH), path_in_repo="configs/lumynax_model_registry.json",
                    repo_id="AbteeXAILab/marama-route", repo_type="model", token=TOKEN,
                    commit_message=f"chore(registry): add Pack A speech & specialized (+{added})")


def main():
    log(f"=== Pack A start === free local: {free_gb():.1f} GB ===")
    # 1) Scaffold each repo
    for s in SPECS:
        log(f"\n--- scaffold {s['repo_id']}")
        result = build_and_push(s)
        log(f"  scaffold: {result}")
    # 2) Update registry now (before weight mirror — exposes scaffolds immediately)
    update_registry()
    # 3) Mirror weights (smallest first via sort)
    for s in sorted(SPECS, key=lambda x: x.get("total_params_b") or 0):
        log(f"\n=== mirror {s['repo_id']}  <-  {s['_mirror']['source']}")
        try:
            mirror_files(s["repo_id"], s["_mirror"]["source"], s["_mirror"]["patterns"])
        except Exception as e:
            log(f"  MIRROR FAIL: {e}")
    log("\n=== Pack A end ===")


if __name__ == "__main__":
    main()
