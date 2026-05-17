"""
LumynaX Doc Table Transformer (detection) — LumynaX quickstart.

This script fetches the upstream model from Hugging Face and runs a short
LumynaX-flavoured prompt. Run it on a host that satisfies the resource budget
documented in the README (LumynaX Doc Table Transformer (detection)).

Usage:
    python quickstart.py                # one-shot demo prompt
    python quickstart.py --interactive  # REPL
    python quickstart.py --gguf         # use the GGUF mirror via llama-cpp

LumynaX package repo: https://huggingface.co/AbteeXAILab/lumynax-doc-table-transformer-detection
Upstream weights:     https://huggingface.co/microsoft/table-transformer-detection
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

def _run_hf(prompt: str, interactive: bool):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    print("[lumynax] Loading microsoft/table-transformer-detection. This is a >100B MoE — multi-GPU or accelerate offload recommended.")
    tok = AutoTokenizer.from_pretrained("microsoft/table-transformer-detection", trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        "microsoft/table-transformer-detection", device_map="auto", torch_dtype="auto", trust_remote_code=True
    )
    def chat(user):
        messages = [
            {"role": "system", "content": LUMYNAX_SYSTEM},
            {"role": "user",   "content": user},
        ]
        text = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tok(text, return_tensors="pt").to(model.device)
        out = model.generate(**inputs, max_new_tokens=512, do_sample=True, temperature=0.4)
        return tok.decode(out[0, inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
    if interactive:
        print("[lumynax] interactive mode — empty line exits.")
        while True:
            try: q = input("you> ").strip()
            except EOFError: break
            if not q: break
            print("lumynax> " + chat(q))
    else:
        print(chat(prompt))


def _run_gguf(prompt: str, interactive: bool):
    from llama_cpp import Llama
    mirror = ""
    if not mirror:
        print("[lumynax] No community GGUF mirror registered for this build."); sys.exit(2)
    print(f"[lumynax] Loading GGUF from {mirror}...")
    llm = Llama.from_pretrained(
        repo_id=mirror, filename="*Q4_K_M*.gguf",
        n_ctx=0,
        n_gpu_layers=int(os.environ.get("N_GPU_LAYERS", "-1")), verbose=False,
    )
    def chat(user):
        out = llm.create_chat_completion(messages=[
            {"role": "system", "content": LUMYNAX_SYSTEM},
            {"role": "user",   "content": user},
        ], max_tokens=512, temperature=0.4)
        return out["choices"][0]["message"]["content"]
    if interactive:
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
    p.add_argument("--gguf", action="store_true")
    args = p.parse_args()
    if args.gguf:
        _run_gguf(args.prompt, args.interactive)
    else:
        _run_hf(args.prompt, args.interactive)


if __name__ == "__main__":
    main()
