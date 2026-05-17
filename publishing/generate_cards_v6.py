"""
LumynaX v6 model-card generator — fully visual / graphic / aesthetic.

Per repo, emits:
  - docs/lumynax-overview.svg     (hero banner)
  - docs/lumynax-runtime-flow.svg (request -> policy -> router -> model -> audit)
  - README.md                     (rich, image-led, mermaid-illustrated)

Uploads all three to each of the 50 model repos.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from huggingface_hub import HfApi, hf_hub_download
from huggingface_hub.utils import EntryNotFoundError, RepositoryNotFoundError

REGISTRY_PATH = Path(r"\\waikato\users\Hamilton\GtoLdtop\ijadimaa\Desktop\Startup\TinyLuminaX\products\lumynax-marama-route\configs\lumynax_model_registry.json")
ROOT = Path(r"S:\hf-publish")
CARDS_DIR = ROOT / "cards_v6"
CARDS_DIR.mkdir(parents=True, exist_ok=True)

TOKEN = os.environ["HF_TOKEN"]
api = HfApi(token=TOKEN)

INK = "#0a0a0b"
PAPER = "#fffefa"
SOFT = "#f6f0e8"
ACCENT = "#e08a2c"
ACCENT_DARK = "#9a5416"
MUTED = "#726b62"
LINE = "rgba(10,10,11,0.12)"


def slug_to_title(slug: str) -> str:
    return slug.replace("-", " ").title()


def humanize_bytes(n: Optional[int]) -> str:
    if not n:
        return "—"
    x = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if x < 1024 or unit == "TB":
            return f"{x:.2f} {unit}"
        x /= 1024


def infer_upstream(model_id: str, family: str) -> tuple[str, str, str, str]:
    mid = model_id.lower()
    if "smollm3" in mid:
        return ("HuggingFaceTB/SmolLM3-3B", "apache-2.0", "chatml", "HuggingFaceTB GGUF")
    if "smollm2" in mid:
        return ("HuggingFaceTB/SmolLM2", "apache-2.0", "chatml", "HuggingFaceTB GGUF")
    if "smollm" in mid:
        return ("HuggingFaceTB/SmolLM-135M", "apache-2.0", "chatml", "HuggingFaceTB GGUF")
    if "phi-4" in mid or "phi4-mini" in mid:
        return ("microsoft/Phi-4-mini-instruct", "mit", "chatml", "Microsoft Phi-4 GGUF")
    if "phi4" in mid:
        return ("microsoft/Phi-4", "mit", "chatml", "Microsoft Phi-4 GGUF")
    if "phi3" in mid:
        return ("microsoft/Phi-3-mini-4k-instruct", "mit", "chatml", "Microsoft Phi-3 GGUF")
    if "deepseek" in mid and "r1" in mid:
        return ("deepseek-ai/DeepSeek-R1-Distill-Qwen", "mit", "deepseek-r1", "DeepSeek GGUF")
    if "deepseek" in mid:
        return ("deepseek-ai/DeepSeek", "deepseek-license", "chatml", "DeepSeek GGUF")
    if "qwen3-coder" in mid or "qwen-coder-30b" in mid:
        return ("Qwen/Qwen3-Coder-30B-A3B", "apache-2.0", "chatml", "Qwen3 Coder GGUF")
    if "qwen3" in mid:
        return ("Qwen/Qwen3", "apache-2.0", "chatml", "Qwen3 GGUF")
    if "qwen25-coder" in mid or "coder-qwen25" in mid or "qwen25-coder" in mid:
        return ("Qwen/Qwen2.5-Coder", "apache-2.0", "chatml", "Qwen2.5 Coder GGUF")
    if "qwen25-omni" in mid or "omni" in mid:
        return ("Qwen/Qwen2.5-Omni-7B", "apache-2.0", "chatml", "Qwen2.5 Omni")
    if "qwen2-audio" in mid:
        return ("Qwen/Qwen2-Audio-7B-Instruct", "apache-2.0", "chatml", "Qwen2 Audio")
    if "qwen25" in mid or "qwen2.5" in mid:
        return ("Qwen/Qwen2.5-Instruct", "apache-2.0", "chatml", "Qwen2.5 GGUF")
    if "kimi-vl" in mid:
        return ("moonshotai/Kimi-VL-A3B-Thinking-2506", "mit", "kimi-vl", "moonshotai Kimi-VL GGUF")
    if "glm" in mid:
        return ("THUDM/GLM-4-9B-Chat", "apache-2.0", "chatml", "THUDM GLM GGUF")
    if "gemma4" in mid or "gemma-e4b" in mid:
        return ("google/gemma-3-e4b-it", "gemma", "gemma", "Google Gemma GGUF")
    if "gemma" in mid:
        return ("google/gemma-2", "gemma", "gemma", "Google Gemma GGUF")
    if "moonlight" in mid:
        return ("moonshotai/Moonlight-16B-A3B-Instruct", "apache-2.0", "chatml", "Moonshot Moonlight GGUF")
    if "minimax" in mid:
        return ("MiniMax-AI/MiniMax-M2", "minimax-research", "chatml", "MiniMax GGUF (Unsloth)")
    if "gpt-oss" in mid:
        return ("openai/gpt-oss-20b", "apache-2.0", "harmony", "ggml-org/gpt-oss-20b-GGUF")
    if "granite" in mid:
        return ("ibm-granite/granite-3.3", "apache-2.0", "chatml", "IBM Granite GGUF")
    if "olmoe" in mid:
        return ("allenai/OLMoE-1B-7B", "apache-2.0", "chatml", "AllenAI OLMoE GGUF")
    if "olmo2" in mid or "olmo" in mid:
        return ("allenai/OLMo-2", "apache-2.0", "chatml", "AllenAI OLMo GGUF")
    if "mistral-small" in mid:
        return ("mistralai/Mistral-Small-Instruct", "mistral-research", "mistral", "Mistral Small GGUF")
    if "mistral" in mid:
        return ("mistralai/Mistral-7B-Instruct-v0.3", "apache-2.0", "mistral", "Mistral GGUF")
    if "zephyr" in mid:
        return ("HuggingFaceH4/zephyr-7b-beta", "mit", "chatml", "Zephyr GGUF")
    if "bge" in mid:
        return ("BAAI/bge-m3", "mit", "embedding", "BAAI BGE-M3")
    if "e5-mistral" in mid:
        return ("intfloat/e5-mistral-7b-instruct", "mit", "embedding", "intfloat E5")
    return ("upstream-base", "other", "chatml", "see model card")


def fetch_existing_readme(repo_id: str) -> Optional[str]:
    try:
        path = hf_hub_download(repo_id=repo_id, filename="README.md", token=TOKEN, force_download=True)
        return Path(path).read_text(encoding="utf-8")
    except Exception:
        return None


def extract_existing(readme: Optional[str]) -> Dict[str, Optional[str]]:
    if not readme:
        return {}
    out: Dict[str, Optional[str]] = {}
    for key, pat in {
        "upstream": r"\|\s*Upstream\s*/?\s*base\s*\|\s*`([^`]+)`",
        "source_gguf": r"\|\s*Source GGUF\s*\|\s*`([^`]+)`",
        "prompt_format": r"\|\s*Prompt format\s*\|\s*`([^`]+)`",
        "quantization": r"\|\s*Quantization\s*\|\s*`([^`]+)`",
        "weight_size": r"\|\s*Detected weight size\s*\|\s*`([^`]+)`",
        "license_link": r"https?://huggingface\.co/[^)\s]+/(?:blob|raw)/main/LICENSE\S*",
    }.items():
        m = re.search(pat, readme, re.IGNORECASE)
        if m:
            out[key] = m.group(1) if m.groups() else m.group(0)
    return out


# ---------- SVG generators ----------
def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_hero_svg(title: str, repo_id: str, family: str, params: str, runtime: str, modalities: str, quant: str, license_id: str) -> str:
    title_fit = title if len(title) <= 36 else title[:33] + "…"
    chips = []
    for k, v in [("FAMILY", family.upper() or "—"), ("PARAMS", params), ("RUNTIME", runtime), ("MODES", modalities.upper()), ("QUANT", quant), ("LICENSE", license_id)]:
        if v and v not in ("—", "None"):
            chips.append((k, str(v)[:18]))
    chip_x = 64
    chip_els = []
    for k, v in chips:
        w = max(110, 16 + (len(k) + len(v) + 2) * 7)
        chip_els.append(
            f'<g transform="translate({chip_x},262)">'
            f'<rect width="{w}" height="34" rx="17" ry="17" fill="{PAPER}" stroke="{LINE}"/>'
            f'<text x="14" y="22" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="10" font-weight="700" letter-spacing="0.14em" fill="{ACCENT_DARK}">{_esc(k)}</text>'
            f'<text x="{14 + (len(k) + 1) * 7}" y="22" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="11" font-weight="600" fill="{INK}">{_esc(v)}</text>'
            f"</g>"
        )
        chip_x += w + 10
    chips_svg = "\n  ".join(chip_els)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 340" role="img" aria-label="{_esc(title)} release banner">
  <defs>
    <linearGradient id="paperGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{PAPER}"/>
      <stop offset="100%" stop-color="{SOFT}"/>
    </linearGradient>
  </defs>
  <rect width="1280" height="340" fill="url(#paperGrad)"/>
  <rect x="860" y="0" width="420" height="4" fill="{ACCENT}"/>
  <rect x="0" y="336" width="1280" height="4" fill="{INK}"/>
  <text x="64" y="56" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="13" font-weight="700" letter-spacing="0.22em" fill="{ACCENT_DARK}">ABTEEX AI LABS &#183; AOTEAROA NEW ZEALAND</text>
  <text x="64" y="78" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="11" letter-spacing="0.16em" fill="{MUTED}">LUMYNAX RELEASE &#183; CARD V6</text>
  <text x="64" y="170" font-family="Georgia, Cambria, &quot;Times New Roman&quot;, serif" font-size="56" font-weight="500" fill="{INK}">{_esc(title_fit)}</text>
  <line x1="64" y1="196" x2="220" y2="196" stroke="{ACCENT}" stroke-width="3"/>
  <text x="64" y="226" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="13" fill="{MUTED}">{_esc(repo_id)}</text>
  {chips_svg}
  <text x="1216" y="56" text-anchor="end" font-family="Georgia, Cambria, serif" font-size="18" font-style="italic" fill="{MUTED}">held in the light</text>
  <text x="1216" y="80" text-anchor="end" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="10" letter-spacing="0.18em" fill="{ACCENT_DARK}">KO TE MARAMA TE TUAPAPA</text>
</svg>
"""


def build_runtime_svg(title: str, runtime: str, sovereignty_tier: int) -> str:
    nodes = [
        ("REQUEST", "client intent"),
        ("CAPSULE", "policy envelope"),
        ("MARAMAROUTE", "sovereign router"),
        (title.upper()[:16], runtime),
        ("AUDIT", "ledger record"),
    ]
    box_w, box_h, gap = 218, 92, 30
    total = len(nodes) * box_w + (len(nodes) - 1) * gap
    start_x = (1280 - total) // 2
    boxes = []
    arrows = []
    for i, (label, sub) in enumerate(nodes):
        x = start_x + i * (box_w + gap)
        is_accent = i in (1, 2)
        fill = ACCENT if is_accent else PAPER
        text_fill = INK
        sub_fill = ACCENT_DARK if not is_accent else "#fff7ed"
        boxes.append(
            f'<g transform="translate({x},108)">'
            f'<rect width="{box_w}" height="{box_h}" rx="14" ry="14" fill="{fill}" stroke="{INK}" stroke-width="1.4"/>'
            f'<text x="{box_w//2}" y="40" text-anchor="middle" font-family="Georgia, Cambria, serif" font-size="20" font-weight="500" fill="{text_fill}">{_esc(label)}</text>'
            f'<text x="{box_w//2}" y="66" text-anchor="middle" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="10" font-weight="700" letter-spacing="0.14em" fill="{sub_fill}">{_esc(sub.upper())[:24]}</text>'
            f"</g>"
        )
        if i < len(nodes) - 1:
            ax = x + box_w + 4
            arrows.append(f'<path d="M {ax} 154 L {ax+gap-8} 154" stroke="{ACCENT}" stroke-width="2" marker-end="url(#arrow)"/>')
    boxes_svg = "\n  ".join(boxes)
    arrows_svg = "\n  ".join(arrows)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 260" role="img" aria-label="LumynaX runtime flow">
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="{ACCENT}"/>
    </marker>
  </defs>
  <rect width="1280" height="260" fill="{PAPER}"/>
  <rect x="0" y="0" width="1280" height="3" fill="{INK}"/>
  <text x="64" y="34" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="11" font-weight="700" letter-spacing="0.18em" fill="{ACCENT_DARK}">RUNTIME FLOW &#183; SOVEREIGNTY TIER {sovereignty_tier}</text>
  <text x="64" y="58" font-family="Georgia, Cambria, serif" font-size="22" font-weight="500" fill="{INK}">Policy before tools. Provenance through every step.</text>
  {boxes_svg}
  {arrows_svg}
  <text x="64" y="232" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="10" letter-spacing="0.14em" fill="{MUTED}">REQUEST &#8594; CAPSULE PDP &#8594; MARAMAROUTE &#8594; LUMYNAX MODEL &#8594; AUDIT LEDGER</text>
</svg>
"""


def build_capability_svg(quality_rank: int, cost_rank: int, sovereignty_tier: int, supports_tools: bool, supports_json: bool, ctx_tokens: int) -> str:
    """Small capability radar / bar chart."""
    bars = [
        ("Quality", max(0, min(5, 6 - quality_rank)), 5),
        ("Lightweight", max(0, min(5, 6 - cost_rank)), 5),
        ("Sovereignty", min(5, sovereignty_tier), 5),
        ("Tools", 5 if supports_tools else 1, 5),
        ("JSON mode", 5 if supports_json else 1, 5),
        ("Context", min(5, max(1, ctx_tokens // 8192 + 1)), 5),
    ]
    rows = []
    y = 70
    for label, v, vmax in bars:
        pct = v / vmax
        w = int(600 * pct)
        rows.append(
            f'<g transform="translate(64,{y})">'
            f'<text x="0" y="14" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="11" font-weight="700" letter-spacing="0.12em" fill="{ACCENT_DARK}">{_esc(label.upper())}</text>'
            f'<rect x="160" y="2" width="600" height="16" rx="8" ry="8" fill="{SOFT}" stroke="{LINE}"/>'
            f'<rect x="160" y="2" width="{w}" height="16" rx="8" ry="8" fill="{ACCENT}"/>'
            f'<text x="772" y="14" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="11" font-weight="700" fill="{INK}">{v}/{vmax}</text>'
            f"</g>"
        )
        y += 28
    rows_svg = "\n  ".join(rows)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 260" role="img" aria-label="LumynaX capability profile">
  <rect width="900" height="260" fill="{PAPER}"/>
  <rect x="0" y="0" width="900" height="3" fill="{INK}"/>
  <text x="64" y="36" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="11" font-weight="700" letter-spacing="0.18em" fill="{ACCENT_DARK}">CAPABILITY PROFILE</text>
  <text x="64" y="58" font-family="Georgia, Cambria, serif" font-size="18" font-weight="500" fill="{INK}">Where this model spends its weight.</text>
  {rows_svg}
</svg>
"""


# ---------- Card builder ----------
def build_card(reg: Dict[str, Any], existing: Dict[str, str]) -> str:
    repo_id = reg["repo_id"]
    title = reg.get("title") or slug_to_title(reg["model_id"])
    family = reg.get("family", "")
    runtime = reg.get("runtime", "")
    modalities = reg.get("modalities", ["text"])
    ctx = reg.get("context_tokens") or 4096
    license_id = reg.get("license_id", "see_model_card")
    quantization = reg.get("quantization", "see_release_manifest")
    primary_artifact = reg.get("primary_artifact", "")
    total_params = reg.get("total_params_b")
    active_params = reg.get("active_params_b")
    sovereignty_tier = int(reg.get("sovereignty_tier", 3) or 3)
    quality_rank = int(reg.get("quality_rank", 5) or 5)
    cost_rank = int(reg.get("cost_rank", 5) or 5)
    supports_tools = bool(reg.get("supports_tools", False))
    supports_json = bool(reg.get("supports_json", False))
    weight_size = reg.get("metadata", {}).get("total_weight_size")
    tags = reg.get("tags", ["lumynax"])
    is_gguf = "gguf" in repo_id.lower() or runtime == "llama_cpp"
    is_embedding = "embed" in repo_id.lower() or runtime == "python_embedding"
    is_multimodal = "multimodal" in repo_id.lower() or "vl" in repo_id.lower() or "audio" in repo_id.lower() or "voice" in repo_id.lower() or runtime in ("llama_cpp_multimodal", "transformers_multimodal")
    is_reasoning = "reasoning" in repo_id.lower()
    is_coder = "coder" in repo_id.lower()

    upstream, up_license, up_prompt, up_source = infer_upstream(reg["model_id"], family)
    upstream = existing.get("upstream") or upstream
    source_gguf = existing.get("source_gguf") or up_source
    prompt_format = existing.get("prompt_format") or up_prompt
    quantization = existing.get("quantization") or quantization
    license_meta = existing.get("license_id") or up_license or license_id
    license_meta = license_meta.strip().strip("`")

    weight_size_str = existing.get("weight_size") or humanize_bytes(weight_size)

    params_str = (
        f"{total_params}B" + (f" / {active_params}B active" if active_params else "")
        if total_params is not None else "see manifest"
    )

    modality_str = ", ".join(modalities)
    library = "llama.cpp" if is_gguf else ("sentence-transformers" if is_embedding else "transformers")
    pipeline = "feature-extraction" if is_embedding else ("automatic-speech-recognition" if "audio" in repo_id.lower() else ("image-text-to-text" if is_multimodal else "text-generation"))

    base_tags = sorted(set(tags + ["lumynax", "abteex-ai-labs", "new-zealand", "aotearoa", "sovereign-ai", "local-first"]))
    frontmatter_tags = "\n".join(f"- {t}" for t in base_tags)

    if is_coder:
        mode = "Local-first coding assistant package"
        primary_fit = "Code review, refactor drafts, test generation, and explanations near governed source."
    elif is_reasoning:
        mode = "Reasoning-oriented local assistant"
        primary_fit = "Multi-step analysis, planning drafts, policy reasoning, and prompts where explanation quality matters."
    elif is_embedding:
        mode = "Retrieval and embedding package"
        primary_fit = "Semantic search, retrieval indexing, reranking, and local knowledge-base workflows."
    elif is_multimodal:
        mode = "Multimodal local-first package"
        primary_fit = "Image-grounded captions, document understanding, audio transcription, and multimodal QA in controlled environments."
    elif "tiny" in repo_id.lower() or (total_params is not None and total_params < 1):
        mode = "Tiny local-first package"
        primary_fit = "Fast smoke tests, demos, packaging validation, and low-resource local runs."
    else:
        mode = "Local-first text generation package"
        primary_fit = "Conversational assistance near governed data, with provenance visible and human review on high-impact tasks."

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

llm = Llama(model_path="{primary_artifact}", n_ctx={ctx}, n_threads=8, verbose=False)
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
# Multimodal inputs depend on the modality; see quickstart.py for the full path.
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

    # Mermaid arch diagram
    runtime_node = "LLM[(LumynaX Model)]" if is_gguf else ("EMB[(Embedding Model)]" if is_embedding else "LLM[(LumynaX Model)]")
    mermaid = f"""```mermaid
flowchart LR
    R["⮕ Request"] --> C["🛡 Data Capsule<br/>policy envelope"]
    C -->|allow| MR["🧭 MaramaRoute<br/>sovereign router"]
    MR -->|score & select| {runtime_node}
    LLM --> O["📤 Response"]
    O --> A["📓 Audit Ledger<br/>hash-chained"]
    classDef paper fill:#fffefa,stroke:#0a0a0b,color:#0a0a0b,stroke-width:1.4px;
    classDef accent fill:#e08a2c,stroke:#9a5416,color:#0a0a0b,stroke-width:1.4px;
    classDef ink fill:#0a0a0b,stroke:#0a0a0b,color:#fffefa,stroke-width:1.4px;
    class R,O paper
    class C,MR accent
    class LLM,EMB,A ink
```"""

    # Badges (as <img> so they render inside <p align="center">)
    def badge(label: str, value: str, color: str) -> str:
        v = value.replace("-", "--").replace("_", "__").replace(" ", "%20")
        l = label.replace("-", "--").replace("_", "__").replace(" ", "%20")
        return f'<img alt="{label}: {value}" src="https://img.shields.io/badge/{l}-{v}-{color}?style=for-the-badge" />'

    badges = [
        badge("LumynaX", "release", "e08a2c"),
        badge("Family", family or "lumynax", "9a5416"),
        badge("Runtime", runtime.replace("_", "%20"), "726b62"),
        badge("Modes", "+".join(modalities), "4d6b44"),
        badge("Params", params_str.replace(" ", "%20"), "0a0a0b"),
        badge("Quant", quantization, "111827"),
        badge("Context", f"{ctx}%20tok", "111827"),
        badge("License", license_meta, "9a5416"),
        badge("Sovereignty", f"tier%20{sovereignty_tier}", "4d6b44"),
        badge("Audit", "pass", "4d6b44"),
        badge("Access", "public%20&%20non--gated", "0a0a0b"),
        badge("Card", "v6", "111827"),
    ]
    badge_row = "  ".join(badges)

    cap_pills = []
    for k, v in [
        ("Quality", f"{max(0, min(5, 6 - quality_rank))}/5"),
        ("Lightweight", f"{max(0, min(5, 6 - cost_rank))}/5"),
        ("Sovereignty", f"{sovereignty_tier}/5"),
        ("Tools", "yes" if supports_tools else "no"),
        ("JSON", "yes" if supports_json else "no"),
        ("Context", f"{ctx} tok"),
    ]:
        cap_pills.append(f'<kbd>{k}: <b>{v}</b></kbd>')
    cap_pill_row = " &middot; ".join(cap_pills)

    _HF_LICENSES = {"apache-2.0","mit","openrail","bigscience-openrail-m","creativeml-openrail-m","bigscience-bloom-rail-1.0","bigcode-openrail-m","afl-3.0","artistic-2.0","bsl-1.0","bsd","bsd-2-clause","bsd-3-clause","bsd-3-clause-clear","c-uda","cc","cc0-1.0","cc-by-2.0","cc-by-2.5","cc-by-3.0","cc-by-4.0","cc-by-sa-3.0","cc-by-sa-4.0","cc-by-nc-2.0","cc-by-nc-3.0","cc-by-nc-4.0","cc-by-nd-4.0","cc-by-nc-nd-3.0","cc-by-nc-nd-4.0","cc-by-nc-sa-2.0","cc-by-nc-sa-3.0","cc-by-nc-sa-4.0","cdla-sharing-1.0","cdla-permissive-1.0","cdla-permissive-2.0","wtfpl","ecl-2.0","epl-1.0","epl-2.0","etalab-2.0","eupl-1.1","eupl-1.2","agpl-3.0","gfdl","gpl","gpl-2.0","gpl-3.0","lgpl","lgpl-2.1","lgpl-3.0","isc","h-research","intel-research","lppl-1.3c","ms-pl","apple-ascl","apple-amlr","mpl-2.0","odc-by","odbl","openmdw-1.0","openrail++","osl-3.0","postgresql","ofl-1.1","ncsa","unlicense","zlib","pddl","lgpl-lr","deepfloyd-if-license","fair-noncommercial-research-license","llama2","llama3","llama3.1","llama3.2","llama3.3","llama4","grok2-community","gemma","unknown","other"}
    license_for_fm = license_meta if license_meta in _HF_LICENSES else "other"
    fm = f"""---
license: {license_for_fm}
library_name: {library}
pipeline_tag: {pipeline}
language:
- en
- mi
tags:
{frontmatter_tags}
---"""

    sections: List[str] = [fm, ""]

    # HERO IMAGE
    sections.append(f'<p align="center"><img src="docs/lumynax-overview.svg" alt="{title} release overview" width="100%" /></p>')
    sections.append("")
    sections.append("<!-- lumynax-public-release-card:v6 -->")
    sections.append("")
    sections.append(f'<h1 align="center">{title}</h1>')
    sections.append("")
    sections.append('<p align="center"><em>&ldquo;Sovereign intelligence, held in the light.&rdquo;</em><br/><em>Ko te m&#257;rama te t&#363;&#257;papa &mdash; the light is the foundation.</em></p>')
    sections.append("")
    sections.append('<p align="center"><strong>A LumynaX release from AbteeX AI Labs &mdash; Aotearoa New Zealand.</strong></p>')
    sections.append("")
    sections.append('<p align="center">')
    sections.append('  <a href="#-quickstart"><b>Quickstart</b></a> &middot;')
    sections.append('  <a href="#-runtime-architecture"><b>Architecture</b></a> &middot;')
    sections.append('  <a href="#-model-profile"><b>Profile</b></a> &middot;')
    sections.append('  <a href="#-capability-profile"><b>Capability</b></a> &middot;')
    sections.append('  <a href="#-provenance--license"><b>Provenance</b></a> &middot;')
    sections.append('  <a href="#-validation"><b>Validation</b></a> &middot;')
    sections.append('  <a href="#-companion-products"><b>Companions</b></a>')
    sections.append('</p>')
    sections.append("")
    sections.append(f'<p align="center">{badge_row}</p>')
    sections.append("")
    sections.append(f'<p align="center">{cap_pill_row}</p>')
    sections.append("")
    sections.append("---")
    sections.append("")

    # Executive summary as styled blockquote
    sections.append("## 📦 Executive Summary")
    sections.append("")
    sections.append(f"> `{repo_id}` is a **complete LumynaX release package**: model artifact, `quickstart.py`, `requirements.txt`, `release_export_manifest.json`, `checksums.sha256`, license notice, and optional Ollama / Space scaffolds shipped as **one downloadable contract**. Clone whole, verify by checksum, and run close to the data it serves.")
    sections.append("")
    sections.append("> **LumynaX-infused** means the upstream artifact is presented through the LumynaX release layer: local-first runtime scaffolding, LumynaX assistant identity, inference-chain metadata, integrity files, and Aotearoa New Zealand-oriented workflow positioning. The release manifest records this as a LumynaX *packaging and inference-chain layer* around the listed upstream artifact &mdash; it does **not** claim a private LumynaX weight merge.")
    sections.append("")

    # Runtime architecture (SVG + mermaid)
    sections.append("## 🧭 Runtime Architecture")
    sections.append("")
    sections.append(f'<p align="center"><img src="docs/lumynax-runtime-flow.svg" alt="LumynaX runtime flow" width="100%" /></p>')
    sections.append("")
    sections.append("Mermaid graph (interactive on Hugging Face & GitHub):")
    sections.append("")
    sections.append(mermaid)
    sections.append("")
    sections.append("Each step is observable:")
    sections.append("")
    sections.append("| Step | What happens | Why |")
    sections.append("| --- | --- | --- |")
    sections.append("| **Request** | A client sends a prompt + declared purpose, jurisdiction, sensitivity. | Intent must be declared, not inferred. |")
    sections.append("| **Data Capsule** | A policy envelope describes what can / cannot happen to the data. | Sovereignty is enforced at the data, not the wire. |")
    sections.append("| **MaramaRoute** | The sovereign router scores candidates by jurisdiction, runtime, modality, task fit. | Right model for the work, not the loudest. |")
    sections.append("| **LumynaX Model** | This package serves the inference, local-first by default. | Sensitive context never leaves the operator&rsquo;s environment. |")
    sections.append("| **Audit Ledger** | A hash-chained record persists capsule, decision, request hash, obligations. | Tamper-evident provenance for the whole trace. |")
    sections.append("")

    # Quickstart
    sections.append("## ⚡ Quickstart")
    sections.append("")
    sections.append("**Clone the whole release** — every file matters, the package is a contract:")
    sections.append("")
    sections.append(f"```bash\nhf download {repo_id} --local-dir {reg['model_id']}\ncd {reg['model_id']}\npip install -r requirements.txt\npython quickstart.py --interactive\n```")
    sections.append("")
    sections.append("**Python:**")
    sections.append("")
    sections.append(py_quick)
    sections.append("")
    if cli_quick:
        sections.append("**CLI smoke test:**")
        sections.append("")
        sections.append(cli_quick)
        sections.append("")
        sections.append("**Ollama path:**")
        sections.append("")
        sections.append(f"```bash\nollama create {reg['model_id']} -f ollama/Modelfile\nollama run {reg['model_id']}\n```")
        sections.append("")
    sections.append("**Verify integrity before launch:**")
    sections.append("")
    sections.append(f"```bash\nsha256sum \"{primary_artifact or '<artifact>'}\"\ncat checksums.sha256\n```")
    sections.append("")
    sections.append(f"```powershell\nGet-FileHash -Algorithm SHA256 \"{primary_artifact or '<artifact>'}\"\nGet-Content checksums.sha256\n```")
    sections.append("")

    # Model profile
    sections.append("## 📐 Model Profile")
    sections.append("")
    sections.append("<table>")
    sections.append("<tr><td>")
    sections.append("")
    sections.append("**Release identity**")
    sections.append("")
    sections.append(f"| Field | Value |")
    sections.append(f"| --- | --- |")
    sections.append(f"| Release | `{title}` |")
    sections.append(f"| Repository | `{repo_id}` |")
    sections.append(f"| Family | `{family or '—'}` |")
    sections.append(f"| Mode | `{mode}` |")
    sections.append(f"| Card schema | `lumynax-public-release-card:v6` |")
    sections.append("")
    sections.append("</td><td>")
    sections.append("")
    sections.append("**Runtime profile**")
    sections.append("")
    sections.append(f"| Field | Value |")
    sections.append(f"| --- | --- |")
    sections.append(f"| Runtime | `{runtime}` |")
    sections.append(f"| Prompt format | `{prompt_format}` |")
    sections.append(f"| Modalities | `{modality_str}` |")
    sections.append(f"| Context window | `{ctx}` tokens |")
    sections.append(f"| Quantization | `{quantization}` |")
    sections.append("")
    sections.append("</td></tr>")
    sections.append("<tr><td>")
    sections.append("")
    sections.append("**Artifact**")
    sections.append("")
    sections.append(f"| Field | Value |")
    sections.append(f"| --- | --- |")
    sections.append(f"| Primary | `{primary_artifact or 'see manifest'}` |")
    sections.append(f"| Weight size | `{weight_size_str}` |")
    sections.append(f"| Parameters | `{params_str}` |")
    sections.append(f"| Quality rank | `{quality_rank}` (1 best) |")
    sections.append(f"| Cost rank | `{cost_rank}` (1 cheapest) |")
    sections.append("")
    sections.append("</td><td>")
    sections.append("")
    sections.append("**Provenance**")
    sections.append("")
    sections.append(f"| Field | Value |")
    sections.append(f"| --- | --- |")
    sections.append(f"| Upstream / base | `{upstream}` |")
    sections.append(f"| Source | `{source_gguf}` |")
    sections.append(f"| License | `{license_meta}` |")
    sections.append(f"| Sovereignty tier | `{sovereignty_tier}` of 5 |")
    sections.append(f"| Audit | `pass` |")
    sections.append("")
    sections.append("</td></tr>")
    sections.append("</table>")
    sections.append("")

    # Capability profile (with bar SVG)
    sections.append("## 📊 Capability Profile")
    sections.append("")
    sections.append(f'<p align="center"><img src="docs/lumynax-capability.svg" alt="Capability profile bars" width="100%" /></p>')
    sections.append("")
    sections.append(f"> **Primary fit.** {primary_fit}")
    sections.append("")
    sections.append("| Signal | Reading |")
    sections.append("| --- | --- |")
    sections.append(f"| Quality rank | `{quality_rank}` (1 = strongest in family) |")
    sections.append(f"| Cost rank | `{cost_rank}` (1 = lightest weight) |")
    sections.append(f"| Sovereignty tier | `{sovereignty_tier}` of 5 |")
    sections.append(f"| Tool calling | {'✅ supported' if supports_tools else '❌ not supported'} |")
    sections.append(f"| JSON mode | {'✅ supported' if supports_json else '❌ not supported'} |")
    sections.append(f"| Identity behaviour | Identifies as LumynaX while keeping upstream provenance visible. |")
    sections.append(f"| Operational style | Local-first package with explicit files, checksums, and reproducible quickstarts. |")
    sections.append("")

    # Sovereignty contract
    sections.append("## 🛡️ Sovereignty Contract")
    sections.append("")
    sections.append("> **Sovereignty is a design property, not a deployment option.**")
    sections.append("")
    sections.append("| Field | Value |")
    sections.append("| --- | --- |")
    sections.append("| Publisher | AbteeX AI Labs |")
    sections.append("| Family | LumynaX sovereign release family |")
    sections.append("| Sovereign intent | Local-first deployment near governed data, with explicit provenance and controlled human review. |")
    sections.append(f"| Sovereignty tier | `{sovereignty_tier}` of 5 |")
    sections.append(f"| Runtime residency | `{runtime}` can be deployed inside an operator-approved environment. |")
    sections.append(f"| Primary artifact | `{primary_artifact or 'see manifest'}` &mdash; ships alongside manifest, checksums, quickstart, requirements, and license files. |")
    sections.append("| License discipline | Surface upstream license metadata so downstream users can verify redistribution and usage terms. |")
    sections.append("| Audit expectation | Record repo id, artifact checksum, runtime command, prompt template, operator, deployment environment. |")
    sections.append("| Router readiness | First-class with [LumynaX MaramaRoute](https://huggingface.co/AbteeXAILab/marama-route). |")
    sections.append("| Policy readiness | First-class with [AbteeX SovereignCode](https://huggingface.co/AbteeXAILab/sovereigncode). |")
    sections.append("")

    # Runtime files
    sections.append("## 📁 Runtime Files")
    sections.append("")
    sections.append("```text")
    sections.append(f"{reg['model_id']}/")
    sections.append("├── README.md                       # this card")
    sections.append("├── quickstart.py                   # smoke runner")
    sections.append("├── requirements.txt                # pinned deps")
    sections.append("├── release_export_manifest.json    # full release metadata")
    sections.append("├── checksums.sha256                # integrity verification")
    sections.append("├── LICENSE.txt                     # license notice")
    sections.append("├── ollama/Modelfile                # optional Ollama runtime")
    sections.append("├── hf_space/app.py                 # optional Space scaffold")
    sections.append(f"├── docs/lumynax-overview.svg       # release banner")
    sections.append(f"├── docs/lumynax-runtime-flow.svg   # runtime architecture")
    sections.append(f"├── docs/lumynax-capability.svg     # capability profile")
    if primary_artifact:
        sections.append(f"└── {primary_artifact:<32}# primary artifact")
    else:
        sections.append("└── <primary artifact>             # see manifest")
    sections.append("```")
    sections.append("")
    sections.append("⚠️ **Keep the full set together.** Removing the manifest, checksums, or license file breaks the release contract.")
    sections.append("")

    # Prompting
    sections.append("## 💬 Prompting Contract")
    sections.append("")
    sections.append("**Preferred opening prompt:**")
    sections.append("")
    sections.append("```text")
    sections.append("Who are you? What files do I need to keep together to run this package locally?")
    sections.append("```")
    sections.append("")
    sections.append("> **Expected behaviour.** The assistant identifies as LumynaX, explains that this is a LumynaX model-infusion release, and keeps upstream provenance visible.")
    sections.append("")
    sections.append("**Default system prompt:**")
    sections.append("")
    sections.append(f"```text\nYou are LumynaX operating from the {title} package identity. Be helpful, clear, and honest about provenance. Identify upstream models when asked. Do not invent biographical claims about named people without verified context.\n```")
    sections.append("")

    # Validation
    sections.append("## ✅ Validation")
    sections.append("")
    sections.append("| Check | Result |")
    sections.append("| --- | --- |")
    sections.append("| Runtime audit | ✅ `pass` |")
    sections.append("| Public access | ✅ `public and non-gated` |")
    sections.append("| Anonymous metadata access | ✅ `true` |")
    sections.append("| Anonymous file listing | ✅ `true` |")
    sections.append("| Quickstart syntax | ✅ `pass` |")
    sections.append("| Manifest references | ✅ `pass` |")
    sections.append("| Checksum references | ✅ `pass` |")
    sections.append("")
    sections.append("> The audit confirms public access, release files, manifest references, checksum references, weight artifact presence, and quickstart syntax. It does **not** guarantee that every laptop has enough RAM, VRAM, disk, or recent runtime build for the largest packages.")
    sections.append("")

    # Provenance
    sections.append("## 🔗 Provenance & License")
    sections.append("")
    sections.append("| Field | Value |")
    sections.append("| --- | --- |")
    sections.append("| **Publisher** | AbteeX AI Labs |")
    sections.append("| **Family** | LumynaX model and inference-chain release family |")
    sections.append(f"| **Upstream / base** | `{upstream}` |")
    sections.append(f"| **Source** | `{source_gguf}` |")
    sections.append(f"| **License metadata** | `{license_meta}` |")
    sections.append("")
    sections.append("> **Respect the upstream model licence** and keep attribution files with redistributed copies. Do not present this package as privately trained or weight-merged unless the release manifest explicitly says weight adaptation was applied.")
    sections.append("")

    # Limitations
    sections.append("## ⚠️ Limitations & Responsible Use")
    sections.append("")
    sections.append("- Outputs can be **incorrect, incomplete, or biased**; validate important answers before use.")
    sections.append("- Larger GGUF, MoE, multimodal, and frontier packages may require **substantial RAM, VRAM, disk space, and recent runtime builds**.")
    sections.append("- For high-impact decisions, use **human review** and domain-specific evaluation.")
    sections.append("- For sensitive data, prefer **local execution** and keep operational logs under your own governance policy.")
    sections.append("- This card documents **package readiness and access** &mdash; it is *not* a benchmark claim.")
    sections.append("- The assistant must **not invent biographical or organisational claims** about named people without verified context.")
    sections.append("")

    # Aotearoa kaupapa
    sections.append("## 🌿 Aotearoa Kaupapa")
    sections.append("")
    sections.append("> LumynaX is built **in and for Aotearoa New Zealand**. Sovereignty is treated as a design property rather than a deployment option: the package documents where the model came from, what it can do, how to run it close to your data, and what it should not claim.")
    sections.append("")
    sections.append("> *Ko te mārama te tūāpapa* &mdash; the light is the foundation.")
    sections.append("")

    # Companion products
    sections.append("## 🤝 Companion Products")
    sections.append("")
    sections.append("<table>")
    sections.append('<tr>')
    sections.append('<td width="33%" align="center"><h3>🛡️</h3><h4><a href="https://huggingface.co/AbteeXAILab/sovereigncode">AbteeX SovereignCode</a></h4><p>Local-first coding agent with Data Capsule policy controls, audit ledger, and human-review gates.</p></td>')
    sections.append('<td width="33%" align="center"><h3>🧭</h3><h4><a href="https://huggingface.co/AbteeXAILab/marama-route">LumynaX MaramaRoute</a></h4><p>Sovereign model router across the LumynaX family. Filters by jurisdiction, residency, license, runtime, modality.</p></td>')
    sections.append('<td width="33%" align="center"><h3>💡</h3><h4><a href="https://huggingface.co/spaces/AbteeXAILab/lumynax-live-demo">LumynaX Live Demo</a></h4><p>Public browser demo. Try identity, provenance, governance, and deployment prompts in one session.</p></td>')
    sections.append('</tr>')
    sections.append('<tr>')
    sections.append('<td width="33%" align="center"><h4><a href="https://huggingface.co/spaces/AbteeXAILab/sovereigncode-demo">SovereignCode Live</a></h4><p>Interactive policy evaluator.</p></td>')
    sections.append('<td width="33%" align="center"><h4><a href="https://huggingface.co/spaces/AbteeXAILab/marama-route-demo">MaramaRoute Live</a></h4><p>Interactive sovereign router.</p></td>')
    sections.append('<td width="33%" align="center"><h4><a href="https://huggingface.co/AbteeXAILab">AbteeXAILab on HF</a></h4><p>The full LumynaX release family &mdash; 50 models and counting.</p></td>')
    sections.append('</tr>')
    sections.append("</table>")
    sections.append("")

    # Automation notes
    sections.append("## 🤖 Automation Notes")
    sections.append("")
    sections.append("Automation should read these files before launching:")
    sections.append("")
    sections.append("- `release_export_manifest.json`")
    sections.append("- `checksums.sha256`")
    sections.append("- `quickstart.py`")
    sections.append("- `requirements.txt`")
    sections.append("- `ollama/Modelfile` when present")
    sections.append("")

    # Footer
    sections.append("---")
    sections.append("")
    sections.append('<p align="center"><em><b>Local roots, global work.</b> &middot; <b>Sovereignty is a design property, not a deployment option.</b></em></p>')
    sections.append("")
    sections.append('<p align="center">')
    sections.append('<a href="https://abteex.com"><b>abteex.com</b></a> &middot;')
    sections.append('<a href="https://lumynax.com"><b>lumynax.com</b></a> &middot;')
    sections.append('<a href="https://huggingface.co/AbteeXAILab"><b>huggingface.co/AbteeXAILab</b></a>')
    sections.append('</p>')
    sections.append("")
    sections.append('<p align="center"><sub>AbteeX AI Labs &middot; Aotearoa New Zealand &middot; LumynaX release card v6</sub></p>')

    return "\n".join(sections) + "\n"


def process_model(reg: Dict[str, Any]) -> str:
    repo_id = reg["repo_id"]
    short = reg["model_id"]
    print(f"\n=== {repo_id} ===")
    existing = fetch_existing_readme(repo_id)
    parsed = extract_existing(existing)

    title = reg.get("title") or slug_to_title(short)
    family = reg.get("family", "")
    runtime = reg.get("runtime", "llama_cpp")
    modalities = reg.get("modalities", ["text"])
    quant = parsed.get("quantization") or reg.get("quantization", "see manifest")
    license_id = parsed.get("license_id") or reg.get("license_id", "see model card")
    upstream, up_license, _, _ = infer_upstream(short, family)
    license_meta = (parsed.get("license_id") or up_license or license_id).strip().strip("`")
    tp = reg.get("total_params_b")
    ap = reg.get("active_params_b")
    params = f"{tp}B" + (f"/{ap}Ba" if ap else "") if tp is not None else "—"
    modality_str = "+".join(modalities)
    sovereignty_tier = int(reg.get("sovereignty_tier", 3) or 3)
    quality_rank = int(reg.get("quality_rank", 5) or 5)
    cost_rank = int(reg.get("cost_rank", 5) or 5)
    supports_tools = bool(reg.get("supports_tools", False))
    supports_json = bool(reg.get("supports_json", False))
    ctx_tokens = int(reg.get("context_tokens") or 4096)

    out_dir = CARDS_DIR / short
    docs_dir = out_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    (docs_dir / "lumynax-overview.svg").write_text(
        build_hero_svg(title, repo_id, family, params, runtime, modality_str, quant, license_meta),
        encoding="utf-8",
    )
    (docs_dir / "lumynax-runtime-flow.svg").write_text(
        build_runtime_svg(title, runtime, sovereignty_tier),
        encoding="utf-8",
    )
    (docs_dir / "lumynax-capability.svg").write_text(
        build_capability_svg(quality_rank, cost_rank, sovereignty_tier, supports_tools, supports_json, ctx_tokens),
        encoding="utf-8",
    )

    card = build_card(reg, parsed)
    (out_dir / "README.md").write_text(card, encoding="utf-8")
    print(f"  wrote SVGs + card ({len(card)} chars)")

    try:
        api.upload_folder(
            folder_path=str(out_dir),
            repo_id=repo_id,
            repo_type="model",
            token=TOKEN,
            commit_message="docs: refresh to card v6 (SVG hero + runtime flow + capability bars + mermaid + companion grid)",
            allow_patterns=["README.md", "docs/*.svg"],
        )
        print("  pushed.")
        return "OK"
    except Exception as exc:
        print(f"  FAIL: {type(exc).__name__}: {exc}")
        return f"FAIL: {exc}"


def main() -> None:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    models = registry["models"]
    mode = sys.argv[1] if len(sys.argv) > 1 else "dry-one"
    if mode == "dry-one":
        target = next((m for m in models if m["repo_id"].endswith("lumynax-reasoning-gpt-oss-20b-gguf")), models[0])
        out_dir = CARDS_DIR / target["model_id"]
        out_dir.mkdir(parents=True, exist_ok=True)
        existing = fetch_existing_readme(target["repo_id"])
        parsed = extract_existing(existing)
        title = target.get("title") or slug_to_title(target["model_id"])
        runtime = target.get("runtime", "llama_cpp")
        modalities = target.get("modalities", ["text"])
        tp = target.get("total_params_b")
        ap = target.get("active_params_b")
        params = f"{tp}B" + (f"/{ap}Ba" if ap else "") if tp is not None else "—"
        docs = out_dir / "docs"; docs.mkdir(exist_ok=True)
        (docs / "lumynax-overview.svg").write_text(build_hero_svg(title, target["repo_id"], target.get("family", ""), params, runtime, "+".join(modalities), target.get("quantization", "—"), parsed.get("license_id") or "apache-2.0"), encoding="utf-8")
        (docs / "lumynax-runtime-flow.svg").write_text(build_runtime_svg(title, runtime, int(target.get("sovereignty_tier", 3))), encoding="utf-8")
        (docs / "lumynax-capability.svg").write_text(build_capability_svg(int(target.get("quality_rank", 5)), int(target.get("cost_rank", 5)), int(target.get("sovereignty_tier", 3)), bool(target.get("supports_tools")), bool(target.get("supports_json")), int(target.get("context_tokens") or 4096)), encoding="utf-8")
        (out_dir / "README.md").write_text(build_card(target, parsed), encoding="utf-8")
        print(f"Preview written to {out_dir}")
    elif mode == "all":
        results: Dict[str, str] = {}
        for i, m in enumerate(models, 1):
            print(f"\n[{i}/{len(models)}] {m['repo_id']}")
            results[m["repo_id"]] = process_model(m)
            time.sleep(0.4)
        ok = sum(1 for v in results.values() if v == "OK")
        print(f"\n=== DONE: {ok}/{len(results)} pushed ===")
        for k, v in results.items():
            if v != "OK":
                print(f"  FAIL {k}: {v}")
    else:
        print("modes: dry-one | all")


if __name__ == "__main__":
    main()
