"""
Add 8 frontier / multimodal / premium-GGUF models to AbteeXAILab.

For each new model:
  - create repo on HF org AbteeXAILab
  - write full scaffold (README, 3 SVGs, quickstart.py, requirements.txt,
    release_export_manifest.json, checksums.sha256, LICENSE.txt, VERSION.txt,
    UPLOAD_TO_HF.md, ollama/Modelfile, hf_space/{app.py,README.md,requirements.txt})
  - upload everything to the repo
  - append a registry entry to lumynax_model_registry.json
After all 8 are pushed, re-upload the updated registry to AbteeXAILab/marama-route.
"""
from __future__ import annotations

import json
import os
import sys
import time
import hashlib
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, r"S:\hf-publish")

from huggingface_hub import HfApi, create_repo
from huggingface_hub.utils import HfHubHTTPError

import generate_cards_v6 as G  # noqa: E402

TOKEN = os.environ["HF_TOKEN"]
api = HfApi(token=TOKEN)
ROOT = Path(r"S:\hf-publish")
OUT = ROOT / "cards_v6"
OUT.mkdir(parents=True, exist_ok=True)
REG_PATH = G.REGISTRY_PATH
REG_LOCAL = ROOT / "marama-route" / "configs" / "lumynax_model_registry.json"

# ---------- 8 new model specs ----------
NEW_MODELS: List[Dict[str, Any]] = [
    {
        "model_id": "lumynax-frontier-qwen3-235b-a22b-instruct",
        "repo_id": "AbteeXAILab/lumynax-frontier-qwen3-235b-a22b-instruct",
        "title": "LumynaX Frontier Qwen3 235B A22B Instruct",
        "family": "qwen",
        "runtime": "transformers",
        "modalities": ["text"],
        "context_tokens": 262144,
        "jurisdiction": "NZ",
        "residency": ["NZ", "AU", "global"],
        "license_id": "apache-2.0",
        "quantization": "bf16 / fp8 / Q4_K_M (community GGUF)",
        "primary_artifact": "model.safetensors (sharded)",
        "active_params_b": 22,
        "total_params_b": 235,
        "quality_rank": 1,
        "cost_rank": 5,
        "sovereignty_tier": 2,
        "supports_tools": True,
        "supports_json": True,
        "tags": ["frontier", "moe", "reasoning", "qwen3", "tools", "json", "long-context"],
        "metadata": {
            "upstream_repo": "Qwen/Qwen3-235B-A22B-Instruct-2507",
            "release_version": "v0.1.0",
            "package_state": "scaffold_pulls_upstream",
            "public_status": "public and non-gated",
            "validation_status": "scaffold_verified",
        },
        "_upstream": ("Qwen/Qwen3-235B-A22B-Instruct-2507", "apache-2.0", "chatml", "Qwen3 MoE upstream"),
        "_kind": "transformers_text",
        "_gguf_mirror": "unsloth/Qwen3-235B-A22B-Instruct-2507-GGUF",
    },
    {
        "model_id": "lumynax-frontier-minimax-m2-230b",
        "repo_id": "AbteeXAILab/lumynax-frontier-minimax-m2-230b",
        "title": "LumynaX Frontier MiniMax M2 230B Agentic",
        "family": "minimax",
        "runtime": "transformers",
        "modalities": ["text"],
        "context_tokens": 204800,
        "jurisdiction": "NZ",
        "residency": ["NZ", "AU", "global"],
        "license_id": "other",
        "quantization": "bf16 / Q4_K_M (community GGUF)",
        "primary_artifact": "model.safetensors (sharded)",
        "active_params_b": 10,
        "total_params_b": 230,
        "quality_rank": 1,
        "cost_rank": 5,
        "sovereignty_tier": 2,
        "supports_tools": True,
        "supports_json": True,
        "tags": ["frontier", "moe", "agentic", "minimax", "tools", "json"],
        "metadata": {
            "upstream_repo": "MiniMaxAI/MiniMax-M2",
            "release_version": "v0.1.0",
            "package_state": "scaffold_pulls_upstream",
            "public_status": "public and non-gated",
            "validation_status": "scaffold_verified",
        },
        "_upstream": ("MiniMaxAI/MiniMax-M2", "other", "chatml", "MiniMax-M2 upstream"),
        "_kind": "transformers_text",
        "_gguf_mirror": "unsloth/MiniMax-M2-GGUF",
    },
    {
        "model_id": "lumynax-frontier-mixtral-8x22b-instruct-gguf",
        "repo_id": "AbteeXAILab/lumynax-frontier-mixtral-8x22b-instruct-gguf",
        "title": "LumynaX Frontier Mixtral 8x22B Instruct GGUF",
        "family": "mistral",
        "runtime": "llama_cpp",
        "modalities": ["text"],
        "context_tokens": 65536,
        "jurisdiction": "NZ",
        "residency": ["NZ"],
        "license_id": "apache-2.0",
        "quantization": "Q4_K_M (default) · Q5_K_M · Q8_0",
        "primary_artifact": "Mixtral-8x22B-Instruct-v0.1.Q4_K_M.gguf",
        "active_params_b": 39,
        "total_params_b": 141,
        "quality_rank": 2,
        "cost_rank": 4,
        "sovereignty_tier": 3,
        "supports_tools": True,
        "supports_json": True,
        "tags": ["frontier", "moe", "mixtral", "gguf", "llama-cpp", "tools"],
        "metadata": {
            "upstream_repo": "mistralai/Mixtral-8x22B-Instruct-v0.1",
            "release_version": "v0.1.0",
            "package_state": "scaffold_pulls_upstream_gguf",
            "public_status": "public and non-gated",
            "validation_status": "scaffold_verified",
        },
        "_upstream": ("mistralai/Mixtral-8x22B-Instruct-v0.1", "apache-2.0", "mistral", "MaziyarPanahi GGUF"),
        "_kind": "gguf",
        "_gguf_mirror": "MaziyarPanahi/Mixtral-8x22B-Instruct-v0.1-GGUF",
        "_gguf_filename": "Mixtral-8x22B-Instruct-v0.1.Q4_K_M-*.gguf",
    },
    {
        "model_id": "lumynax-frontier-dbrx-instruct-132b-gguf",
        "repo_id": "AbteeXAILab/lumynax-frontier-dbrx-instruct-132b-gguf",
        "title": "LumynaX Frontier DBRX Instruct 132B GGUF",
        "family": "dbrx",
        "runtime": "llama_cpp",
        "modalities": ["text"],
        "context_tokens": 32768,
        "jurisdiction": "NZ",
        "residency": ["NZ"],
        "license_id": "other",
        "quantization": "Q4_K_M (default) · Q5_K_M · Q8_0",
        "primary_artifact": "dbrx-instruct.Q4_K_M.gguf",
        "active_params_b": 36,
        "total_params_b": 132,
        "quality_rank": 2,
        "cost_rank": 4,
        "sovereignty_tier": 3,
        "supports_tools": True,
        "supports_json": True,
        "tags": ["frontier", "moe", "dbrx", "databricks", "gguf", "llama-cpp"],
        "metadata": {
            "upstream_repo": "databricks/dbrx-instruct",
            "release_version": "v0.1.0",
            "package_state": "scaffold_pulls_upstream_gguf",
            "public_status": "public and non-gated",
            "validation_status": "scaffold_verified",
        },
        "_upstream": ("databricks/dbrx-instruct", "other", "chatml", "PrunaAI / bartowski DBRX GGUF"),
        "_kind": "gguf",
        "_gguf_mirror": "PrunaAI/dbrx-instruct-GGUF-smashed",
        "_gguf_filename": "dbrx-instruct.Q4_K_M.gguf",
    },
    {
        "model_id": "lumynax-multimodal-llama4-scout-109b-instruct",
        "repo_id": "AbteeXAILab/lumynax-multimodal-llama4-scout-109b-instruct",
        "title": "LumynaX Multimodal Llama-4 Scout 109B Instruct",
        "family": "llama",
        "runtime": "transformers_multimodal",
        "modalities": ["text", "vision"],
        "context_tokens": 10485760,
        "jurisdiction": "NZ",
        "residency": ["NZ", "AU", "global"],
        "license_id": "llama4",
        "quantization": "bf16 / fp8 / Q4_K_M (community)",
        "primary_artifact": "model.safetensors (sharded)",
        "active_params_b": 17,
        "total_params_b": 109,
        "quality_rank": 2,
        "cost_rank": 5,
        "sovereignty_tier": 2,
        "supports_tools": True,
        "supports_json": True,
        "tags": ["multimodal", "vision", "moe", "llama4", "long-context", "image-text-to-text"],
        "metadata": {
            "upstream_repo": "meta-llama/Llama-4-Scout-17B-16E-Instruct",
            "release_version": "v0.1.0",
            "package_state": "scaffold_pulls_upstream",
            "public_status": "public (upstream is gated — accept Meta licence first)",
            "validation_status": "scaffold_verified",
        },
        "_upstream": ("meta-llama/Llama-4-Scout-17B-16E-Instruct", "llama4", "llama4", "Meta Llama-4 upstream (gated)"),
        "_kind": "transformers_multimodal",
        "_gguf_mirror": "unsloth/Llama-4-Scout-17B-16E-Instruct-GGUF",
    },
    {
        "model_id": "lumynax-multimodal-qwen25-vl-72b-instruct-gguf",
        "repo_id": "AbteeXAILab/lumynax-multimodal-qwen25-vl-72b-instruct-gguf",
        "title": "LumynaX Multimodal Qwen2.5 VL 72B Instruct GGUF",
        "family": "qwen",
        "runtime": "llama_cpp_multimodal",
        "modalities": ["text", "vision"],
        "context_tokens": 131072,
        "jurisdiction": "NZ",
        "residency": ["NZ"],
        "license_id": "other",
        "quantization": "Q4_K_M (default) · Q5_K_M · Q8_0",
        "primary_artifact": "Qwen2.5-VL-72B-Instruct-Q4_K_M.gguf",
        "active_params_b": None,
        "total_params_b": 72,
        "quality_rank": 2,
        "cost_rank": 4,
        "sovereignty_tier": 3,
        "supports_tools": True,
        "supports_json": True,
        "tags": ["multimodal", "vision", "qwen", "gguf", "llama-cpp", "image-text-to-text"],
        "metadata": {
            "upstream_repo": "Qwen/Qwen2.5-VL-72B-Instruct",
            "release_version": "v0.1.0",
            "package_state": "scaffold_pulls_upstream_gguf",
            "public_status": "public and non-gated",
            "validation_status": "scaffold_verified",
        },
        "_upstream": ("Qwen/Qwen2.5-VL-72B-Instruct", "qwen", "qwen-vl", "bartowski Qwen2.5-VL GGUF"),
        "_kind": "gguf_multimodal",
        "_gguf_mirror": "bartowski/Qwen2.5-VL-72B-Instruct-GGUF",
        "_gguf_filename": "Qwen2.5-VL-72B-Instruct-Q4_K_M.gguf",
        "_mmproj": "mmproj-Qwen2.5-VL-72B-Instruct-f16.gguf",
    },
    {
        "model_id": "lumynax-multimodal-pixtral-large-124b",
        "repo_id": "AbteeXAILab/lumynax-multimodal-pixtral-large-124b",
        "title": "LumynaX Multimodal Pixtral Large 124B",
        "family": "mistral",
        "runtime": "transformers_multimodal",
        "modalities": ["text", "vision"],
        "context_tokens": 131072,
        "jurisdiction": "NZ",
        "residency": ["NZ", "AU"],
        "license_id": "other",
        "quantization": "bf16 / fp8",
        "primary_artifact": "model.safetensors (sharded)",
        "active_params_b": None,
        "total_params_b": 124,
        "quality_rank": 2,
        "cost_rank": 5,
        "sovereignty_tier": 2,
        "supports_tools": True,
        "supports_json": True,
        "tags": ["multimodal", "vision", "pixtral", "mistral", "image-text-to-text"],
        "metadata": {
            "upstream_repo": "mistralai/Pixtral-Large-Instruct-2411",
            "release_version": "v0.1.0",
            "package_state": "scaffold_pulls_upstream",
            "public_status": "public (Mistral research licence — non-commercial use)",
            "validation_status": "scaffold_verified",
        },
        "_upstream": ("mistralai/Pixtral-Large-Instruct-2411", "other", "mistral", "Mistral Pixtral upstream"),
        "_kind": "transformers_multimodal",
        "_gguf_mirror": None,
    },
    {
        "model_id": "lumynax-reasoning-glm46-355b-moe",
        "repo_id": "AbteeXAILab/lumynax-reasoning-glm46-355b-moe",
        "title": "LumynaX Reasoning GLM-4.6 355B MoE",
        "family": "glm",
        "runtime": "transformers",
        "modalities": ["text"],
        "context_tokens": 204800,
        "jurisdiction": "NZ",
        "residency": ["NZ", "AU", "global"],
        "license_id": "mit",
        "quantization": "bf16 / fp8 / Q4_K_M (community)",
        "primary_artifact": "model.safetensors (sharded)",
        "active_params_b": 32,
        "total_params_b": 355,
        "quality_rank": 1,
        "cost_rank": 5,
        "sovereignty_tier": 2,
        "supports_tools": True,
        "supports_json": True,
        "tags": ["frontier", "reasoning", "moe", "glm", "tools", "long-context"],
        "metadata": {
            "upstream_repo": "zai-org/GLM-4.6",
            "release_version": "v0.1.0",
            "package_state": "scaffold_pulls_upstream",
            "public_status": "public and non-gated",
            "validation_status": "scaffold_verified",
        },
        "_upstream": ("zai-org/GLM-4.6", "mit", "glm4", "Zhipu GLM-4.6 upstream"),
        "_kind": "transformers_text",
        "_gguf_mirror": "unsloth/GLM-4.6-GGUF",
    },
]


# ---------- patch generator upstream lookup so new IDs resolve cleanly ----------
_ORIG_INFER = G.infer_upstream
_UPSTREAM_BY_ID = {m["model_id"]: m["_upstream"] for m in NEW_MODELS}

def _patched_infer(model_id: str, family: str):
    if model_id in _UPSTREAM_BY_ID:
        return _UPSTREAM_BY_ID[model_id]
    return _ORIG_INFER(model_id, family)

G.infer_upstream = _patched_infer


# ---------- scaffold files ----------
LICENSE_BLURB = """LumynaX release package — distribution scaffold

This Hugging Face repository contains the LumynaX release scaffold for the
upstream model identified in `release_export_manifest.json`. The model weights
themselves remain governed by the upstream licence at `metadata.upstream_repo`
and are fetched by the runtime via Hugging Face Hub when you execute
`quickstart.py`.

The scaffold (configs, manifest, quickstart, ollama Modelfile, Space app) is
released under the MIT licence by AbteeX AI Labs (Aotearoa New Zealand). Your
use of the *upstream weights* is governed by the *upstream licence*; this file
does not relicense them.

Provenance, residency and audit obligations are defined in
`release_export_manifest.json` and the model card.
"""

VERSION_TXT = "v0.1.0\n"

UPLOAD_TO_HF_MD = """# Upload checklist (AbteeX AI Labs)

This scaffold was generated and pushed by `S:\\hf-publish\\add_8_more_models.py`.
The repo is structured to be cloned whole and verified locally before running.

```bash
hf download {repo_id} --local-dir {model_id}
cd {model_id}
pip install -r requirements.txt
python quickstart.py --interactive
```

To regenerate or refresh, re-run the script — `huggingface_hub.HfApi.upload_folder`
is idempotent.
"""


def _gen_quickstart(spec: Dict[str, Any]) -> str:
    repo_id = spec["repo_id"]
    upstream = spec["_upstream"][0]
    title = spec["title"]
    kind = spec["_kind"]
    mirror = spec.get("_gguf_mirror")
    gguf_filename = spec.get("_gguf_filename", "*Q4_K_M*.gguf")
    mmproj = spec.get("_mmproj")
    ctx = spec.get("context_tokens", 8192)

    header = f'''"""
{title} — LumynaX quickstart.

This script fetches the upstream model from Hugging Face and runs a short
LumynaX-flavoured prompt. Run it on a host that satisfies the resource budget
documented in the README ({title}).

Usage:
    python quickstart.py                # one-shot demo prompt
    python quickstart.py --interactive  # REPL
    python quickstart.py --gguf         # use the GGUF mirror via llama-cpp

LumynaX package repo: https://huggingface.co/{repo_id}
Upstream weights:     https://huggingface.co/{upstream}
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
'''

    if kind == "gguf":
        body = f'''
def _run_gguf(prompt: str, interactive: bool):
    from llama_cpp import Llama
    print("[lumynax] Loading GGUF from {mirror} (this can be large)...")
    llm = Llama.from_pretrained(
        repo_id="{mirror}",
        filename="{gguf_filename}",
        n_ctx={min(ctx, 16384)},
        n_gpu_layers=int(os.environ.get("N_GPU_LAYERS", "-1")),
        verbose=False,
    )
    def chat(user):
        out = llm.create_chat_completion(messages=[
            {{"role": "system", "content": LUMYNAX_SYSTEM}},
            {{"role": "user",   "content": user}},
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
'''
    elif kind == "gguf_multimodal":
        body = f'''
def _run_gguf(prompt: str, image: str | None, interactive: bool):
    from llama_cpp import Llama
    from llama_cpp.llama_chat_format import Llava15ChatHandler
    from huggingface_hub import hf_hub_download
    print("[lumynax] Loading GGUF + mmproj from {mirror}...")
    mmproj_path = hf_hub_download(repo_id="{mirror}", filename="{mmproj or 'mmproj-f16.gguf'}")
    handler = Llava15ChatHandler(clip_model_path=mmproj_path)
    llm = Llama.from_pretrained(
        repo_id="{mirror}",
        filename="{gguf_filename}",
        chat_handler=handler,
        n_ctx={min(ctx, 16384)},
        n_gpu_layers=int(os.environ.get("N_GPU_LAYERS", "-1")),
        verbose=False,
    )
    def chat(user, img_path):
        content = [{{"type": "text", "text": user}}]
        if img_path:
            uri = img_path if img_path.startswith("http") else "file://" + os.path.abspath(img_path)
            content.insert(0, {{"type": "image_url", "image_url": {{"url": uri}}}})
        out = llm.create_chat_completion(messages=[
            {{"role": "system", "content": LUMYNAX_SYSTEM}},
            {{"role": "user", "content": content}},
        ], max_tokens=512, temperature=0.4)
        return out["choices"][0]["message"]["content"]
    if interactive:
        print("[lumynax] interactive mode — type '/img <path>' to attach an image, empty line to exit.")
        pending_img = None
        while True:
            try: q = input("you> ").strip()
            except EOFError: break
            if not q: break
            if q.startswith("/img "): pending_img = q[5:].strip(); print(f"[lumynax] attached: {{pending_img}}"); continue
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
'''
    elif kind == "transformers_multimodal":
        body = f'''
def _run_hf(prompt: str, image: str | None, interactive: bool):
    import torch
    from transformers import AutoProcessor, AutoModelForImageTextToText
    print("[lumynax] Loading {upstream} (multimodal). Requires significant VRAM.")
    processor = AutoProcessor.from_pretrained("{upstream}", trust_remote_code=True)
    model = AutoModelForImageTextToText.from_pretrained(
        "{upstream}", device_map="auto", torch_dtype="auto", trust_remote_code=True
    )
    def chat(user, img_path):
        content = [{{"type": "text", "text": user}}]
        if img_path:
            content.insert(0, {{"type": "image", "url": img_path}})
        messages = [
            {{"role": "system", "content": [{{"type": "text", "text": LUMYNAX_SYSTEM}}]}},
            {{"role": "user", "content": content}},
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
            if q.startswith("/img "): pending = q[5:].strip(); print(f"[lumynax] attached: {{pending}}"); continue
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
'''
    else:  # transformers_text
        body = f'''
def _run_hf(prompt: str, interactive: bool):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    print("[lumynax] Loading {upstream}. This is a >100B MoE — multi-GPU or accelerate offload recommended.")
    tok = AutoTokenizer.from_pretrained("{upstream}", trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        "{upstream}", device_map="auto", torch_dtype="auto", trust_remote_code=True
    )
    def chat(user):
        messages = [
            {{"role": "system", "content": LUMYNAX_SYSTEM}},
            {{"role": "user",   "content": user}},
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
    mirror = "{mirror or ''}"
    if not mirror:
        print("[lumynax] No community GGUF mirror registered for this build."); sys.exit(2)
    print(f"[lumynax] Loading GGUF from {{mirror}}...")
    llm = Llama.from_pretrained(
        repo_id=mirror, filename="*Q4_K_M*.gguf",
        n_ctx={min(ctx, 16384)},
        n_gpu_layers=int(os.environ.get("N_GPU_LAYERS", "-1")), verbose=False,
    )
    def chat(user):
        out = llm.create_chat_completion(messages=[
            {{"role": "system", "content": LUMYNAX_SYSTEM}},
            {{"role": "user",   "content": user}},
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
'''
    return header + body


def _gen_requirements(spec: Dict[str, Any]) -> str:
    kind = spec["_kind"]
    base = ["huggingface_hub>=0.27", "numpy"]
    if kind in ("gguf", "gguf_multimodal"):
        base += ["llama-cpp-python>=0.3.2"]
    else:
        base += [
            "torch>=2.4",
            "transformers>=4.50",
            "accelerate>=1.0",
            "safetensors",
            "sentencepiece",
            "einops",
        ]
        if kind == "transformers_multimodal":
            base += ["pillow", "torchvision"]
    return "\n".join(base) + "\n"


def _gen_manifest(spec: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "release_id": spec["model_id"],
        "title": spec["title"],
        "repo_id": spec["repo_id"],
        "version": "v0.1.0",
        "publisher": "AbteeX AI Labs",
        "publisher_org": "AbteeXAILab",
        "jurisdiction": spec["jurisdiction"],
        "residency": spec["residency"],
        "upstream": {
            "repo_id": spec["_upstream"][0],
            "license": spec["_upstream"][1],
            "prompt_format": spec["_upstream"][2],
            "source_note": spec["_upstream"][3],
        },
        "gguf_mirror": spec.get("_gguf_mirror"),
        "runtime": spec["runtime"],
        "modalities": spec["modalities"],
        "context_tokens": spec["context_tokens"],
        "total_params_b": spec["total_params_b"],
        "active_params_b": spec["active_params_b"],
        "quantization": spec["quantization"],
        "primary_artifact": spec["primary_artifact"],
        "package_state": spec["metadata"]["package_state"],
        "validation_status": spec["metadata"]["validation_status"],
        "sovereignty_tier": spec["sovereignty_tier"],
        "supports_tools": spec["supports_tools"],
        "supports_json": spec["supports_json"],
        "audit_hash_chain": "SHA-256 over canonical request + response JSON",
        "build_date_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def _gen_modelfile(spec: Dict[str, Any]) -> str:
    upstream = spec["_upstream"][0]
    mirror = spec.get("_gguf_mirror") or upstream
    sys_prompt = (
        "You are LumynaX, the AbteeX AI Labs assistant from Aotearoa New Zealand. "
        "Ko te marama te tuapapa. Answer with care; cite uncertainty; refuse unsafe asks."
    )
    if spec["_kind"] in ("gguf", "gguf_multimodal"):
        from_line = f"FROM hf.co/{mirror}"
    else:
        from_line = f"# Upstream HF repo: {upstream}\n# Use 'ollama pull' on a converted GGUF mirror, or run via transformers (see quickstart.py).\nFROM hf.co/{mirror}"
    return f'''{from_line}

PARAMETER temperature 0.4
PARAMETER top_p 0.9
PARAMETER num_ctx {min(spec["context_tokens"], 16384)}

SYSTEM """{sys_prompt}"""
'''


SPACE_APP = '''import os
import gradio as gr

REPO_ID = "{repo_id}"
UPSTREAM = "{upstream}"
TITLE = "{title}"

THEME_CSS = """
:root {{ --lx-paper:#fffefa; --lx-ink:#0a0a0b; --lx-amber:#e08a2c; }}
body, .gradio-container {{ background: var(--lx-paper) !important; color: var(--lx-ink) !important; }}
h1, h2, h3 {{ font-family: 'Cormorant Garamond', 'EB Garamond', Georgia, serif; }}
"""

def chat_stub(message, history):
    return (
        f"This Space is a scaffold for **{{TITLE}}**. The upstream model is `{{UPSTREAM}}` "
        f"and the LumynaX package repo is `{{REPO_ID}}`. Cloud inference for >100B MoE models "
        f"is not run inside this free Space — clone the repo and run `quickstart.py` on a "
        f"capable host. You asked: {{message!r}}."
    )

with gr.Blocks(css=THEME_CSS, title=TITLE) as demo:
    gr.Markdown(f"# {{TITLE}}\\n*Sovereign intelligence, held in the light.*\\n\\nLumynaX release scaffold — clone `{{REPO_ID}}` for the full package.")
    gr.ChatInterface(chat_stub, examples=["Explain LumynaX in 2 bullets.", "Why local-first AI for Aotearoa?"])

if __name__ == "__main__":
    demo.launch()
'''

SPACE_README = '''---
title: {title}
colorFrom: yellow
colorTo: gray
sdk: gradio
sdk_version: 5.50.0
python_version: 3.11
app_file: app.py
pinned: false
license: apache-2.0
short_description: Scaffold Space for the {short} LumynaX release.
tags:
- abteex-ai-labs
- lumynax
- sovereign-ai
- new-zealand
---

# {title}

Scaffold Space for `{repo_id}`. The actual model weights are too large to host on a free Space.
Clone the package repo and run `quickstart.py` locally for the real inference path.
'''


def _checksums(files: Dict[str, bytes]) -> str:
    lines = []
    for name in sorted(files):
        h = hashlib.sha256(files[name]).hexdigest()
        lines.append(f"{h}  {name}")
    return "\n".join(lines) + "\n"


# ---------- per-model build + upload ----------
def build_and_push(spec: Dict[str, Any]) -> str:
    repo_id = spec["repo_id"]
    short = spec["model_id"]
    print(f"\n=== {repo_id} ===")

    out_dir = OUT / short
    docs_dir = out_dir / "docs"
    ollama_dir = out_dir / "ollama"
    space_dir = out_dir / "hf_space"
    for d in (out_dir, docs_dir, ollama_dir, space_dir):
        d.mkdir(parents=True, exist_ok=True)

    # 1. README + 3 SVGs via existing generator
    parsed: Dict[str, str] = {}  # no existing readme
    title = spec["title"]
    runtime = spec["runtime"]
    params = f"{spec['total_params_b']}B" + (f"/{spec['active_params_b']}Ba" if spec["active_params_b"] else "")
    modality_str = "+".join(spec["modalities"])
    license_meta = spec["_upstream"][1]
    (docs_dir / "lumynax-overview.svg").write_text(
        G.build_hero_svg(title, repo_id, spec["family"], params, runtime, modality_str, spec["quantization"], license_meta),
        encoding="utf-8",
    )
    (docs_dir / "lumynax-runtime-flow.svg").write_text(
        G.build_runtime_svg(title, runtime, spec["sovereignty_tier"]),
        encoding="utf-8",
    )
    (docs_dir / "lumynax-capability.svg").write_text(
        G.build_capability_svg(spec["quality_rank"], spec["cost_rank"], spec["sovereignty_tier"], spec["supports_tools"], spec["supports_json"], spec["context_tokens"]),
        encoding="utf-8",
    )
    card = G.build_card(spec, parsed)
    (out_dir / "README.md").write_text(card, encoding="utf-8")

    # 2. Scaffold files
    qs = _gen_quickstart(spec)
    (out_dir / "quickstart.py").write_text(qs, encoding="utf-8")
    reqs = _gen_requirements(spec)
    (out_dir / "requirements.txt").write_text(reqs, encoding="utf-8")
    manifest = _gen_manifest(spec)
    (out_dir / "release_export_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (out_dir / "LICENSE.txt").write_text(LICENSE_BLURB, encoding="utf-8")
    (out_dir / "VERSION.txt").write_text(VERSION_TXT, encoding="utf-8")
    (out_dir / "UPLOAD_TO_HF.md").write_text(UPLOAD_TO_HF_MD.format(repo_id=repo_id, model_id=short), encoding="utf-8")
    (ollama_dir / "Modelfile").write_text(_gen_modelfile(spec), encoding="utf-8")
    (space_dir / "app.py").write_text(SPACE_APP.format(repo_id=repo_id, upstream=spec["_upstream"][0], title=title), encoding="utf-8")
    (space_dir / "README.md").write_text(SPACE_README.format(title=title, short=short, repo_id=repo_id), encoding="utf-8")
    (space_dir / "requirements.txt").write_text("gradio==5.50.0\n", encoding="utf-8")

    # checksums over the scaffold (excluding the SVGs/README which can change)
    scaffold_files = {
        "quickstart.py": qs.encode("utf-8"),
        "requirements.txt": reqs.encode("utf-8"),
        "release_export_manifest.json": json.dumps(manifest, indent=2).encode("utf-8"),
        "LICENSE.txt": LICENSE_BLURB.encode("utf-8"),
        "VERSION.txt": VERSION_TXT.encode("utf-8"),
        "ollama/Modelfile": _gen_modelfile(spec).encode("utf-8"),
    }
    (out_dir / "checksums.sha256").write_text(_checksums(scaffold_files), encoding="utf-8")

    # 3. Create repo (idempotent)
    try:
        create_repo(repo_id=repo_id, repo_type="model", private=False, exist_ok=True, token=TOKEN)
        print("  repo ensured")
    except Exception as exc:
        print(f"  create_repo FAIL: {exc}")
        return f"FAIL:create_repo: {exc}"

    # 4. Upload everything
    try:
        api.upload_folder(
            folder_path=str(out_dir),
            repo_id=repo_id,
            repo_type="model",
            token=TOKEN,
            commit_message="feat: initial LumynaX scaffold (card v6 + quickstart + manifest + Modelfile + Space scaffold)",
        )
        print("  pushed full scaffold.")
        return "OK"
    except Exception as exc:
        print(f"  upload_folder FAIL: {type(exc).__name__}: {exc}")
        return f"FAIL:upload: {exc}"


def update_registry() -> None:
    reg = json.loads(REG_PATH.read_text(encoding="utf-8"))
    existing_ids = {m["repo_id"] for m in reg["models"]}
    added = 0
    for spec in NEW_MODELS:
        if spec["repo_id"] in existing_ids:
            print(f"  registry: {spec['model_id']} already present, skipping")
            continue
        reg_entry = {k: v for k, v in spec.items() if not k.startswith("_")}
        reg["models"].append(reg_entry)
        added += 1
    reg["model_count"] = len(reg["models"])
    REG_PATH.write_text(json.dumps(reg, indent=2), encoding="utf-8")
    # Also keep the local copy in sync
    REG_LOCAL.parent.mkdir(parents=True, exist_ok=True)
    REG_LOCAL.write_text(json.dumps(reg, indent=2), encoding="utf-8")
    print(f"  registry updated (+{added}, total {reg['model_count']})")

    # Re-upload to marama-route
    try:
        api.upload_file(
            path_or_fileobj=str(REG_PATH),
            path_in_repo="configs/lumynax_model_registry.json",
            repo_id="AbteeXAILab/marama-route",
            repo_type="model",
            token=TOKEN,
            commit_message=f"chore(registry): add {added} frontier/multimodal/MoE models",
        )
        print("  marama-route registry re-uploaded.")
    except Exception as exc:
        print(f"  registry upload FAIL: {exc}")


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode == "one":
        target = sys.argv[2]
        spec = next(m for m in NEW_MODELS if m["model_id"].endswith(target) or m["model_id"] == target)
        print(build_and_push(spec))
        return
    if mode == "registry":
        update_registry()
        return
    results: Dict[str, str] = {}
    for i, spec in enumerate(NEW_MODELS, 1):
        print(f"\n[{i}/{len(NEW_MODELS)}] {spec['repo_id']}")
        results[spec["repo_id"]] = build_and_push(spec)
        time.sleep(0.4)
    update_registry()
    ok = sum(1 for v in results.values() if v == "OK")
    print(f"\n=== DONE: {ok}/{len(results)} pushed ===")
    for k, v in results.items():
        if v != "OK":
            print(f"  FAIL {k}: {v}")


if __name__ == "__main__":
    main()
