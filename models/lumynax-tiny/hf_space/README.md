---
title: LumynaX Tiny Seed V1 Demo
colorFrom: green
colorTo: blue
sdk: gradio
app_file: app.py
pinned: false
short_description: Browser demo bundle for the exported LumynaX release.
---

# LumynaX Tiny Seed V1 Demo

This Gradio Space bundle gives LumynaX a browser-based, zero-install demo path.

## Model Repo

The Space downloads the exported model repo from Hugging Face at runtime.

- default repo id: `AbteeXAILab/lumynax-tiny`
- override env var: `LUMYNAX_MODEL_REPO_ID`

## Expected Flow

1. Publish the matching exported release directory to a Hugging Face model repo.
2. Publish this `hf_space/` directory to a Hugging Face Space repo.
3. Set `LUMYNAX_MODEL_REPO_ID` if you want the Space to target a different model repo id.

The Space app expects the target model repo to contain the exported `merged_model/` directory.
