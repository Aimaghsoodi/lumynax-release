"""
LumynaX Multimodal Pixtral Large 124B — LumynaX quickstart.

This script fetches the upstream model from Hugging Face and runs a short
LumynaX-flavoured prompt. Run it on a host that satisfies the resource budget
documented in the README (LumynaX Multimodal Pixtral Large 124B).

Usage:
    python quickstart.py                # one-shot demo prompt
    python quickstart.py --interactive  # REPL
    python quickstart.py --gguf         # use the GGUF mirror via llama-cpp

LumynaX package repo: https://huggingface.co/AbteeXAILab/lumynax-multimodal-pixtral-large-124b
Upstream weights:     https://huggingface.co/mistralai/Pixtral-Large-Instruct-2411
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

def _run_hf(prompt: str, image: str | None, interactive: bool):
    import torch
    from transformers import AutoProcessor, AutoModelForImageTextToText
    print("[lumynax] Loading mistralai/Pixtral-Large-Instruct-2411 (multimodal). Requires significant VRAM.")
    processor = AutoProcessor.from_pretrained("mistralai/Pixtral-Large-Instruct-2411", trust_remote_code=True)
    model = AutoModelForImageTextToText.from_pretrained(
        "mistralai/Pixtral-Large-Instruct-2411", device_map="auto", torch_dtype="auto", trust_remote_code=True
    )
    def chat(user, img_path):
        content = [{"type": "text", "text": user}]
        if img_path:
            content.insert(0, {"type": "image", "url": img_path})
        messages = [
            {"role": "system", "content": [{"type": "text", "text": LUMYNAX_SYSTEM}]},
            {"role": "user", "content": content},
        ]
        inputs = processor.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt"
        ).to(model.device)
        out = model.generate(**inputs, max_new_tokens=512, do_sample=True, temperature=0.4)
        return processor.batch_decode(out[:, inputs["input_ids"].shape[-1]:], skip_special_tokens=True)[0]
    if interactive:
        print("[lumynax] interactive mode — '/img <path>' to attach, empty line exits.")
        pending = None
        while True:
            try: q = input("you> ").strip()
            except EOFError: break
            if not q: break
            if q.startswith("/img "): pending = q[5:].strip(); print(f"[lumynax] attached: {pending}"); continue
            print("lumynax> " + chat(q, pending)); pending = None
    else:
        print(chat(prompt, image))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--interactive", action="store_true")
    p.add_argument("--prompt", default=DEMO_PROMPT)
    p.add_argument("--image", default=None)
    p.add_argument("--gguf", action="store_true", help="if set, use community GGUF mirror via llama-cpp")
    args = p.parse_args()
    if args.gguf:
        print("[lumynax] GGUF path: see README for the community GGUF mirror and run the GGUF quickstart there.")
        sys.exit(0)
    _run_hf(args.prompt, args.image, args.interactive)


if __name__ == "__main__":
    main()
