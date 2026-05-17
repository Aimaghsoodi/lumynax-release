"""
Lumynax Math Qwen25 Math 7B Gguf — LumynaX quickstart (clone & run).

This loads the GGUF that ships with this repo. No upstream HF call needed
once you've done `hf download AbteeXAILab/lumynax-math-qwen25-math-7b-gguf`.

Usage:
  python quickstart.py                   # one-shot demo prompt
  python quickstart.py --interactive     # REPL
"""
from __future__ import annotations
import argparse, glob, os, sys
from pathlib import Path

LUMYNAX_SYSTEM = "You are LumynaX, the AbteeX AI Labs assistant from Aotearoa New Zealand. Ko te marama te tuapapa. Answer with care; cite uncertainty; refuse unsafe asks."
DEMO_PROMPT = "Explain in 3 bullets why local-first AI matters for Aotearoa New Zealand."

# Locate the primary GGUF that was downloaded alongside this script.
HERE = Path(__file__).resolve().parent
PRIMARY = HERE / r"Qwen2.5-Math-7B-Instruct-Q4_K_M.gguf"


def main():
    from llama_cpp import Llama
    p = argparse.ArgumentParser()
    p.add_argument("--interactive", action="store_true")
    p.add_argument("--prompt", default=DEMO_PROMPT)
    args = p.parse_args()
    if not PRIMARY.exists():
        print(f"[lumynax] primary weight file missing: {PRIMARY}", file=sys.stderr)
        print(f"[lumynax] run: hf download AbteeXAILab/lumynax-math-qwen25-math-7b-gguf --local-dir <dir> first.", file=sys.stderr)
        sys.exit(2)
    print(f"[lumynax] loading {PRIMARY.name}{shard_log_suffix}")
    llm = Llama(model_path=str(PRIMARY), n_ctx=16384,
                n_gpu_layers=int(os.environ.get("N_GPU_LAYERS","-1")), verbose=False)
    def chat(user):
        out = llm.create_chat_completion(messages=[
            {"role":"system","content":LUMYNAX_SYSTEM},
            {"role":"user","content":user},
        ], max_tokens=512, temperature=0.4)
        return out["choices"][0]["message"]["content"]
    if args.interactive:
        print("[lumynax] interactive mode — empty line exits.")
        while True:
            try: q = input("you> ").strip()
            except EOFError: break
            if not q: break
            print("lumynax> " + chat(q))
    else:
        print(chat(args.prompt))

if __name__ == "__main__":
    main()
