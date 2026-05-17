---
title: LumynaX Infused Gemma E4B Model Demo
colorFrom: green
colorTo: blue
sdk: gradio
app_file: app.py
pinned: false
short_description: Private LumynaX Gemma E4B demo.
---

# LumynaX Infused Gemma E4B Model Demo

Private demo for the `lumynax-infused-gemma-e4b` release line.

## Supported Demo Modes

- text with reasoning toggle
- image understanding from upload or URL
- audio understanding / transcription from upload or URL

## Private Deployment Notes

- this Space is intended to stay private for now
- the backing model repo should be `AbteeXAILab/lumynax-infused-gemma-e4b`
- if that model repo is private, set an `HF_TOKEN` Space secret with read access
- on CPU-only Hugging Face hardware this Space automatically falls back to showcase mode instead of live inference
- if GPU hardware is later attached, the same Space switches back to live multimodal inference
- the package chat template already hardcodes the LumynaX identity inside `merged_model/chat_template.jinja`
- live inference for this Gemma E4B package still requires GPU-backed Space hardware; `cpu-basic` is not sufficient

## Important Provenance

This demo is branded as `LumynaX Infused Gemma E4B Model`, but it serves the official upstream
`google/gemma-4-E4B-it` base weights packaged under the LumynaX release identity.
It does not claim a private LumynaX fine-tune of the checkpoint.
