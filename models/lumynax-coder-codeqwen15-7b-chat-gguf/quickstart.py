"""
LumynaX Coder CodeQwen1.5 7B Chat GGUF — LumynaX quickstart.

This script fetches the upstream model from Hugging Face and runs a short
LumynaX-flavoured prompt. Run it on a host that satisfies the resource budget
documented in the README (LumynaX Coder CodeQwen1.5 7B Chat GGUF).

Usage:
    python quickstart.py                # one-shot demo prompt
    python quickstart.py --interactive  # REPL
    python quickstart.py --gguf         # use the GGUF mirror via llama-cpp

LumynaX package repo: https://huggingface.co/AbteeXAILab/lumynax-coder-codeqwen15-7b-chat-gguf
Upstream weights:     https://huggingface.co/Qwen/CodeQwen1.5-7B-Chat
"""
from __future__ import annotations
import argparse, os, sys

LUMYNAX_SYSTEM = (
    "You are LumynaX, the AbteeX AI Labs assistant from Aotearoa New Zealand. "
    "Ko te marama te tuapapa - the light is the foundation. "
    "Answer with care, cite uncertainty, and prefer local-first reasoning. "
    "Refuse unsafe, unlawful, or sovereignty-violating requests."
)
DEMO_PROMPT = "Explain in 3 bullets why local-first AI matters for Aotearoa New Zealand."

def _run_gguf(prompt: str, interactive: bool):
    from llama_cpp import Llama
    print("[lumynax] Loading GGUF from Qwen/CodeQwen1.5-7B-Chat-GGUF (this can be large)...")
    llm = Llama.from_pretrained(
        repo_id="Qwen/CodeQwen1.5-7B-Chat-GGUF",
        filename="codeqwen-1_5-7b-chat-q4_k_m.gguf",
        n_ctx=16384,
        n_gpu_layers=int(os.environ.get("N_GPU_LAYERS", "-1")),
        verbose=False,
    )
    def chat(user):
        out = llm.create_chat_completion(messages=[
            {"role": "system", "content": LUMYNAX_SYSTEM},
            {"role": "user",   "content": user},
        ], max_tokens=512, temperature=0.4)
        return out["choices"][0]["message"]["content"]
    if interactive:
        print("[lumynax] interactive mode — empty line exits.")
        while True:
            try: q = input("you> ").strip()
            except EOFError: break
            if not q: break
            print("lumynax> " + chat(q))
    else:
        print(chat(prompt))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--interactive", action="store_true")
    p.add_argument("--prompt", default=DEMO_PROMPT)
    p.add_argument("--gguf", action="store_true", help="kept for compatibility — this build is GGUF-only")
    args = p.parse_args()
    _run_gguf(args.prompt, args.interactive)


if __name__ == "__main__":
    main()
