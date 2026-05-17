"""Serial resume of the 5 missing Pack D + E models, smallest-first."""
import sys, os, time
sys.path.insert(0, r"S:\hf-publish")
from pack_a_ship import mirror_files

# (dest_repo, source_repo, patterns, approx_GB)
PLAN = [
    ("AbteeXAILab/lumynax-coder-codellama-70b-instruct-gguf",
     "TheBloke/CodeLlama-70B-Instruct-GGUF", ["codellama-70b-instruct.Q4_K_M.gguf"], 41),
    ("AbteeXAILab/lumynax-reasoning-deepseek-r1-distill-llama-70b-gguf",
     "bartowski/DeepSeek-R1-Distill-Llama-70B-GGUF", ["DeepSeek-R1-Distill-Llama-70B-Q4_K_M.gguf"], 42),
    ("AbteeXAILab/lumynax-frontier-coder-deepseek-v25-1210-gguf",
     "bartowski/DeepSeek-V2.5-1210-GGUF", ["DeepSeek-V2.5-1210-Q4_K_M/*.gguf"], 142),
    ("AbteeXAILab/lumynax-frontier-coder-qwen3-480b-a35b-gguf",
     "unsloth/Qwen3-Coder-480B-A35B-Instruct-GGUF", ["Q4_K_M/*.gguf"], 290),
    ("AbteeXAILab/lumynax-reasoning-deepseek-prover-v2-671b-gguf",
     "unsloth/DeepSeek-Prover-V2-671B-GGUF", ["Q4_K_M/*.gguf"], 404),
]
for i, (dst, src, pats, gb) in enumerate(PLAN, 1):
    print(f"\n>>>>>> [{i}/{len(PLAN)}] {dst}  (~{gb} GB)")
    try:
        mirror_files(dst, src, pats)
    except Exception as e:
        print(f"  FAIL: {e}")
print("\n=== resume DONE ===")
