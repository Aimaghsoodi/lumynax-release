"""Verify Pack A upstreams are non-gated and find best GGUF mirrors."""
import os
from huggingface_hub import HfApi
api = HfApi(token=os.environ["HF_TOKEN"])

CANDS = [
    ("openai/whisper-large-v3-turbo", "ASR"),
    ("hexgrad/Kokoro-82M", "TTS"),
    ("BAAI/bge-reranker-v2-m3", "reranker"),
    ("meta-llama/Llama-Guard-3-8B", "safety (likely gated)"),
    ("allenai/wildguard", "safety (alt)"),
    ("google/shieldgemma-9b", "safety (alt)"),
    ("Qwen/Qwen2.5-Math-7B-Instruct", "math"),
    ("facebook/nllb-200-3.3B", "translation"),
    ("deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct", "code MoE"),
    ("NousResearch/Hermes-3-Llama-3.1-8B", "chat"),
]
print(f"{'repo':<55} {'gated':<7} {'private':<8} note")
for r, note in CANDS:
    try:
        info = api.repo_info(r)
        gated = getattr(info, "gated", False) or False
        print(f"{r:<55} {str(gated):<7} {str(info.private):<8} {note}")
    except Exception as e:
        print(f"{r:<55} ERR {str(e)[:60]}")

print()
print("=== GGUF mirror candidates ===")
GGUFS = [
    ("Qwen/Qwen2.5-Math-7B-Instruct",   ["bartowski/Qwen2.5-Math-7B-Instruct-GGUF","mradermacher/Qwen2.5-Math-7B-Instruct-GGUF"]),
    ("deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct", ["bartowski/DeepSeek-Coder-V2-Lite-Instruct-GGUF","unsloth/DeepSeek-Coder-V2-Lite-Instruct-GGUF"]),
    ("NousResearch/Hermes-3-Llama-3.1-8B", ["bartowski/Hermes-3-Llama-3.1-8B-GGUF","NousResearch/Hermes-3-Llama-3.1-8B-GGUF"]),
]
for orig, mirrors in GGUFS:
    print(f"\n{orig}")
    for m in mirrors:
        try:
            info = api.repo_info(m, files_metadata=True)
            q4 = [(s.rfilename, s.size or 0) for s in info.siblings if "q4_k_m" in s.rfilename.lower()]
            if q4:
                print(f"  OK  {m}: {q4[0][0]} ({q4[0][1]/1e9:.2f} GB)")
                break
            else:
                print(f"  ??  {m}: no Q4_K_M")
        except Exception:
            print(f"  --  {m}: missing")
