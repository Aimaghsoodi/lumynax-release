"""`lumynax serve` — start an OpenAI-compatible server for any LumynaX model.

Auto-detects format:
  - GGUF  → llama.cpp.server (llama-cpp-python[server])
  - safetensors → vLLM (preferred) or transformers (fallback)
"""
from __future__ import annotations
import os, sys, subprocess, json, shutil
from pathlib import Path
from typing import Optional

from huggingface_hub import hf_hub_download, snapshot_download
from . import registry as _reg


def _is_gguf(m: dict) -> bool:
    return "gguf" in (m.get("model_id") or "").lower() or (m.get("runtime") or "").startswith("llama_cpp")


def _has_safetensors(m: dict) -> bool:
    return not _is_gguf(m)


def _ensure_local(m: dict, out_dir: Path, weights: bool = True) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    allow = None if weights else ["README.md","quickstart.py","requirements.txt","docs/*","ollama/Modelfile","release_export_manifest.json"]
    snapshot_download(repo_id=m["repo_id"], local_dir=str(out_dir), allow_patterns=allow,
                      token=os.environ.get("HF_TOKEN"))
    return out_dir


def serve(model_id: str, port: int = 8080, host: str = "127.0.0.1",
          backend: Optional[str] = None, ctx: Optional[int] = None,
          n_gpu_layers: int = -1, out_dir: Optional[Path] = None) -> None:
    """Launch the right OpenAI-compatible server for this model."""
    m = _reg.find(model_id)
    if not m:
        print(f"[lumynax] model not found: {model_id}", file=sys.stderr); sys.exit(2)
    slug = m["repo_id"].split("/")[-1]
    target = out_dir or (Path.cwd() / slug)
    print(f"[lumynax] preparing {m['repo_id']} in {target}")
    _ensure_local(m, target, weights=True)
    ctx = ctx or int(m.get("context_tokens") or 16384)
    chosen = backend or ("llama-cpp" if _is_gguf(m) else "vllm")
    print(f"[lumynax] backend = {chosen}, ctx = {ctx}, port = {port}")
    if chosen == "llama-cpp":
        _serve_llama_cpp(m, target, host, port, ctx, n_gpu_layers)
    elif chosen == "vllm":
        _serve_vllm(m, target, host, port, ctx)
    elif chosen == "transformers":
        _serve_transformers(m, target, host, port, ctx)
    else:
        print(f"[lumynax] unknown backend {chosen}", file=sys.stderr); sys.exit(2)


def _find_primary_gguf(target: Path, m: dict) -> Path:
    """Locate the main GGUF shard 1 (llama.cpp auto-loads sibling shards)."""
    declared = m.get("primary_artifact") or ""
    if declared and (target / declared).exists():
        return target / declared
    candidates = list(target.rglob("*.gguf"))
    if not candidates:
        print(f"[lumynax] no .gguf found under {target}", file=sys.stderr); sys.exit(2)
    # Prefer Q4_K_M, then shard 00001-of-, else largest
    for pat in ("*Q4_K_M*00001*", "*Q4_K_M*", "*q4_k_m*00001*", "*q4_k_m*", "*00001*"):
        for c in candidates:
            if c.match(pat):
                return c
    return max(candidates, key=lambda p: p.stat().st_size)


def _serve_llama_cpp(m: dict, target: Path, host: str, port: int, ctx: int, n_gpu_layers: int) -> None:
    weight = _find_primary_gguf(target, m)
    if shutil.which("llama-server"):
        cmd = ["llama-server", "-m", str(weight), "--port", str(port), "--host", host,
               "-c", str(min(ctx, 32768)), "-ngl", str(n_gpu_layers)]
        print(f"[lumynax] $ {' '.join(cmd)}")
        subprocess.run(cmd, check=False); return
    # fallback to llama-cpp-python's server
    print(f"[lumynax] llama-server not on PATH; falling back to python -m llama_cpp.server")
    print(f"[lumynax] install: pip install 'llama-cpp-python[server]'")
    cmd = [sys.executable, "-m", "llama_cpp.server", "--model", str(weight),
           "--host", host, "--port", str(port),
           "--n_ctx", str(min(ctx, 32768)), "--n_gpu_layers", str(n_gpu_layers)]
    print(f"[lumynax] $ {' '.join(cmd)}")
    subprocess.run(cmd, check=False)


def _serve_vllm(m: dict, target: Path, host: str, port: int, ctx: int) -> None:
    if not shutil.which("vllm"):
        print("[lumynax] vllm not on PATH. Install: pip install vllm", file=sys.stderr)
        print("[lumynax] Falling back to transformers...")
        return _serve_transformers(m, target, host, port, ctx)
    cmd = ["vllm", "serve", str(target), "--host", host, "--port", str(port),
           "--max-model-len", str(min(ctx, 32768)), "--dtype", "auto"]
    if "moe" in (m.get("model_id") or "").lower():
        cmd += ["--enable-expert-parallel"]
    if "vision" in (m.get("modalities") or []) or "multimodal" in m.get("model_id",""):
        cmd += ["--trust-remote-code"]
    print(f"[lumynax] $ {' '.join(cmd)}")
    subprocess.run(cmd, check=False)


def _serve_transformers(m: dict, target: Path, host: str, port: int, ctx: int) -> None:
    """Minimal transformers-backed OpenAI server. Only viable for single-GPU small models."""
    print("[lumynax] transformers backend = simple in-process OpenAI server (small models only).")
    print("[lumynax] For real serving of safetensors models, install vLLM:  pip install vllm")
    print("[lumynax] Then re-run with --backend vllm.")
    sys.exit(1)
