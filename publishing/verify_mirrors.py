"""Check that the GGUF mirror repos exist + list their Q4_K_M (or best-available) shards."""
import os
from huggingface_hub import HfApi
api = HfApi(token=os.environ["HF_TOKEN"])

CANDIDATES = [
    ("AbteeXAILab/lumynax-frontier-qwen3-235b-a22b-instruct",     "unsloth/Qwen3-235B-A22B-Instruct-2507-GGUF"),
    ("AbteeXAILab/lumynax-frontier-minimax-m2-230b",              "unsloth/MiniMax-M2-GGUF"),
    ("AbteeXAILab/lumynax-frontier-mixtral-8x22b-instruct-gguf",  "MaziyarPanahi/Mixtral-8x22B-Instruct-v0.1-GGUF"),
    ("AbteeXAILab/lumynax-frontier-dbrx-instruct-132b-gguf",      "PrunaAI/dbrx-instruct-GGUF-smashed"),
    ("AbteeXAILab/lumynax-multimodal-internvl3-78b-instruct",     "OpenGVLab/InternVL3-78B-Instruct"),
    ("AbteeXAILab/lumynax-multimodal-qwen25-vl-72b-instruct-gguf","bartowski/Qwen2.5-VL-72B-Instruct-GGUF"),
    ("AbteeXAILab/lumynax-multimodal-pixtral-large-124b",         "mistralai/Pixtral-Large-Instruct-2411"),
    ("AbteeXAILab/lumynax-reasoning-glm46-355b-moe",              "unsloth/GLM-4.6-GGUF"),
]
# fallback candidates for repos where main mirror may not exist
FALLBACKS = {
    "AbteeXAILab/lumynax-frontier-dbrx-instruct-132b-gguf": [
        "mradermacher/dbrx-instruct-GGUF",
        "mradermacher/dbrx-instruct-i1-GGUF",
        "PrunaAI/dbrx-instruct-GGUF-smashed",
    ],
    "AbteeXAILab/lumynax-multimodal-internvl3-78b-instruct": [
        "OpenGVLab/InternVL3-78B-Instruct",   # safetensors only
    ],
    "AbteeXAILab/lumynax-multimodal-pixtral-large-124b": [
        "mistralai/Pixtral-Large-Instruct-2411",  # safetensors
    ],
}

def info(repo):
    try:
        r = api.repo_info(repo, files_metadata=True)
        weights = [(s.rfilename, s.size or 0) for s in r.siblings
                   if s.rfilename.lower().endswith((".gguf",".safetensors",".bin",".pt"))]
        return weights
    except Exception as e:
        return f"ERR: {type(e).__name__}: {str(e)[:120]}"

def hum(n):
    n=float(n);
    for u in ("B","KB","MB","GB","TB"):
        if n<1024 or u=="TB": return f"{n:6.2f}{u}"
        n/=1024

for dest, src in CANDIDATES:
    print(f"\n--- {dest}")
    r = info(src)
    if isinstance(r, str):
        print(f"  primary mirror MISSING: {src}  ({r})")
        for f in FALLBACKS.get(dest, []):
            r2 = info(f)
            if isinstance(r2, list):
                print(f"  fallback OK: {f} ({len(r2)} weight files)")
                r = r2; src = f
                break
            else:
                print(f"  fallback MISSING: {f}")
        if isinstance(r, str):
            print(f"  >> NO USABLE MIRROR. Manual decision needed.")
            continue
    print(f"  source: {src}  ({len(r)} weight files)")
    # show Q4_K_M-ish files, else top 5 by size
    q4 = [(n,s) for n,s in r if "q4_k_m" in n.lower() or "q4km" in n.lower()]
    if q4:
        total = sum(s for _,s in q4)
        print(f"  Q4_K_M shards: {len(q4)} files, total {hum(total)}")
        for n,s in sorted(q4)[:6]: print(f"    {hum(s):>10}  {n}")
        if len(q4) > 6: print(f"    ... +{len(q4)-6} more")
    else:
        print(f"  no Q4_K_M matched. Top files by size:")
        for n,s in sorted(r, key=lambda x: -x[1])[:6]: print(f"    {hum(s):>10}  {n}")
