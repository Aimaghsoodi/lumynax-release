---
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
