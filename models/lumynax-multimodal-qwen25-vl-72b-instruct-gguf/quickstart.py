"""
Lumynax Multimodal Qwen25 Vl 72B Instruct Gguf — LumynaX quickstart (clone & run, multimodal).

Loads the local GGUF + mmproj that ship with this repo.

Usage:
  python quickstart.py                       # one-shot demo prompt
  python quickstart.py --interactive         # REPL ('/img <path>' to attach)
  python quickstart.py --image foo.jpg --prompt "describe this"
"""
from __future__ import annotations
import argparse, os, sys
from pathlib import Path

LUMYNAX_SYSTEM = "You are LumynaX, the AbteeX AI Labs assistant from Aotearoa New Zealand. Ko te marama te tuapapa. Answer with care; cite uncertainty; refuse unsafe asks."
DEMO_PROMPT = "Explain in 3 bullets why local-first AI matters for Aotearoa New Zealand."

HERE = Path(__file__).resolve().parent
PRIMARY = HERE / r"Qwen2.5-VL-72B-Instruct-Q4_K_M.gguf"
MMPROJ  = HERE / r"mmproj-Qwen2.5-VL-72B-Instruct-f16.gguf"

def main():
    from llama_cpp import Llama
    from llama_cpp.llama_chat_format import Llava15ChatHandler
    p = argparse.ArgumentParser()
    p.add_argument("--interactive", action="store_true")
    p.add_argument("--prompt", default=DEMO_PROMPT)
    p.add_argument("--image", default=None)
    args = p.parse_args()
    for f in (PRIMARY, MMPROJ):
        if not f.exists():
            print(f"[lumynax] missing weight file: {f}", file=sys.stderr)
            print(f"[lumynax] run: hf download AbteeXAILab/lumynax-multimodal-qwen25-vl-72b-instruct-gguf --local-dir <dir> first.", file=sys.stderr)
            sys.exit(2)
    print(f"[lumynax] loading {PRIMARY.name} + mmproj")
    handler = Llava15ChatHandler(clip_model_path=str(MMPROJ))
    llm = Llama(model_path=str(PRIMARY), chat_handler=handler, n_ctx=16384,
                n_gpu_layers=int(os.environ.get("N_GPU_LAYERS","-1")), verbose=False)
    def chat(user, img):
        content = [{"type":"text","text":user}]
        if img:
            uri = img if img.startswith("http") else "file://" + os.path.abspath(img)
            content.insert(0, {"type":"image_url","image_url":{"url":uri}})
        out = llm.create_chat_completion(messages=[
            {"role":"system","content":LUMYNAX_SYSTEM},
            {"role":"user","content":content},
        ], max_tokens=512, temperature=0.4)
        return out["choices"][0]["message"]["content"]
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
