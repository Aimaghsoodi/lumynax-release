"""
Refresh quickstart.py for the 8 newly-mirrored repos so they load the
LOCAL mirrored weight files (no upstream HF call needed at runtime).
After this, every repo is true clone-and-run.
"""
import os, json, sys
from pathlib import Path
from huggingface_hub import HfApi
sys.path.insert(0, r"S:\hf-publish")

TOKEN = os.environ["HF_TOKEN"]
api = HfApi(token=TOKEN)

NEW_REPOS = {
    # repo_id: (primary_artifact_filename, mmproj_filename or None, kind)
    "AbteeXAILab/lumynax-frontier-qwen3-235b-a22b-instruct": (
        "Q4_K_M/Qwen3-235B-A22B-Instruct-2507-Q4_K_M-00001-of-00003.gguf",
        None, "gguf_split"
    ),
    "AbteeXAILab/lumynax-frontier-minimax-m2-230b": (
        "Q4_K_M/MiniMax-M2-Q4_K_M-00001-of-00003.gguf",
        None, "gguf_split"
    ),
    "AbteeXAILab/lumynax-frontier-mixtral-8x22b-instruct-gguf": (
        "Mixtral-8x22B-Instruct-v0.1.Q4_K_M-00001-of-00002.gguf",
        None, "gguf_split"
    ),
    "AbteeXAILab/lumynax-frontier-dbrx-instruct-132b-gguf": (
        "dbrx-instruct.Q2_K.gguf",
        None, "gguf_single"
    ),
    "AbteeXAILab/lumynax-multimodal-qwen25-vl-72b-instruct-gguf": (
        "Qwen2.5-VL-72B-Instruct-Q4_K_M.gguf",
        "mmproj-Qwen2.5-VL-72B-Instruct-f16.gguf", "gguf_vision"
    ),
    "AbteeXAILab/lumynax-multimodal-pixtral-large-124b": (
        "consolidated.safetensors.index.json",
        None, "safetensors_vision"
    ),
    "AbteeXAILab/lumynax-reasoning-glm46-355b-moe": (
        "Q4_K_M/GLM-4.6-Q4_K_M-00001-of-00005.gguf",
        None, "gguf_split"
    ),
    "AbteeXAILab/lumynax-multimodal-internvl3-78b-instruct": (
        "model.safetensors.index.json",
        None, "safetensors_vision"
    ),
}

SYS_BLURB = (
    "You are LumynaX, the AbteeX AI Labs assistant from Aotearoa New Zealand. "
    "Ko te marama te tuapapa. Answer with care; cite uncertainty; refuse unsafe asks."
)

TPL_GGUF = '''"""
{title} — LumynaX quickstart (clone & run).

This loads the GGUF that ships with this repo. No upstream HF call needed
once you've done `hf download {repo_id}`.

Usage:
  python quickstart.py                   # one-shot demo prompt
  python quickstart.py --interactive     # REPL
"""
from __future__ import annotations
import argparse, glob, os, sys
from pathlib import Path

LUMYNAX_SYSTEM = "{sys_blurb}"
DEMO_PROMPT = "Explain in 3 bullets why local-first AI matters for Aotearoa New Zealand."

# Locate the primary GGUF that was downloaded alongside this script.
HERE = Path(__file__).resolve().parent
PRIMARY = HERE / r"{primary}"
{shard_glob_block}

def main():
    from llama_cpp import Llama
    p = argparse.ArgumentParser()
    p.add_argument("--interactive", action="store_true")
    p.add_argument("--prompt", default=DEMO_PROMPT)
    args = p.parse_args()
    if not PRIMARY.exists():
        print(f"[lumynax] primary weight file missing: {{PRIMARY}}", file=sys.stderr)
        print(f"[lumynax] run: hf download {repo_id} --local-dir <dir> first.", file=sys.stderr)
        sys.exit(2)
    print(f"[lumynax] loading {{PRIMARY.name}}{{shard_log_suffix}}")
    llm = Llama(model_path=str(PRIMARY), n_ctx={ctx},
                n_gpu_layers=int(os.environ.get("N_GPU_LAYERS","-1")), verbose=False)
    def chat(user):
        out = llm.create_chat_completion(messages=[
            {{"role":"system","content":LUMYNAX_SYSTEM}},
            {{"role":"user","content":user}},
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
'''

TPL_GGUF_VISION = '''"""
{title} — LumynaX quickstart (clone & run, multimodal).

Loads the local GGUF + mmproj that ship with this repo.

Usage:
  python quickstart.py                       # one-shot demo prompt
  python quickstart.py --interactive         # REPL ('/img <path>' to attach)
  python quickstart.py --image foo.jpg --prompt "describe this"
"""
from __future__ import annotations
import argparse, os, sys
from pathlib import Path

LUMYNAX_SYSTEM = "{sys_blurb}"
DEMO_PROMPT = "Explain in 3 bullets why local-first AI matters for Aotearoa New Zealand."

HERE = Path(__file__).resolve().parent
PRIMARY = HERE / r"{primary}"
MMPROJ  = HERE / r"{mmproj}"

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
            print(f"[lumynax] missing weight file: {{f}}", file=sys.stderr)
            print(f"[lumynax] run: hf download {repo_id} --local-dir <dir> first.", file=sys.stderr)
            sys.exit(2)
    print(f"[lumynax] loading {{PRIMARY.name}} + mmproj")
    handler = Llava15ChatHandler(clip_model_path=str(MMPROJ))
    llm = Llama(model_path=str(PRIMARY), chat_handler=handler, n_ctx={ctx},
                n_gpu_layers=int(os.environ.get("N_GPU_LAYERS","-1")), verbose=False)
    def chat(user, img):
        content = [{{"type":"text","text":user}}]
        if img:
            uri = img if img.startswith("http") else "file://" + os.path.abspath(img)
            content.insert(0, {{"type":"image_url","image_url":{{"url":uri}}}})
        out = llm.create_chat_completion(messages=[
            {{"role":"system","content":LUMYNAX_SYSTEM}},
            {{"role":"user","content":content}},
        ], max_tokens=512, temperature=0.4)
        return out["choices"][0]["message"]["content"]
    if args.interactive:
        print("[lumynax] interactive — '/img <path>' attaches, empty line exits.")
        pending = None
        while True:
            try: q = input("you> ").strip()
            except EOFError: break
            if not q: break
            if q.startswith("/img "): pending = q[5:].strip(); print(f"[lumynax] attached: {{pending}}"); continue
            print("lumynax> " + chat(q, pending)); pending = None
    else:
        print(chat(args.prompt, args.image))

if __name__ == "__main__":
    main()
'''

TPL_SAFETENSORS = '''"""
{title} — LumynaX quickstart (clone & run, multimodal safetensors).

Loads the local safetensors shards in this repo via transformers.
Requires significant VRAM ({mem_hint}).

Usage:
  python quickstart.py --interactive
  python quickstart.py --image foo.jpg --prompt "describe this"
"""
from __future__ import annotations
import argparse, os, sys
from pathlib import Path

LUMYNAX_SYSTEM = "{sys_blurb}"
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
    if not (HERE / "{primary}").exists():
        print(f"[lumynax] weight index missing in {{HERE}}", file=sys.stderr)
        print(f"[lumynax] run: hf download {repo_id} --local-dir <dir> first.", file=sys.stderr)
        sys.exit(2)
    print(f"[lumynax] loading from local repo {{HERE}}")
    processor = AutoProcessor.from_pretrained(str(HERE), trust_remote_code=True)
    model = AutoModelForImageTextToText.from_pretrained(
        str(HERE), device_map="auto", torch_dtype="auto", trust_remote_code=True
    )
    def chat(user, img):
        content = [{{"type":"text","text":user}}]
        if img: content.insert(0, {{"type":"image","url":img}})
        messages = [
            {{"role":"system","content":[{{"type":"text","text":LUMYNAX_SYSTEM}}]}},
            {{"role":"user","content":content}},
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
            if q.startswith("/img "): pending = q[5:].strip(); print(f"[lumynax] attached: {{pending}}"); continue
            print("lumynax> " + chat(q, pending)); pending = None
    else:
        print(chat(args.prompt, args.image))

if __name__ == "__main__":
    main()
'''


def render(repo_id: str, info: tuple) -> str:
    primary, mmproj, kind = info
    title = repo_id.split("/")[-1].replace("-", " ").title()
    ctx = 16384
    if kind == "gguf_single":
        return TPL_GGUF.format(
            title=title, repo_id=repo_id, sys_blurb=SYS_BLURB,
            primary=primary, ctx=ctx,
            shard_glob_block="", shard_log_suffix="",
        )
    if kind == "gguf_split":
        # llama.cpp auto-detects further shards when you point at shard 00001-of-NNNNN
        return TPL_GGUF.format(
            title=title, repo_id=repo_id, sys_blurb=SYS_BLURB,
            primary=primary, ctx=ctx,
            shard_glob_block="# llama.cpp auto-loads sibling shards from the same dir.",
            shard_log_suffix=" (split GGUF — sibling shards auto-loaded)",
        )
    if kind == "gguf_vision":
        return TPL_GGUF_VISION.format(
            title=title, repo_id=repo_id, sys_blurb=SYS_BLURB,
            primary=primary, mmproj=mmproj, ctx=ctx,
        )
    if kind == "safetensors_vision":
        mem_hint = "200+ GB VRAM" if "pixtral" in repo_id else "160+ GB VRAM"
        return TPL_SAFETENSORS.format(
            title=title, repo_id=repo_id, sys_blurb=SYS_BLURB,
            primary=primary, mem_hint=mem_hint,
        )
    raise ValueError(kind)


def main():
    for repo, info in NEW_REPOS.items():
        print(f"=== {repo}")
        content = render(repo, info)
        try:
            api.upload_file(
                path_or_fileobj=content.encode("utf-8"),
                path_in_repo="quickstart.py",
                repo_id=repo, repo_type="model", token=TOKEN,
                commit_message="docs(quickstart): load mirrored local weights (no upstream fetch)",
            )
            print("  pushed quickstart.py")
        except Exception as e:
            print(f"  FAIL: {e}")

if __name__ == "__main__":
    main()
