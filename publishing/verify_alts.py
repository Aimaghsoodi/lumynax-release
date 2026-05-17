import os
from huggingface_hub import HfApi
api = HfApi(token=os.environ["HF_TOKEN"])

# Pixtral gating check
def gated(repo):
    try:
        r = api.repo_info(repo)
        return f"gated={getattr(r,'gated',None)}, private={r.private}"
    except Exception as e:
        return f"ERR: {str(e)[:120]}"

print("Pixtral-Large status:")
print(" ", gated("mistralai/Pixtral-Large-Instruct-2411"))
print("Pixtral-12B status:")
print(" ", gated("mistralai/Pixtral-12B-2409"))
print("Molmo-72B status:")
print(" ", gated("allenai/Molmo-72B-0924"))
print("NVLM-D-72B status:")
print(" ", gated("nvidia/NVLM-D-72B"))
print("Qwen2-VL-72B status:")
print(" ", gated("Qwen/Qwen2-VL-72B-Instruct"))

print()
print("Candidate GGUF mirrors for Qwen2.5-VL-72B:")
for r in ["mradermacher/Qwen2.5-VL-72B-Instruct-GGUF",
          "unsloth/Qwen2.5-VL-72B-Instruct-GGUF",
          "ggml-org/Qwen2.5-VL-72B-Instruct-GGUF",
          "Mungert/Qwen2.5-VL-72B-Instruct-GGUF",
          "second-state/Qwen2.5-VL-72B-Instruct-GGUF",
          "bartowski/Qwen2-VL-72B-Instruct-GGUF",
          "Qwen/Qwen2.5-VL-72B-Instruct-GGUF"]:
    try:
        info = api.repo_info(r, files_metadata=True)
        weights = [(s.rfilename, s.size or 0) for s in info.siblings if s.rfilename.lower().endswith(".gguf")]
        q4 = [(n,s) for n,s in weights if "q4_k_m" in n.lower()]
        if q4:
            tot = sum(s for _,s in q4)/1e9
            print(f"  OK  {r}: {len(q4)} Q4_K_M shards, {tot:.1f} GB")
        else:
            print(f"  ??  {r}: exists, {len(weights)} GGUFs but no Q4_K_M")
            for n,s in sorted(weights, key=lambda x:-x[1])[:3]:
                print(f"       {s/1e9:5.1f}GB  {n}")
    except Exception as e:
        print(f"  --  {r}: missing")

print()
print("Candidate GGUF mirrors for DBRX-instruct (looking for Q4_K_M):")
for r in ["mradermacher/dbrx-instruct-i1-GGUF",
          "mradermacher/dbrx-instruct-GGUF",
          "ggml-org/dbrx-instruct-GGUF",
          "bartowski/dbrx-instruct-GGUF",
          "PrunaAI/dbrx-instruct-GGUF-smashed",
          "nold/dbrx-instruct-GGUF",
          "Mungert/dbrx-instruct-GGUF"]:
    try:
        info = api.repo_info(r, files_metadata=True)
        weights = [(s.rfilename, s.size or 0) for s in info.siblings if s.rfilename.lower().endswith(".gguf")]
        q4 = [(n,s) for n,s in weights if "q4_k_m" in n.lower()]
        if q4:
            tot = sum(s for _,s in q4)/1e9
            print(f"  OK  {r}: {len(q4)} Q4_K_M shards, {tot:.1f} GB")
        else:
            print(f"  ??  {r}: exists, {len(weights)} GGUFs but no Q4_K_M")
            for n,s in sorted(weights, key=lambda x:-x[1])[:3]:
                print(f"       {s/1e9:5.1f}GB  {n}")
    except Exception as e:
        print(f"  --  {r}: missing")
