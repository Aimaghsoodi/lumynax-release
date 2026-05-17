"""
LumynaX Multimodal Qwen2.5 VL 72B Instruct GGUF — LumynaX quickstart.

This script fetches the upstream model from Hugging Face and runs a short
LumynaX-flavoured prompt. Run it on a host that satisfies the resource budget
documented in the README (LumynaX Multimodal Qwen2.5 VL 72B Instruct GGUF).

Usage:
    python quickstart.py                # one-shot demo prompt
    python quickstart.py --interactive  # REPL
    python quickstart.py --gguf         # use the GGUF mirror via llama-cpp

LumynaX package repo: https://huggingface.co/AbteeXAILab/lumynax-multimodal-qwen25-vl-72b-instruct-gguf
Upstream weights:     https://huggingface.co/Qwen/Qwen2.5-VL-72B-Instruct
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

def _run_gguf(prompt: str, image: str | None, interactive: bool):
    from llama_cpp import Llama
    from llama_cpp.llama_chat_format import Llava15ChatHandler
    from huggingface_hub import hf_hub_download
    print("[lumynax] Loading GGUF + mmproj from ggml-org/Qwen2.5-VL-72B-Instruct-GGUF...")
    mmproj_path = hf_hub_download(repo_id="ggml-org/Qwen2.5-VL-72B-Instruct-GGUF", filename="mmproj-Qwen2.5-VL-72B-Instruct-f16.gguf")
    handler = Llava15ChatHandler(clip_model_path=mmproj_path)
    llm = Llama.from_pretrained(
        repo_id="ggml-org/Qwen2.5-VL-72B-Instruct-GGUF",
        filename="Qwen2.5-VL-72B-Instruct-Q4_K_M.gguf",
        chat_handler=handler,
        n_ctx=16384,
        n_gpu_layers=int(os.environ.get("N_GPU_LAYERS", "-1")),
        verbose=False,
    )
    def chat(user, img_path):
        content = [{"type": "text", "text": user}]
        if img_path:
            uri = img_path if img_path.startswith("http") else "file://" + os.path.abspath(img_path)
            content.insert(0, {"type": "image_url", "image_url": {"url": uri}})
        out = llm.create_chat_completion(messages=[
            {"role": "system", "content": LUMYNAX_SYSTEM},
            {"role": "user", "content": content},
        ], max_tokens=512, temperature=0.4)
        return out["choices"][0]["message"]["content"]
    if interactive:
        print("[lumynax] interactive mode — type '/img <path>' to attach an image, empty line to exit.")
        pending_img = None
        while True:
            try: q = input("you> ").strip()
            except EOFError: break
            if not q: break
            if q.startswith("/img "): pending_img = q[5:].strip(); print(f"[lumynax] attached: {pending_img}"); continue
            print("lumynax> " + chat(q, pending_img)); pending_img = None
    else:
        print(chat(prompt, image))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--interactive", action="store_true")
    p.add_argument("--prompt", default=DEMO_PROMPT)
    p.add_argument("--image", default=None, help="path or URL of an image to describe")
    args = p.parse_args()
    _run_gguf(args.prompt, args.image, args.interactive)


if __name__ == "__main__":
    main()
