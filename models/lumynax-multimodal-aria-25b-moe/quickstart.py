"""
Lumynax Multimodal Aria 25B Moe — LumynaX quickstart (clone & run, multimodal safetensors).

Loads the local safetensors shards in this repo via transformers.
Requires significant VRAM (160+ GB VRAM).

Usage:
  python quickstart.py --interactive
  python quickstart.py --image foo.jpg --prompt "describe this"
"""
from __future__ import annotations
import argparse, os, sys
from pathlib import Path

LUMYNAX_SYSTEM = "You are LumynaX, the AbteeX AI Labs assistant from Aotearoa New Zealand. Ko te marama te tuapapa. Answer with care; cite uncertainty; refuse unsafe asks."
DEMO_PROMPT = "Explain in 3 bullets why local-first AI matters for Aotearoa New Zealand."
HERE = Path(__file__).resolve().parent

def main():
    import torch
    from transformers import AutoProcessor, AutoModelForImageTextToText
    p = argparse.ArgumentParser()
    p.add_argument("--interactive", action="store_true")
    p.add_argument("--prompt", default=DEMO_PROMPT)
    p.add_argument("--image", default=None)
    args = p.parse_args()
    if not (HERE / "model.safetensors.index.json").exists():
        print(f"[lumynax] weight index missing in {HERE}", file=sys.stderr)
        print(f"[lumynax] run: hf download AbteeXAILab/lumynax-multimodal-aria-25b-moe --local-dir <dir> first.", file=sys.stderr)
        sys.exit(2)
    print(f"[lumynax] loading from local repo {HERE}")
    processor = AutoProcessor.from_pretrained(str(HERE), trust_remote_code=True)
    model = AutoModelForImageTextToText.from_pretrained(
        str(HERE), device_map="auto", torch_dtype="auto", trust_remote_code=True
    )
    def chat(user, img):
        content = [{"type":"text","text":user}]
        if img: content.insert(0, {"type":"image","url":img})
        messages = [
            {"role":"system","content":[{"type":"text","text":LUMYNAX_SYSTEM}]},
            {"role":"user","content":content},
        ]
        inputs = processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=True,
                                               return_dict=True, return_tensors="pt").to(model.device)
        out = model.generate(**inputs, max_new_tokens=512, do_sample=True, temperature=0.4)
        return processor.batch_decode(out[:, inputs["input_ids"].shape[-1]:], skip_special_tokens=True)[0]
    if args.interactive:
        print("[lumynax] interactive — '/img <path>' attaches, empty line exits.")
        pending = None
        while True:
            try: q = input("you> ").strip()
            except EOFError: break
            if not q: break
            if q.startswith("/img "): pending = q[5:].strip(); print(f"[lumynax] attached: {pending}"); continue
            print("lumynax> " + chat(q, pending)); pending = None
    else:
        print(chat(args.prompt, args.image))

if __name__ == "__main__":
    main()
