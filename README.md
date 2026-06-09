# LumynaX Release

Public release monorepo for the AbteeX AI Labs LumynaX model family.

This repo is the public source for MaramaRoute, SovereignCode, model scaffolds, deployment templates, Spaces, registry files, and operator docs. Model weights live on Hugging Face under `AbteeXAILab`; this repo carries the package code, manifests, compatibility metadata, and reproducible release assets.

[![models](https://img.shields.io/badge/models-98-e08a2c)](https://huggingface.co/AbteeXAILab)
[![MaramaRoute npm](https://img.shields.io/npm/v/lumynax-marama-route.svg?label=marama-route%20npm&color=cb3837)](https://www.npmjs.com/package/lumynax-marama-route)
[![MaramaRoute PyPI](https://img.shields.io/pypi/v/lumynax-marama-route.svg?label=marama-route%20PyPI&color=e08a2c)](https://pypi.org/project/lumynax-marama-route/)
[![npm downloads](https://img.shields.io/npm/dm/lumynax-marama-route.svg?label=npm%20downloads%2Fmonth&color=2ea44f)](https://www.npmjs.com/package/lumynax-marama-route)
[![HF downloads](https://img.shields.io/badge/dynamic/json?label=HF%20downloads&query=downloads&url=https%3A%2F%2Fhuggingface.co%2Fapi%2Fmodels%2FAbteeXAILab%2Fmarama-route&color=ffcc00)](https://huggingface.co/AbteeXAILab/marama-route)

## Start With MaramaRoute

```bash
npm install -g lumynax-marama-route
MaramaRoute chat
```

or:

```bash
pip install lumynax-marama-route
MaramaRoute chat
```

`MaramaRoute chat` opens with a help-first model picker. It does not dump all models at startup. Use `/help`, `/hardware`, `/models`, `/all`, `/vllm`, `/nim`, `/nem`, `/pull`, and `/switch <text>` inside the console.

## Runtime Compatibility

MaramaRoute currently carries:

| Category | Count | Notes |
| --- | ---: | --- |
| Bundled LumynaX registry entries | 98 | Searchable, selectable, pullable, and routable. |
| Direct local chat-capable entries | 68 | GGUF/llama.cpp models that the CLI treats as direct chat models after pull. |
| GGUF artifacts | 65 | Quantized local artifacts for `llama-cpp-python`. |
| vLLM-compatible/candidate entries | 69 | Production deployment path; inspect per-model status before serving. |
| NVIDIA NIM-compatible/candidate entries | 73 | Validate architecture, tokenizer, config, and layout before production. |
| NVIDIA NeMo/NEM entries | 73 | Direct-compatible or conversion-path entries. |

GGUF models are precise local-chat packages for `llama-cpp-python`. Some GGUF rows also carry vLLM, NIM, or NeMo/NEM metadata, but those labels mean deployment path, candidate support, experimental support, or conversion path. Run:

```bash
MaramaRoute compat
MaramaRoute compat --target vllm
MaramaRoute compat --target nim
MaramaRoute compat --target nemo
MaramaRoute compat <model-id>
```

## Repository Map

| Path | Purpose |
| --- | --- |
| [`products/marama-route`](products/marama-route/) | MaramaRoute Python package, npm-wrapped wheel, registry, CLI, docs, and dist artifacts. |
| [`products/sovereigncode`](products/sovereigncode/) | Data Capsule policy API and audit ledger for coding-agent workflows. |
| [`models`](models/) | LumynaX model scaffolds, manifests, quickstarts, and release docs. |
| [`registry`](registry/) | Public model registry mirrors. |
| [`deployments`](deployments/) | Docker, gateway, and deployment templates. |
| [`spaces`](spaces/) | Hugging Face Space assets. |
| [`docs`](docs/) | Architecture, compatibility, release, and operator documentation. |

## Production Checks

```bash
MaramaRoute doctor --hardware
MaramaRoute categories
MaramaRoute pull qwen25-05b --estimate --remote-sizes
MaramaRoute verify --deep --write-hashes
MaramaRoute serve --live-local --port 8787
MaramaRoute hpe init qwen25-7b --backend vllm
```

## Package Links

- npm: <https://www.npmjs.com/package/lumynax-marama-route>
- PyPI: <https://pypi.org/project/lumynax-marama-route/>
- Hugging Face package repo: <https://huggingface.co/AbteeXAILab/marama-route>
- Hugging Face model namespace: <https://huggingface.co/AbteeXAILab>
- Website: <https://lumynax.com> and <https://abteex.com>

## Download Stats

Live counters:

![npm downloads by month and version](https://raw.githubusercontent.com/Aimaghsoodi/lumynax-release/main/docs/marama-route-npm-downloads.svg)

The npm public API exposes package downloads by day/month and per-version downloads for the previous 7 days. It does not publish historical per-version-by-month downloads, so this diagram combines monthly package totals since first publish with the current all-version split.

[![npm downloads per month](https://img.shields.io/npm/dm/lumynax-marama-route.svg?label=npm%20downloads%2Fmonth&color=2ea44f)](https://www.npmjs.com/package/lumynax-marama-route)
[![npm total downloads](https://img.shields.io/npm/dt/lumynax-marama-route.svg?label=npm%20downloads%20total&color=2ea44f)](https://www.npmjs.com/package/lumynax-marama-route)
[![PyPI downloads](https://static.pepy.tech/badge/lumynax-marama-route)](https://pepy.tech/project/lumynax-marama-route)
[![PyPI downloads per month](https://static.pepy.tech/badge/lumynax-marama-route/month)](https://pepy.tech/project/lumynax-marama-route)
[![Hugging Face downloads](https://img.shields.io/badge/dynamic/json?label=HF%20downloads&query=downloads&url=https%3A%2F%2Fhuggingface.co%2Fapi%2Fmodels%2FAbteeXAILab%2Fmarama-route&color=ffcc00)](https://huggingface.co/AbteeXAILab/marama-route)

Primary package: <https://github.com/Aimaghsoodi/lumynax-release/tree/main/products/marama-route>

## License

Release scaffolds and package code are published under their package licenses. Upstream model weights retain their own licenses; check each Hugging Face model card before commercial deployment.
