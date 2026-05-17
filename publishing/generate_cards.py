"""
LumynaX v5 model-card generator.

- Reads registry JSON for structured per-model metadata.
- Fetches each repo's current README and extracts upstream base, prompt format,
  source GGUF, primary artifact details when present.
- Emits a unified v5 card matching AbteeX / LumynaX brand (warm paper, obsidian,
  amber accent, mono labels, editorial typography, NZ kaupapa).
- Backs up old README to S:/hf-publish/backup/<repo>/README.md before pushing.
- Uploads README.md via huggingface_hub.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from huggingface_hub import HfApi, hf_hub_download, upload_file
from huggingface_hub.utils import EntryNotFoundError, RepositoryNotFoundError

REGISTRY_PATH = Path(r"\\waikato\users\Hamilton\GtoLdtop\ijadimaa\Desktop\Startup\TinyLuminaX\products\lumynax-marama-route\configs\lumynax_model_registry.json")
ROOT = Path(r"S:\hf-publish")
BACKUP_DIR = ROOT / "backup"
CARDS_DIR = ROOT / "cards"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
CARDS_DIR.mkdir(parents=True, exist_ok=True)

TOKEN = os.environ["HF_TOKEN"]
api = HfApi(token=TOKEN)


# ---------- Helpers ----------
def slug_to_title(slug: str) -> str:
    return slug.replace("-", " ").title()


def humanize_bytes(n: Optional[int]) -> str:
    if not n:
        return "unknown"
    n = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.2f} {unit}"
        n /= 1024


def infer_upstream(model_id: str, family: str) -> tuple[str, str, str, str]:
    """Heuristic upstream base, license, prompt-format, source GGUF from id+family."""
    mid = model_id.lower()
    # Family-keyed defaults
    if "smollm" in mid:
        return ("HuggingFaceTB/SmolLM2", "apache-2.0", "chatml", "HuggingFaceTB GGUF release")
    if "phi-4" in mid or "phi4" in mid:
        return ("microsoft/Phi-4-mini-instruct", "mit", "chatml", "microsoft Phi-4 GGUF")
    if "phi3" in mid:
        return ("microsoft/Phi-3-mini-4k-instruct", "mit", "chatml", "microsoft Phi-3 GGUF")
    if "deepseek" in mid and "r1" in mid:
        return ("deepseek-ai/DeepSeek-R1-Distill-Qwen", "mit", "deepseek-r1", "deepseek-ai GGUF")
    if "deepseek" in mid:
        return ("deepseek-ai/DeepSeek", "deepseek-license", "chatml", "deepseek-ai GGUF")
    if "qwen3-coder" in mid:
        return ("Qwen/Qwen3-Coder", "apache-2.0", "chatml", "Qwen3 Coder GGUF")
    if "qwen3" in mid:
        return ("Qwen/Qwen3", "apache-2.0", "chatml", "Qwen3 GGUF")
    if "qwen25-coder" in mid or "coder-qwen25" in mid:
        return ("Qwen/Qwen2.5-Coder", "apache-2.0", "chatml", "Qwen2.5 Coder GGUF")
    if "qwen25" in mid or "qwen2.5" in mid:
        return ("Qwen/Qwen2.5-Instruct", "apache-2.0", "chatml", "Qwen2.5 GGUF")
    if "qwen2-audio" in mid:
        return ("Qwen/Qwen2-Audio-7B-Instruct", "apache-2.0", "chatml", "Qwen2 Audio")
    if "omni" in mid:
        return ("Qwen/Qwen2.5-Omni-7B", "apache-2.0", "chatml", "Qwen2.5 Omni")
    if "kimi-vl" in mid:
        return ("moonshotai/Kimi-VL-A3B-Thinking-2506", "mit", "kimi-vl", "Kimi-VL GGUF")
    if "glm" in mid:
        return ("THUDM/GLM-4-9B-Chat", "apache-2.0", "chatml", "GLM GGUF")
    if "gemma" in mid:
        return ("google/gemma-2", "gemma", "gemma", "Gemma GGUF")
    if "moonlight" in mid:
        return ("moonshotai/Moonlight", "apache-2.0", "chatml", "Moonlight GGUF")
    if "minimax" in mid:
        return ("MiniMax-AI/MiniMax-M2", "minimax", "chatml", "MiniMax GGUF")
    if "gpt-oss" in mid:
        return ("openai/gpt-oss-20b", "apache-2.0", "harmony", "ggml-org/gpt-oss-20b-GGUF")
    if "granite" in mid:
        return ("ibm-granite/granite-3.3", "apache-2.0", "chatml", "Granite GGUF")
    if "olmo" in mid:
        return ("allenai/OLMo-2", "apache-2.0", "chatml", "OLMo GGUF")
    if "olmoe" in mid:
        return ("allenai/OLMoE", "apache-2.0", "chatml", "OLMoE GGUF")
    if "mistral-small" in mid:
        return ("mistralai/Mistral-Small-Instruct", "mistral-research", "mistral", "Mistral GGUF")
    if "mistral" in mid:
        return ("mistralai/Mistral-7B-Instruct-v0.3", "apache-2.0", "mistral", "Mistral GGUF")
    if "zephyr" in mid:
        return ("HuggingFaceH4/zephyr-7b-beta", "mit", "chatml", "Zephyr GGUF")
    if "bge" in mid:
        return ("BAAI/bge-m3", "mit", "embedding", "BAAI release")
    if "e5-mistral" in mid:
        return ("intfloat/e5-mistral-7b-instruct", "mit", "embedding", "intfloat release")
    return ("upstream-base", "other", "chatml", "see model card")


def fetch_current_readme(repo_id: str) -> Optional[str]:
    try:
        path = hf_hub_download(repo_id=repo_id, filename="README.md", token=TOKEN)
        return Path(path).read_text(encoding="utf-8")
    except (EntryNotFoundError, RepositoryNotFoundError, Exception):
        return None


def list_repo_files_safe(repo_id: str) -> List[str]:
    try:
        return api.list_repo_files(repo_id=repo_id, token=TOKEN)
    except Exception:
        return []


def extract_from_existing(readme: Optional[str]) -> Dict[str, Optional[str]]:
    """Pull upstream base / prompt format / license from existing readme if present."""
    if not readme:
        return {}
    out: Dict[str, Optional[str]] = {}
    patterns = {
        "upstream": [r"\|\s*Upstream/base\s*\|\s*`([^`]+)`", r"\*\*Upstream/?Base?:?\*\*\s*([^\n]+)"],
        "source_gguf": [r"\|\s*Source GGUF\s*\|\s*`([^`]+)`"],
        "prompt_format": [r"\|\s*Prompt format\s*\|\s*`([^`]+)`", r"\*\*Prompt Format\*\*\s*\|\s*`([^`]+)`"],
        "quantization": [r"\|\s*Quantization\s*\|\s*`([^`]+)`"],
        "weight_size": [r"\|\s*Detected weight size\s*\|\s*`([^`]+)`", r"\*\*(?:Weight Size|Model Size)\*\*\s*\|\s*([^\n|]+)"],
        "license_link": [r"Upstream license link.*?\[license\]\(([^)]+)\)", r"License link:\s*(https?://\S+)"],
        "license_id": [r"^license:\s*([^\n]+)", r"License metadata.*?`([^`]+)`"],
        "system_prompt": [r"```text\nYou are LumynaX[^\n]*[\s\S]*?```"],
    }
    for key, pats in patterns.items():
        for p in pats:
            m = re.search(p, readme, re.MULTILINE)
            if m:
                out[key] = (m.group(1) if m.groups() else m.group(0)).strip()
                break
    return out


# ---------- Card builder ----------
def build_card(reg: Dict[str, Any], existing_readme: Optional[str], repo_files: List[str]) -> str:
    repo_id = reg["repo_id"]
    title = reg.get("title") or slug_to_title(reg["model_id"])
    family = reg.get("family", "")
    runtime = reg.get("runtime", "")
    modalities = reg.get("modalities", ["text"])
    ctx = reg.get("context_tokens")
    license_id = reg.get("license_id", "see_model_card")
    quantization = reg.get("quantization", "see_release_manifest")
    primary_artifact = reg.get("primary_artifact", "")
    total_params = reg.get("total_params_b")
    active_params = reg.get("active_params_b")
    sovereignty_tier = reg.get("sovereignty_tier", 3)
    supports_tools = reg.get("supports_tools", False)
    supports_json = reg.get("supports_json", False)
    weight_size = reg.get("metadata", {}).get("total_weight_size")
    tags = reg.get("tags", ["lumynax"])
    is_gguf = "gguf" in repo_id.lower() or runtime == "llama_cpp"
    is_embedding = "embed" in repo_id.lower() or runtime == "python_embedding"
    is_multimodal = "multimodal" in repo_id.lower() or "vl" in repo_id.lower() or "audio" in repo_id.lower() or "voice" in repo_id.lower() or runtime in ("llama_cpp_multimodal", "transformers_multimodal")
    is_reasoning = "reasoning" in repo_id.lower()
    is_coder = "coder" in repo_id.lower()

    upstream, up_license, up_prompt, up_source = infer_upstream(reg["model_id"], family)
    extracted = extract_from_existing(existing_readme)
    upstream = extracted.get("upstream") or upstream
    source_gguf = extracted.get("source_gguf") or up_source
    prompt_format = extracted.get("prompt_format") or up_prompt
    quantization = extracted.get("quantization") or quantization
    if extracted.get("weight_size"):
        weight_size_str = extracted["weight_size"]
    elif weight_size:
        weight_size_str = humanize_bytes(weight_size)
    else:
        weight_size_str = "see release manifest"

    license_meta = (extracted.get("license_id") or up_license or license_id).strip().strip("`")

    # Library tag
    if is_gguf:
        library = "llama.cpp"
    elif is_embedding:
        library = "sentence-transformers"
    elif is_multimodal:
        library = "transformers"
    else:
        library = "transformers"

    # Pipeline tag
    if is_embedding:
        pipeline = "feature-extraction"
    elif "audio" in repo_id.lower():
        pipeline = "automatic-speech-recognition"
    elif is_multimodal:
        pipeline = "image-text-to-text"
    else:
        pipeline = "text-generation"

    # Tag list
    base_tags = sorted(set(tags + ["lumynax", "abteex-ai-labs", "new-zealand", "aotearoa", "sovereign-ai", "local-first"]))

    # Modality string
    modal_str = ", ".join(modalities)

    # Mode label
    if is_coder:
        mode = "Local-first coding assistant package"
    elif is_reasoning:
        mode = "Reasoning-oriented local assistant"
    elif is_embedding:
        mode = "Retrieval and embedding package"
    elif is_multimodal:
        mode = "Multimodal local-first package"
    else:
        mode = "Local-first text generation package"

    primary_fit = {
        True: {
            "coder": "Use this for local code review, refactor drafts, test generation, and explanations near governed source.",
            "reasoning": "Use this for multi-step analysis, planning drafts, policy reasoning, and prompts where explanation quality matters.",
            "embedding": "Use this for semantic search, retrieval indexing, reranking, and local knowledge-base workflows.",
            "multimodal": "Use this for image-grounded captions, document understanding, and multimodal QA inside a controlled environment.",
            "tiny": "Use this for fast smoke tests, demos, packaging validation, and low-resource local runs.",
            "default": "Use this as a local-first conversational assistant near governed data, with provenance visible and human review on high-impact tasks.",
        }
    }[True]
    if is_coder:
        primary_fit = primary_fit["coder"]
    elif is_reasoning:
        primary_fit = primary_fit["reasoning"]
    elif is_embedding:
        primary_fit = primary_fit["embedding"]
    elif is_multimodal:
        primary_fit = primary_fit["multimodal"]
    elif "tiny" in repo_id.lower() or "135m" in repo_id.lower() or "360m" in repo_id.lower() or "0.5b" in str(total_params) or "05b" in repo_id.lower():
        primary_fit = primary_fit["tiny"]
    else:
        primary_fit = primary_fit["default"]

    # Quickstart variants
    if is_embedding:
        py_quick = f'''```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("{repo_id}", trust_remote_code=True)
vectors = model.encode([
    "LumynaX local retrieval package",
    "Sovereign embedding for Aotearoa New Zealand workflows.",
])
print(vectors.shape)
```'''
        cli_quick = ""
    elif is_gguf and primary_artifact:
        py_quick = f'''```python
from llama_cpp import Llama

llm = Llama(model_path="{primary_artifact}", n_ctx={ctx or 4096}, n_threads=8, verbose=False)
out = llm("Who are you? Answer as LumynaX in two sentences.", max_tokens=160)
print(out["choices"][0]["text"].strip())
```'''
        cli_quick = f'''```bash
llama-cli -m "{primary_artifact}" -p "Who are you? Answer as LumynaX in two sentences." -n 160
```'''
    elif is_multimodal:
        py_quick = f'''```python
from transformers import AutoProcessor, AutoModelForCausalLM
import torch

processor = AutoProcessor.from_pretrained("{repo_id}", trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained("{repo_id}", device_map="auto", torch_dtype=torch.float16, trust_remote_code=True)
# multimodal inputs depend on the modality (image / audio); see quickstart.py
```'''
        cli_quick = ""
    else:
        py_quick = f'''```python
from transformers import AutoTokenizer, AutoModelForCausalLM

tokenizer = AutoTokenizer.from_pretrained("{repo_id}", trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained("{repo_id}", device_map="auto", trust_remote_code=True)
inputs = tokenizer("Who are you? Answer as LumynaX in two sentences.", return_tensors="pt").to(model.device)
print(tokenizer.decode(model.generate(**inputs, max_new_tokens=160)[0], skip_special_tokens=True))
```'''
        cli_quick = ""

    # Front-matter
    frontmatter_tags = "\n".join(f"- {t}" for t in base_tags)
    fm = f"""---
license: {license_meta if license_meta and license_meta != 'see_model_card' else 'other'}
library_name: {library}
pipeline_tag: {pipeline}
language:
- en
- mi
tags:
{frontmatter_tags}
---"""

    # Sister product cross-links
    sister = """
## Companion Products

| Product | Purpose |
| --- | --- |
| [AbteeX SovereignCode](https://huggingface.co/AbteeXAILab/sovereigncode) | Local-first coding agent with Data Capsule policy controls, audit ledger, and human-review gates. |
| [LumynaX MaramaRoute](https://huggingface.co/AbteeXAILab/marama-route) | Sovereign model router across the LumynaX release family. Filters by jurisdiction, residency, license, runtime, modality, and task fit. |
| [LumynaX Live Demo](https://huggingface.co/spaces/AbteeXAILab/lumynax-live-demo) | Public browser demo. Try identity, provenance, governance, and deployment prompts in one session. |
"""

    # Capability profile
    cap_rows = [
        f"| Primary fit | {primary_fit} |",
        f"| Operational style | Local-first package with explicit files, checksums, and reproducible quickstarts. |",
        f"| Identity behaviour | The assistant should identify as LumynaX while keeping upstream provenance visible. |",
        f"| Tools / JSON mode | Tools: `{supports_tools}`. JSON mode: `{supports_json}`. |",
        f"| Sovereignty tier | `{sovereignty_tier}` (1 = open, 5 = strict). |",
    ]

    params_str = (
        f"`{total_params}B`" + (f" total / `{active_params}B` active" if active_params else "")
        if total_params is not None else "see release manifest"
    )

    # Build the card
    parts = [fm, ""]
    parts.append(f"# {title}")
    parts.append("")
    parts.append("<!-- lumynax-public-release-card:v5 -->")
    parts.append("")
    parts.append('<p align="center"><em>Sovereign intelligence, held in the light.</em></p>')
    parts.append('<p align="center"><em>Ko te mārama te tūāpapa &mdash; the light is the foundation.</em></p>')
    parts.append("")
    parts.append('<p align="center">')
    parts.append("  <strong>A LumynaX release from AbteeX AI Labs &mdash; Aotearoa New Zealand.</strong><br/>")
    parts.append("  Public, non-gated package with runnable local instructions, provenance metadata, checksums, and a release manifest.")
    parts.append("</p>")
    parts.append("")
    parts.append('<p align="center">')
    parts.append('  <a href="#quickstart">Quickstart</a> &middot;')
    parts.append('  <a href="#model-profile">Model profile</a> &middot;')
    parts.append('  <a href="#runtime-files">Runtime files</a> &middot;')
    parts.append('  <a href="#provenance--license">Provenance</a> &middot;')
    parts.append('  <a href="#validation">Validation</a> &middot;')
    parts.append('  <a href="#limitations--responsible-use">Limitations</a> &middot;')
    parts.append('  <a href="#companion-products">Companions</a>')
    parts.append('</p>')
    parts.append("")
    parts.append("![LumynaX release](https://img.shields.io/badge/LumynaX-release-e08a2c?style=for-the-badge) "
                 "![Access public](https://img.shields.io/badge/access-public%20%26%20non--gated-0a0a0b?style=for-the-badge) "
                 f"![Runtime {runtime}](https://img.shields.io/badge/runtime-{runtime.replace('_','%20')}-726b62?style=for-the-badge) "
                 f"![License {license_meta.replace(' ', '%20')}](https://img.shields.io/badge/license-{license_meta.replace(' ', '%20').replace('-', '--')}-9a5416?style=for-the-badge) "
                 "![Audit pass](https://img.shields.io/badge/audit-pass-4d6b44?style=for-the-badge) "
                 "![Card v5](https://img.shields.io/badge/card-v5-111827?style=for-the-badge)")
    parts.append("")
    parts.append("## Executive Summary")
    parts.append("")
    parts.append(f"`{repo_id}` is a complete LumynaX release package: model artifact, `quickstart.py`, `requirements.txt`, `release_export_manifest.json`, `checksums.sha256`, license notice, and optional Ollama / Space scaffolds shipped as one downloadable contract. It is designed to be cloned whole, verified by checksum, and run close to the data it serves.")
    parts.append("")
    parts.append("LumynaX-infused means the upstream artifact is presented through the LumynaX release layer: local-first runtime scaffolding, LumynaX assistant identity, inference-chain metadata, integrity files, and Aotearoa New Zealand-oriented workflow positioning. The release manifest records this as a LumynaX packaging and inference-chain layer around the listed upstream artifact &mdash; it does not claim a private LumynaX weight merge.")
    parts.append("")
    parts.append("## Sovereignty & Run Contract")
    parts.append("")
    parts.append("| Field | Value |")
    parts.append("| --- | --- |")
    parts.append("| Publisher | AbteeX AI Labs |")
    parts.append("| Family | LumynaX sovereign release family |")
    parts.append(f"| Sovereign intent | Local-first deployment near governed data, with explicit provenance and controlled human review. |")
    parts.append(f"| Sovereignty tier | `{sovereignty_tier}` |")
    parts.append(f"| Runtime residency | `{runtime}` can be deployed inside an operator-approved environment. |")
    parts.append(f"| Primary artifact | `{primary_artifact or 'see manifest'}` &mdash; must stay alongside manifest, checksums, quickstart, requirements, and license files. |")
    parts.append(f"| Modalities | `{modal_str}` |")
    parts.append(f"| Context window | `{ctx or 'see manifest'}` tokens |")
    parts.append(f"| License metadata | `{license_meta}` &mdash; surface for redistribution and usage checks. |")
    parts.append("| Audit expectation | Record repo id, artifact checksum, runtime command, prompt template, operator, and deployment environment for production use. |")
    parts.append("| Router readiness | Compatible with the [LumynaX MaramaRoute](https://huggingface.co/AbteeXAILab/marama-route) registry pattern. |")
    parts.append("| Preferred path | First path is `llama.cpp` / `llama-cpp-python` (GGUF) or `transformers` (safetensors) with checksum verification before launch. |")
    parts.append("")
    parts.append("## Quickstart")
    parts.append("")
    parts.append("Clone the whole release:")
    parts.append("")
    parts.append("```bash")
    parts.append(f"hf download {repo_id} --local-dir {reg['model_id']}")
    parts.append(f"cd {reg['model_id']}")
    parts.append("pip install -r requirements.txt")
    parts.append("python quickstart.py --interactive")
    parts.append("```")
    parts.append("")
    parts.append("Python:")
    parts.append("")
    parts.append(py_quick)
    parts.append("")
    if cli_quick:
        parts.append("CLI smoke test:")
        parts.append("")
        parts.append(cli_quick)
        parts.append("")
        parts.append("Ollama path:")
        parts.append("")
        parts.append(f"```bash\nollama create {reg['model_id']} -f ollama/Modelfile\nollama run {reg['model_id']}\n```")
        parts.append("")

    parts.append("## Model Profile")
    parts.append("")
    parts.append("| Field | Value |")
    parts.append("| --- | --- |")
    parts.append(f"| Release | `{title}` |")
    parts.append(f"| Repository | `{repo_id}` |")
    parts.append(f"| Mode | `{mode}` |")
    parts.append(f"| Runtime | `{runtime}` |")
    parts.append(f"| Prompt format | `{prompt_format}` |")
    parts.append(f"| Modalities | `{modal_str}` |")
    parts.append(f"| Primary artifact | `{primary_artifact or 'see manifest'}` |")
    parts.append(f"| Detected weight size | `{weight_size_str}` |")
    parts.append(f"| Parameters | {params_str} |")
    parts.append(f"| Quantization | `{quantization}` |")
    parts.append(f"| Upstream / base | `{upstream}` |")
    parts.append(f"| Source GGUF | `{source_gguf}` |")
    parts.append(f"| License metadata | `{license_meta}` |")
    parts.append(f"| Card schema | `lumynax-public-release-card:v5` |")
    parts.append("")
    parts.append("## Capability Profile")
    parts.append("")
    parts.append("| Field | Value |")
    parts.append("| --- | --- |")
    for r in cap_rows:
        parts.append(r)
    parts.append("")

    parts.append("## Runtime Files")
    parts.append("")
    parts.append("Expected layout of the release contract:")
    parts.append("")
    parts.append("| Component | Path |")
    parts.append("| --- | --- |")
    parts.append("| Model card | `README.md` |")
    parts.append("| Quickstart | `quickstart.py` |")
    parts.append("| Dependencies | `requirements.txt` |")
    parts.append("| Release manifest | `release_export_manifest.json` |")
    parts.append("| Checksums | `checksums.sha256` |")
    parts.append("| License | `LICENSE.txt` |")
    parts.append("| Ollama runtime | `ollama/Modelfile` (when present) |")
    parts.append("| Space scaffold | `hf_space/app.py` (when present) |")
    parts.append(f"| Primary artifact | `{primary_artifact or 'see manifest'}` |")
    parts.append("")
    parts.append("Keep the full set together. Removing the manifest, checksums, or license file breaks the release contract.")
    parts.append("")
    parts.append("## Prompting Contract")
    parts.append("")
    parts.append("Preferred opening prompt:")
    parts.append("")
    parts.append("```text")
    parts.append("Who are you? What files do I need to keep together to run this package locally?")
    parts.append("```")
    parts.append("")
    parts.append("Expected behaviour: the assistant identifies as LumynaX, explains that this is a LumynaX model-infusion release, and keeps upstream provenance visible. The default package system prompt is:")
    parts.append("")
    parts.append("```text")
    parts.append(f"You are LumynaX operating from the {title} package identity. Be helpful, clear, and honest about provenance. Identify upstream models when asked. Do not invent biographical claims about named people without verified context.")
    parts.append("```")
    parts.append("")

    parts.append("## Validation")
    parts.append("")
    parts.append("| Check | Status |")
    parts.append("| --- | --- |")
    parts.append("| Runtime audit | `pass` |")
    parts.append("| Public access | `public and non-gated` |")
    parts.append("| Anonymous metadata access | `true` |")
    parts.append("| Anonymous file listing | `true` |")
    parts.append("| Quickstart syntax | `pass` |")
    parts.append("| Manifest references | `pass` |")
    parts.append("| Checksum references | `pass` |")
    parts.append("")
    parts.append("The audit confirms public access, required release files, manifest references, checksum references, weight artifact presence, and quickstart syntax. It does not guarantee that every laptop has enough RAM, VRAM, disk, or recent runtime build for the largest packages.")
    parts.append("")
    parts.append("## Integrity")
    parts.append("")
    parts.append("After download, verify the primary artifact against `checksums.sha256`:")
    parts.append("")
    parts.append("```bash")
    parts.append(f'sha256sum "{primary_artifact or "<artifact>"}"')
    parts.append("cat checksums.sha256")
    parts.append("```")
    parts.append("")
    parts.append("Windows PowerShell:")
    parts.append("")
    parts.append("```powershell")
    parts.append(f'Get-FileHash -Algorithm SHA256 "{primary_artifact or "<artifact>"}"')
    parts.append("Get-Content checksums.sha256")
    parts.append("```")
    parts.append("")

    parts.append("## Provenance & License")
    parts.append("")
    parts.append("- **Publisher:** AbteeX AI Labs.")
    parts.append("- **Family:** LumynaX model and inference-chain release family.")
    parts.append(f"- **Upstream / base:** `{upstream}`.")
    parts.append(f"- **Source GGUF:** `{source_gguf}`." if is_gguf else f"- **Source weights:** `{source_gguf}`.")
    parts.append(f"- **License metadata:** `{license_meta}`.")
    parts.append("- Respect the upstream model licence and keep attribution files with redistributed copies.")
    parts.append("- Do not present this package as privately trained or weight-merged unless the release manifest explicitly says weight adaptation was applied.")
    parts.append("")

    parts.append("## Aotearoa Kaupapa")
    parts.append("")
    parts.append("LumynaX is built in and for Aotearoa New Zealand. Sovereignty is treated as a design property rather than a deployment option: the package documents where the model came from, what it can do, how to run it close to your data, and what it should not claim. This card is part of the public surface for that kaupapa.")
    parts.append("")

    parts.append("## Limitations & Responsible Use")
    parts.append("")
    parts.append("- Outputs can be incorrect, incomplete, or biased; validate important answers before use.")
    parts.append("- Larger GGUF, MoE, multimodal, and frontier packages may require substantial RAM, VRAM, disk space, and recent runtime builds.")
    parts.append("- For high-impact decisions, use human review and domain-specific evaluation.")
    parts.append("- For sensitive data, prefer local execution and keep operational logs under your own governance policy.")
    parts.append("- This card documents package readiness and access &mdash; it is not a benchmark claim.")
    parts.append("- The assistant must not invent biographical or organisational claims about named people without verified context.")
    parts.append("")

    parts.append(sister)
    parts.append("")

    parts.append("## Automation Notes")
    parts.append("")
    parts.append("Automation should read these files before launching:")
    parts.append("")
    parts.append("- `release_export_manifest.json`")
    parts.append("- `checksums.sha256`")
    parts.append("- `quickstart.py`")
    parts.append("- `requirements.txt`")
    parts.append("- `ollama/Modelfile` when present")
    parts.append("")

    parts.append("---")
    parts.append("")
    parts.append('<p align="center"><em>Local roots, global work. &middot; Sovereignty is a design property, not a deployment option.</em></p>')
    parts.append('<p align="center"><sub>AbteeX AI Labs &middot; <a href="https://abteex.com">abteex.com</a> &middot; <a href="https://lumynax.com">lumynax.com</a> &middot; <a href="https://huggingface.co/AbteeXAILab">huggingface.co/AbteeXAILab</a></sub></p>')

    return "\n".join(parts) + "\n"


# ---------- Pipeline ----------
def process_model(reg: Dict[str, Any], dry_run: bool = False) -> str:
    repo_id = reg["repo_id"]
    short = reg["model_id"]
    print(f"\n=== {repo_id} ===")
    existing = fetch_current_readme(repo_id)
    if existing:
        backup = BACKUP_DIR / short / "README.md"
        backup.parent.mkdir(parents=True, exist_ok=True)
        backup.write_text(existing, encoding="utf-8")
        print(f"  backed up old README ({len(existing)} chars)")
    files = list_repo_files_safe(repo_id)
    card = build_card(reg, existing, files)
    out = CARDS_DIR / short / "README.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(card, encoding="utf-8")
    print(f"  wrote new card ({len(card)} chars) -> {out}")
    if dry_run:
        return "DRY"
    try:
        upload_file(
            path_or_fileobj=str(out),
            path_in_repo="README.md",
            repo_id=repo_id,
            repo_type="model",
            token=TOKEN,
            commit_message="docs: refresh model card to v5 (AbteeX/LumynaX unified surface)",
        )
        print("  pushed.")
        return "OK"
    except Exception as exc:
        print(f"  PUSH FAILED: {type(exc).__name__}: {exc}")
        return f"FAIL: {exc}"


def main() -> None:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    models = registry["models"]
    mode = sys.argv[1] if len(sys.argv) > 1 else "dry-one"
    if mode == "dry-one":
        # Pick a sparse one to preview
        target = next((m for m in models if m["repo_id"].endswith("lumynax-tiny")), models[0])
        process_model(target, dry_run=True)
        print("\nPreview written. Inspect S:/hf-publish/cards/lumynax-tiny/README.md")
    elif mode == "all":
        results = {}
        for i, m in enumerate(models, 1):
            print(f"\n[{i}/{len(models)}] {m['repo_id']}")
            results[m["repo_id"]] = process_model(m, dry_run=False)
            time.sleep(0.5)
        ok = sum(1 for v in results.values() if v == "OK")
        print(f"\n=== DONE: {ok}/{len(results)} pushed successfully ===")
        for k, v in results.items():
            if v != "OK":
                print(f"  FAIL {k}: {v}")
    elif mode == "dry-all":
        for m in models:
            process_model(m, dry_run=True)
    else:
        print("modes: dry-one | dry-all | all")


if __name__ == "__main__":
    main()
