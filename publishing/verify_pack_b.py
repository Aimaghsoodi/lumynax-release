"""Verify Pack B (Frontier Round 2) non-gated + GGUF mirrors."""
import os
from huggingface_hub import HfApi
api = HfApi(token=os.environ["HF_TOKEN"])

CANDS = [
    ("Qwen/Qwen2.5-72B-Instruct", "frontier dense"),
    ("CohereForAI/c4ai-command-r-plus-08-2024", "tool-use 104B"),
    ("allenai/OLMo-2-1124-32B-Instruct", "fully-open 32B"),
    ("01-ai/Yi-1.5-34B-Chat", "multilingual 34B"),
    ("internlm/internlm3-8b-instruct", "newer reasoning"),
    ("rhymes-ai/Aria", "MoE multimodal"),
    ("allenai/Molmo-72B-0924", "pure-vision 72B"),
    ("openbmb/MiniCPM-V-2_6", "efficient multimodal"),
]
for r, note in CANDS:
    try:
        info = api.repo_info(r, files_metadata=True)
        sz = sum(s.size or 0 for s in info.siblings if s.rfilename.lower().endswith((".safetensors",".bin")))
        gated = getattr(info, "gated", False)
        print(f"{r:<55} gated={str(gated):<8} {sz/1e9:>5.1f} GB  {note}")
    except Exception as e:
        print(f"{r:<55} ERR {str(e)[:60]}")

print()
print("=== GGUF Q4_K_M mirrors ===")
GGUFS = {
    "Qwen/Qwen2.5-72B-Instruct":            ["bartowski/Qwen2.5-72B-Instruct-GGUF","unsloth/Qwen2.5-72B-Instruct-GGUF","Qwen/Qwen2.5-72B-Instruct-GGUF"],
    "CohereForAI/c4ai-command-r-plus-08-2024":["bartowski/c4ai-command-r-plus-08-2024-GGUF","CohereForAI/c4ai-command-r-plus-08-2024-GGUF"],
    "allenai/OLMo-2-1124-32B-Instruct":      ["bartowski/OLMo-2-1124-32B-Instruct-GGUF","mradermacher/OLMo-2-1124-32B-Instruct-GGUF"],
    "01-ai/Yi-1.5-34B-Chat":                  ["bartowski/Yi-1.5-34B-Chat-GGUF","mradermacher/Yi-1.5-34B-Chat-GGUF","01-ai/Yi-1.5-34B-Chat-GGUF"],
    "internlm/internlm3-8b-instruct":         ["bartowski/internlm3-8b-instruct-GGUF","mradermacher/internlm3-8b-instruct-GGUF"],
    "openbmb/MiniCPM-V-2_6":                  ["openbmb/MiniCPM-V-2_6-gguf","ggml-org/MiniCPM-V-2_6-gguf","second-state/MiniCPM-V-2_6-gguf"],
}
for orig, mirrors in GGUFS.items():
    print(f"\n{orig}")
    for m in mirrors:
        try:
            info = api.repo_info(m, files_metadata=True)
            q4 = [(s.rfilename, s.size or 0) for s in info.siblings if "q4_k_m" in s.rfilename.lower()]
            if q4:
                total = sum(s for _,s in q4)
                names = [n for n,_ in sorted(q4)]
                print(f"  OK  {m}: {len(q4)} Q4_K_M file(s), total {total/1e9:.1f} GB")
                for n in names[:4]: print(f"      {n}")
                break
            else:
                print(f"  ??  {m}: no Q4_K_M")
        except Exception:
            print(f"  --  {m}: missing")
