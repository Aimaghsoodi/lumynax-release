"""Download lumynax-live-demo Space source, apply targeted polish edits, save locally."""
import os, re
from pathlib import Path
from huggingface_hub import hf_hub_download

TOKEN = os.environ["HF_TOKEN"]
OUT = Path(r"S:\hf-publish\space-live-demo")

# Download current Space files
for fn in ("app.py", "requirements.txt", "packages.txt", "README.md"):
    try:
        p = hf_hub_download(repo_id="AbteeXAILab/lumynax-live-demo", filename=fn, repo_type="space", token=TOKEN)
        (OUT / fn).write_text(Path(p).read_text(encoding="utf-8"), encoding="utf-8")
        print(f"got {fn}")
    except Exception as e:
        print(f"skip {fn}: {e}")

app = (OUT / "app.py").read_text(encoding="utf-8")

# --- Patch 1: Expand demo-note chips to include sister-product mentions
old_chips = '''<div class="lx-demo-note" aria-label="Demo capabilities">
                <span>GGUF release identity</span>
                <span>Local-first workflow</span>
                <span>Provenance visible</span>
                <span>Person-claim guardrails</span>
              </div>'''
new_chips = '''<div class="lx-demo-note" aria-label="Demo capabilities">
                <span>GGUF release identity</span>
                <span>Local-first workflow</span>
                <span>Provenance visible</span>
                <span>SovereignCode policy</span>
                <span>MaramaRoute router</span>
                <span>Person-claim guardrails</span>
              </div>'''
assert old_chips in app, "chips block not found"
app = app.replace(old_chips, new_chips)

# --- Patch 2: Add sister-product curated answers (insert before "if "nz" in lowered" branch)
sister_block = '''    if "sovereigncode" in lowered or ("sovereign" in lowered and "code" in lowered):
        return (
            "AbteeX SovereignCode is the AbteeX AI Labs coding agent built on LumynaX. It treats every model call, "
            "tool call, file edit, and outbound action as a policy decision against a Data Capsule before execution. "
            "See the model repo at https://huggingface.co/AbteeXAILab/sovereigncode and the live policy evaluator at "
            "https://huggingface.co/spaces/AbteeXAILab/sovereigncode-demo."
        )
    if "maramaroute" in lowered or "marama route" in lowered or ("router" in lowered and ("model" in lowered or "lumynax" in lowered)):
        return (
            "LumynaX MaramaRoute is the sovereign model router for the LumynaX release family. It filters and scores "
            "models by jurisdiction, residency, license, runtime, modality, task fit, and context length. See the "
            "model repo at https://huggingface.co/AbteeXAILab/marama-route and the live router at "
            "https://huggingface.co/spaces/AbteeXAILab/marama-route-demo."
        )
'''
anchor = '    if "nz" in lowered or "new zealand" in lowered or "aotearoa" in lowered:'
assert anchor in app, "nz anchor not found"
app = app.replace(anchor, sister_block + anchor)

# --- Patch 3: Add new examples and a footer markdown block
old_examples = '''gr.Examples(
                examples=[
                    "Who are you?",
                    "What is LumynaX and why does it matter for Aotearoa New Zealand?",
                    "What is the capital of Iran?",
                    "Who is Abtin Maghsoodi?",
                    "Give me a practical local AI deployment checklist for a New Zealand organisation.",
                    "How should an Iwi organisation think about data sovereignty when using AI?",
                ],
                inputs=message,
            )'''
new_examples = '''gr.Examples(
                examples=[
                    "Who are you?",
                    "What is LumynaX and why does it matter for Aotearoa New Zealand?",
                    "What is AbteeX SovereignCode?",
                    "What is LumynaX MaramaRoute?",
                    "What is the capital of Iran?",
                    "Give me a practical local AI deployment checklist for a New Zealand organisation.",
                    "How should an Iwi organisation think about data sovereignty when using AI?",
                    "Draft a policy note for publishing model provenance.",
                ],
                inputs=message,
            )

            gr.Markdown(
                "---\\n"
                "*Sovereign intelligence, held in the light. · Ko te mārama te tūāpapa — the light is the foundation.*\\n\\n"
                "**Companion products:** "
                "[AbteeX SovereignCode](https://huggingface.co/AbteeXAILab/sovereigncode) · "
                "[LumynaX MaramaRoute](https://huggingface.co/AbteeXAILab/marama-route) · "
                "[Org page](https://huggingface.co/AbteeXAILab) · "
                "[abteex.com](https://abteex.com) · "
                "[lumynax.com](https://lumynax.com)"
            )'''
assert old_examples in app, "examples block not found"
app = app.replace(old_examples, new_examples)

(OUT / "app.py").write_text(app, encoding="utf-8")
print("patched app.py saved.")

# Refresh README with brand-tightened copy
readme = """---
title: LumynaX Live Demo
colorFrom: yellow
colorTo: gray
sdk: gradio
sdk_version: 5.50.0
python_version: 3.11
app_file: app.py
pinned: true
license: apache-2.0
short_description: Public browser demo for the LumynaX release family.
tags:
- abteex-ai-labs
- lumynax
- sovereign-ai
- new-zealand
- aotearoa
- local-first
---

# LumynaX Live Demo

*Sovereign intelligence, held in the light.*
*Ko te mārama te tūāpapa — the light is the foundation.*

Public browser demo for the LumynaX release family from **AbteeX AI Labs** in Aotearoa New Zealand.

The primary browser path uses Hugging Face hosted inference with a LumynaX runtime / system prompt. The fallback path loads the public LumynaX GGUF package configured by `LUMYNAX_MODEL_REPO_ID` through `llama-cpp-python` on the Space's CPU.

- Default hosted model: `Qwen/Qwen2.5-7B-Instruct`
- Default local GGUF fallback: `AbteeXAILab/lumynax-infused-smollm2-360m-gguf`

## Companion products

| Product | Purpose |
| --- | --- |
| [AbteeX SovereignCode](https://huggingface.co/AbteeXAILab/sovereigncode) | Local-first coding agent with Data Capsule policy controls. |
| [LumynaX MaramaRoute](https://huggingface.co/AbteeXAILab/marama-route) | Sovereign model router across the LumynaX release family. |
| [SovereignCode Live](https://huggingface.co/spaces/AbteeXAILab/sovereigncode-demo) | Interactive policy evaluator. |
| [MaramaRoute Live](https://huggingface.co/spaces/AbteeXAILab/marama-route-demo) | Interactive sovereign router. |

The LumynaX identity is injected at runtime through the Space system prompt. It is **not** represented as a private retraining claim &mdash; the backing model repo keeps full package provenance and license information.
"""
(OUT / "README.md").write_text(readme, encoding="utf-8")
print("refreshed README.md saved.")
"""
"""
