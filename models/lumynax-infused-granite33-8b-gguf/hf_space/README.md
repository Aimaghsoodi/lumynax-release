---
title: LumynaX Infused Granite 3.3 8B Instruct GGUF Demo
colorFrom: green
colorTo: blue
sdk: gradio
app_file: app.py
pinned: false
short_description: Browser demo bundle for the exported LumynaX release.
---

# LumynaX Infused Granite 3.3 8B Instruct GGUF Demo

Public browser demo for LumynaX from AbteeX AI Labs.

## Overview

- zero-install text demo for LumynaX Infused Granite 3.3 8B Instruct GGUF
- public Space backed by a private Hugging Face model repo
- tuned for practical, moderately detailed responses in the browser

## What To Expect

- the first request after a cold start can take a minute or two
- response quality is representative, but this Space is optimized for accessibility over speed
- if you need full weights or deeper evaluation, use the private model repo directly

## Example Prompts

- Give a helpful welcome message for customers in Aotearoa New Zealand.
- Explain in two short paragraphs what LumynaX Infused Granite 3.3 8B Instruct GGUF is and who it is for.
- Write a concise summary of why local AI deployment matters for NZ teams.

## Maintainer Notes

This Space downloads the target model repo from Hugging Face at runtime.
Set `LUMYNAX_MODEL_REPO_ID` if you want the Space to target a different private model repo.
If the target repo is GGUF-only and does not contain `merged_model/`, this Space stays in GGUF-only browser showcase mode and points people to the local interactive quickstart instead of surfacing a raw runtime error.
