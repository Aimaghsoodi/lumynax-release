"""Check QwQ-32B and Phi-4 GGUF mirrors."""
import os
from huggingface_hub import HfApi
api = HfApi(token=os.environ["HF_TOKEN"])
for r in ["bartowski/QwQ-32B-GGUF","bartowski/phi-4-GGUF","mradermacher/QwQ-32B-GGUF","unsloth/QwQ-32B-GGUF","unsloth/phi-4-GGUF","Qwen/QwQ-32B-GGUF","microsoft/phi-4-gguf"]:
    try:
        info = api.repo_info(r, files_metadata=True)
        q4 = [(s.rfilename, s.size or 0) for s in info.siblings if "q4_k_m" in s.rfilename.lower()]
        if q4:
            print(f"OK  {r}: {q4[0][0]} ({q4[0][1]/1e9:.2f} GB)")
        else:
            print(f"??  {r}: no Q4_K_M")
    except Exception:
        print(f"--  {r}: missing")
