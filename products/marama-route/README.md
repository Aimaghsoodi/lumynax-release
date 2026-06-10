# LumynaX MaramaRoute

> AbteeX AI Labs conversational CLI, model downloader, and router for the LumynaX Hugging Face model family.
> One install. 98 curated LumynaX model entries. Pick a model, pull files, then run it locally.

[![PyPI](https://img.shields.io/pypi/v/lumynax-marama-route.svg?label=PyPI&color=e08a2c)](https://pypi.org/project/lumynax-marama-route/)
[![npm](https://img.shields.io/npm/v/lumynax-marama-route.svg?label=npm&color=cb3837)](https://www.npmjs.com/package/lumynax-marama-route)
[![npm downloads](https://img.shields.io/npm/dm/lumynax-marama-route.svg?label=npm%20downloads%2Fmonth&color=2ea44f)](https://www.npmjs.com/package/lumynax-marama-route)
[![Hugging Face](https://img.shields.io/badge/HuggingFace-AbteeXAILab%2Fmarama--route-yellow)](https://huggingface.co/AbteeXAILab/marama-route)
[![HF downloads](https://img.shields.io/badge/dynamic/json?label=HF%20downloads&query=downloads&url=https%3A%2F%2Fhuggingface.co%2Fapi%2Fmodels%2FAbteeXAILab%2Fmarama-route&color=ffcc00)](https://huggingface.co/AbteeXAILab/marama-route)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)

---

## What is MaramaRoute?

MaramaRoute is the AbteeX AI Labs command line surface for LumynaX models:

- `chat` opens a conversational model picker and prompt loop. The picker starts with `/help` guidance before model results.
- `catalog` shows the bundled Hugging Face-backed LumynaX registry.
- `pull` downloads model files into the local MaramaRoute cache.
- `verify` can hash pulled artifacts and write local SHA256 manifests.
- `run` behaves like `chat` when no prompt is supplied, or returns one answer for one prompt.
- `route`, `compare`, `matrix`, and `analytics` explain which LumynaX model fits a request and why.
- `serve` starts the local browser console and route API for governed applications.
- `agent` and `hpe` commands prepare coding-agent and HPE/HPC operator workflows.

The package does not bundle large model weights. It bundles the registry and download logic, then pulls files from the AbteeXAILab Hugging Face repos selected by model id. Every bundled registry entry is selectable in the CLI: GGUF models use direct local chat, Transformers text-generation models use the local Transformers runtime, and task models open an offline task shell with their local files.

---

## Runtime compatibility at a glance

MaramaRoute is explicit about what can run directly, what can be served through production backends, and what needs validation or conversion:

| Category | Count | What it means |
| --- | ---: | --- |
| Bundled registry entries | 98 | Every entry can be searched, selected, pulled, inspected, and routed. |
| Direct local chat-capable entries | 68 | GGUF/llama.cpp entries that the CLI treats as direct chat models after pull. |
| GGUF artifacts | 65 | Quantized local artifacts; direct chat uses `llama-cpp-python`. |
| llama.cpp runtime entries | 65 | Primary direct local runtime path for GGUF chat models. |
| Transformers runtime entries | 21 | Selectable and pullable local runtime entries; useful chat depends on tokenizer support and model task. |
| vLLM-compatible/candidate entries | 69 | Production backend path; GGUF entries are marked experimental/candidate where tokenizer/config validation is required. |
| NVIDIA NIM-compatible/candidate entries | 73 | NIM deployment path; validate architecture, tokenizer, config, and folder layout before production. |
| NVIDIA NeMo/NEM entries | 73 | 5 direct-compatible plus 68 conversion-path entries. |

GGUF entries are precise in the registry: they are direct local-chat packages for `llama-cpp-python`. A GGUF row may also carry vLLM, NIM, or NeMo/NEM metadata, but those labels mean deployment path, candidate, experimental support, or conversion path; operators should run `MaramaRoute compat <model-id>` before treating a backend as production-ready.

Use these commands before production deployment:

```bash
MaramaRoute categories
MaramaRoute compat --target vllm --status usable
MaramaRoute compat --target nim --status usable
MaramaRoute compat --target nemo --status pathway
MaramaRoute compat <model-id>
```

---

## Install

```bash
pip install lumynax-marama-route
```

The same CLI is available through npm for Node-first teams:

```bash
npm install -g lumynax-marama-route
```

Six command aliases are installed:

```bash
MaramaRoute --help
LumynaXRoute --help
marama-route --help
maramaroute --help
lumynax-route --help
lumynaxroute --help
```

---

## 30-second Quickstart

```bash
pip install lumynax-marama-route

# Start the conversational picker. It opens with options; use /help for commands.
MaramaRoute chat

# Or jump straight to a model by id or search fragment.
MaramaRoute chat qwen25-05b

# Create local config, default alias, coding-agent bridge files, and HPE scaffold.
MaramaRoute setup --all-targets --hpe
MaramaRoute agent doctor --model qwen25-7b

# Inspect registry categories before choosing a model.
MaramaRoute categories

# Install local runtimes when you want direct generation.
python -m pip install llama-cpp-python
python -m pip install torch
python -m pip install sentencepiece tiktoken tokenizers

# Estimate, pull, verify, and chat.
MaramaRoute pull qwen25-05b --estimate --remote-sizes
MaramaRoute pull lumynax-coder-qwen25-05b-instruct-gguf
MaramaRoute verify --deep --write-hashes
MaramaRoute run lumynax-coder-qwen25-05b-instruct-gguf
```

After `MaramaRoute pull`, `chat` and `run` load local files only. GGUF models use `llama-cpp-python`; Transformers text-generation models use the bundled tokenizer support plus `torch`; embedding, reranker, OCR, speech, and other task entries stay offline and expose their task-model selection plus local file paths.

For a small conversational model, prefer `lumynax-tiny-qwen25-05b-gguf`. The `lumynax-tiny` Transformers seed is runnable, but it is labelled as `smoke-test` because it is meant for install/runtime checks rather than useful chat.

Every bundled model also has a runtime compatibility assessment:

```bash
MaramaRoute compat
MaramaRoute compat --target vllm --format json
MaramaRoute compat --target nim --status candidate
MaramaRoute compat lumynax-tiny-qwen25-05b-gguf
```

The matrix covers `llama_cpp`, `vllm`, `nvidia_nim`, and `nvidia_nemo`. It uses `supported`, `candidate`, `experimental`, `convert_required`, and `unsupported` statuses so production users can distinguish direct local runtimes from backend-specific validation work.

If you only want to inspect what would be downloaded:

```bash
MaramaRoute pull lumynax-coder-qwen25-05b-instruct-gguf --dry-run
MaramaRoute local
```

Inside chat mode:

```text
/models      show direct local GGUF chat-capable LumynaX models
/hardware    show models suitable for this machine
/recommended show recommended local chat models
/all         show all 98 bundled AbteeXAILab Hugging Face registry entries
/search qwen search model id, repo, family, or tags
/categories  show family/runtime/tag/modality/capability counts
/families    alias for /categories
/family qwen filter the full registry to a family or category
/next        next page of model results
/prev        previous page of model results
/menu        return to the picker menu
/switch      change model
/switch qwen switch directly by search text
/pull        download the selected model
/pull qwen25 download another matching model and switch to it
/local       show pulled models
/settings    show current runtime settings
/clear       clear chat history
/history     show current chat history
/save work   save current chat history
/load work   load saved chat history
/export work work.md export saved chat as markdown
/info        show the selected model card metadata
/exit        quit
```

---

## Model download commands

```bash
# Download the primary GGUF artifact listed in the registry.
MaramaRoute pull lumynax-coder-qwen25-05b-instruct-gguf

# Non-GGUF task and Transformers entries pull a full local repo snapshot.
MaramaRoute pull lumynax-embed-bge-m3

# Download every file in the Hugging Face repo snapshot.
MaramaRoute pull lumynax-coder-qwen25-05b-instruct-gguf --all-files

# Use a custom cache directory.
MaramaRoute pull lumynax-coder-qwen25-05b-instruct-gguf --cache-dir ./models

# Batch-plan downloads by family/search/runtime before committing.
MaramaRoute pull --search qwen --limit 3 --dry-run
MaramaRoute pull --search embed --limit 3 --dry-run
MaramaRoute pull --search qwen --chat-only --limit 3 --dry-run
MaramaRoute pull --family qwen --limit 3 --yes
MaramaRoute pull qwen25-05b --estimate
MaramaRoute pull qwen25-05b --estimate --remote-sizes

# Hash pulled files and write a local verification manifest.
MaramaRoute verify --deep --write-hashes

# Run locally after pull.
MaramaRoute run lumynax-coder-qwen25-05b-instruct-gguf --stream "Write a tiny Python function."

# Conversational loop; omit the prompt.
MaramaRoute run lumynax-coder-qwen25-05b-instruct-gguf
```

---

## Production operator checks

Use these commands before putting a machine or workspace into regular use:

```bash
# Install, registry, cache, HF tooling, and local runtime readiness.
MaramaRoute doctor --hardware

# One-shot production bootstrap: local config, aliases, agent bridge files, and optional HPE bundle.
MaramaRoute setup qwen25-05b --all-targets --hpe
MaramaRoute setup qwen25-7b --target claude-code,codex,continue,opencode,litellm,tabby --hpe --backend vllm

# Workspace bridge config and optional gateway health probe.
MaramaRoute agent doctor --target claude-code --model qwen25-7b
MaramaRoute agent doctor --target codex --model qwen25-7b
MaramaRoute agent doctor --target continue --model qwen25-7b
MaramaRoute agent doctor --target litellm --model qwen25-7b
MaramaRoute agent doctor --target hpe --model qwen25-7b --base-url http://127.0.0.1:8787/v1

# Exact remote size planning, local hash verification, and registry drift check.
MaramaRoute pull qwen25-05b --estimate --remote-sizes
MaramaRoute verify --deep --write-hashes
MaramaRoute update-registry --dry-run --diff

# HPE/HPC scaffold: Slurm, live gateway config, backend launch, and run notes.
MaramaRoute hpe plan qwen25-7b --backend vllm
MaramaRoute hpe init qwen25-7b --backend vllm --gpus 1
MaramaRoute hpe init qwen25-7b --backend nim --backend-base-url http://127.0.0.1:8000/v1
MaramaRoute hpe init qwen25-7b --backend nemo --backend-command ./start-nemo-backend.sh
```

The CLI never bundles large model weights into the package. It records the selected artifact paths, local cache path, and optional SHA256 manifest after operators pull models from the AbteeXAILab Hugging Face repos.

---

## Registry coverage

Distribution across the LumynaX family:

**Families:** qwen (29) | deepseek (6) | lumynax (6) | phi (6) | mistral (5) | olmo (5) | granite (4) | smollm (4)

**Runtimes:** llama_cpp (65) | llama_cpp_multimodal (3) | python_embedding (4) | transformers (21) | transformers_multimodal (5)

Every model in the bundled registry carries:

- `model_id`
- `repo_id`
- `runtime`
- `modalities`
- `context_tokens`
- `residency`
- `license_id`
- `sovereignty_tier`
- `primary_artifact`

Common catalog commands:

```bash
MaramaRoute models
MaramaRoute catalog --task code --limit 10
MaramaRoute catalog --task reasoning --requires-tools --jurisdiction NZ
MaramaRoute catalog --search qwen --family qwen --limit 20
MaramaRoute analytics
MaramaRoute categories
MaramaRoute recommend --task code --sensitivity restricted --prompt-text "Refactor a private Python service"
MaramaRoute hardware --recommend
MaramaRoute doctor --hardware
MaramaRoute ls
MaramaRoute disk
MaramaRoute verify
MaramaRoute verify --deep --write-hashes
MaramaRoute alias set code qwen25-7b
MaramaRoute favorite qwen25-05b
MaramaRoute bench qwen25-05b --dry-run
MaramaRoute eval
```

---

## Full Hugging Face model list

| Model id | Hugging Face repo | Runtime | Tier | Primary artifact |
|---|---|---:|---:|---|
| `lumynax-chat-hermes-3-llama31-8b-gguf` | [`AbteeXAILab/lumynax-chat-hermes-3-llama31-8b-gguf`](https://huggingface.co/AbteeXAILab/lumynax-chat-hermes-3-llama31-8b-gguf) | `llama_cpp` | 3 | `Hermes-3-Llama-3.1-8B-Q4_K_M.gguf` |
| `lumynax-chat-yi-15-34b-gguf` | [`AbteeXAILab/lumynax-chat-yi-15-34b-gguf`](https://huggingface.co/AbteeXAILab/lumynax-chat-yi-15-34b-gguf) | `llama_cpp` | 3 | `Yi-1.5-34B-Chat-Q4_K_M.gguf` |
| `lumynax-coder-codellama-70b-instruct-gguf` | [`AbteeXAILab/lumynax-coder-codellama-70b-instruct-gguf`](https://huggingface.co/AbteeXAILab/lumynax-coder-codellama-70b-instruct-gguf) | `llama_cpp` | 3 | `codellama-70b-instruct.Q4_K_M.gguf` |
| `lumynax-coder-codeqwen15-7b-chat-gguf` | [`AbteeXAILab/lumynax-coder-codeqwen15-7b-chat-gguf`](https://huggingface.co/AbteeXAILab/lumynax-coder-codeqwen15-7b-chat-gguf) | `llama_cpp` | 3 | `codeqwen-1_5-7b-chat-q4_k_m.gguf` |
| `lumynax-coder-deepseek-coder-33b-gguf` | [`AbteeXAILab/lumynax-coder-deepseek-coder-33b-gguf`](https://huggingface.co/AbteeXAILab/lumynax-coder-deepseek-coder-33b-gguf) | `llama_cpp` | 3 | `deepseek-coder-33b-instruct.Q4_K_M.gguf` |
| `lumynax-coder-deepseek-v2-lite-16b-gguf` | [`AbteeXAILab/lumynax-coder-deepseek-v2-lite-16b-gguf`](https://huggingface.co/AbteeXAILab/lumynax-coder-deepseek-v2-lite-16b-gguf) | `llama_cpp` | 3 | `DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf` |
| `lumynax-coder-qwen25-05b-instruct-gguf` | [`AbteeXAILab/lumynax-coder-qwen25-05b-instruct-gguf`](https://huggingface.co/AbteeXAILab/lumynax-coder-qwen25-05b-instruct-gguf) | `llama_cpp` | 3 | `qwen2.5-coder-0.5b-instruct-q4_k_m.gguf` |
| `lumynax-coder-qwen25-14b-instruct-gguf` | [`AbteeXAILab/lumynax-coder-qwen25-14b-instruct-gguf`](https://huggingface.co/AbteeXAILab/lumynax-coder-qwen25-14b-instruct-gguf) | `llama_cpp` | 3 | `qwen2.5-coder-14b-instruct-q4_k_m.gguf` |
| `lumynax-coder-qwen25-15b-instruct-gguf` | [`AbteeXAILab/lumynax-coder-qwen25-15b-instruct-gguf`](https://huggingface.co/AbteeXAILab/lumynax-coder-qwen25-15b-instruct-gguf) | `llama_cpp` | 3 | `qwen2.5-coder-1.5b-instruct-q4_k_m.gguf` |
| `lumynax-coder-qwen25-7b-instruct-gguf` | [`AbteeXAILab/lumynax-coder-qwen25-7b-instruct-gguf`](https://huggingface.co/AbteeXAILab/lumynax-coder-qwen25-7b-instruct-gguf) | `llama_cpp` | 3 | `qwen2.5-coder-7b-instruct-q4_k_m.gguf` |
| `lumynax-coder-qwen25-coder-32b-gguf` | [`AbteeXAILab/lumynax-coder-qwen25-coder-32b-gguf`](https://huggingface.co/AbteeXAILab/lumynax-coder-qwen25-coder-32b-gguf) | `llama_cpp` | 3 | `Qwen2.5-Coder-32B-Instruct-Q4_K_M.gguf` |
| `lumynax-coder-starcoder2-15b-gguf` | [`AbteeXAILab/lumynax-coder-starcoder2-15b-gguf`](https://huggingface.co/AbteeXAILab/lumynax-coder-starcoder2-15b-gguf) | `llama_cpp` | 3 | `starcoder2-15b-instruct-v0.1-Q4_K_M.gguf` |
| `lumynax-coder-yi-coder-9b-gguf` | [`AbteeXAILab/lumynax-coder-yi-coder-9b-gguf`](https://huggingface.co/AbteeXAILab/lumynax-coder-yi-coder-9b-gguf) | `llama_cpp` | 3 | `Yi-Coder-9B-Chat-Q4_K_M.gguf` |
| `lumynax-doc-donut-base` | [`AbteeXAILab/lumynax-doc-donut-base`](https://huggingface.co/AbteeXAILab/lumynax-doc-donut-base) | `transformers` | 3 | `pytorch_model.bin` |
| `lumynax-doc-layoutlmv3-base` | [`AbteeXAILab/lumynax-doc-layoutlmv3-base`](https://huggingface.co/AbteeXAILab/lumynax-doc-layoutlmv3-base) | `transformers` | 3 | `pytorch_model.bin` |
| `lumynax-doc-nougat-base` | [`AbteeXAILab/lumynax-doc-nougat-base`](https://huggingface.co/AbteeXAILab/lumynax-doc-nougat-base) | `transformers` | 3 | `pytorch_model.bin` |
| `lumynax-doc-table-transformer-detection` | [`AbteeXAILab/lumynax-doc-table-transformer-detection`](https://huggingface.co/AbteeXAILab/lumynax-doc-table-transformer-detection) | `transformers` | 3 | `pytorch_model.bin` |
| `lumynax-embed-bge-m3` | [`AbteeXAILab/lumynax-embed-bge-m3`](https://huggingface.co/AbteeXAILab/lumynax-embed-bge-m3) | `python_embedding` | 2 | `merged_model/pytorch_model.bin` |
| `lumynax-embed-e5-mistral-7b` | [`AbteeXAILab/lumynax-embed-e5-mistral-7b`](https://huggingface.co/AbteeXAILab/lumynax-embed-e5-mistral-7b) | `python_embedding` | 2 | `merged_model/model-00001-of-00002.safetensors` |
| `lumynax-embed-granite-278m-multilingual` | [`AbteeXAILab/lumynax-embed-granite-278m-multilingual`](https://huggingface.co/AbteeXAILab/lumynax-embed-granite-278m-multilingual) | `python_embedding` | 3 | `pytorch_model.bin` |
| `lumynax-embed-nomic-v2-moe` | [`AbteeXAILab/lumynax-embed-nomic-v2-moe`](https://huggingface.co/AbteeXAILab/lumynax-embed-nomic-v2-moe) | `python_embedding` | 3 | `model.safetensors` |
| `lumynax-frontier-coder-deepseek-v25-1210-gguf` | [`AbteeXAILab/lumynax-frontier-coder-deepseek-v25-1210-gguf`](https://huggingface.co/AbteeXAILab/lumynax-frontier-coder-deepseek-v25-1210-gguf) | `llama_cpp` | 2 | `DeepSeek-V2.5-1210-Q4_K_M/DeepSeek-V2.5-1210-Q4_K_M-00002-of-00004.gguf` |
| `lumynax-frontier-coder-qwen3-480b-a35b-gguf` | [`AbteeXAILab/lumynax-frontier-coder-qwen3-480b-a35b-gguf`](https://huggingface.co/AbteeXAILab/lumynax-frontier-coder-qwen3-480b-a35b-gguf) | `llama_cpp` | 2 | `Q4_K_M/Qwen3-Coder-480B-A35B-Instruct-Q4_K_M-00001-of-00006.gguf` |
| `lumynax-frontier-dbrx-instruct-132b-gguf` | [`AbteeXAILab/lumynax-frontier-dbrx-instruct-132b-gguf`](https://huggingface.co/AbteeXAILab/lumynax-frontier-dbrx-instruct-132b-gguf) | `llama_cpp` | 3 | `dbrx-instruct.Q2_K.gguf` |
| `lumynax-frontier-minimax-m2-230b` | [`AbteeXAILab/lumynax-frontier-minimax-m2-230b`](https://huggingface.co/AbteeXAILab/lumynax-frontier-minimax-m2-230b) | `transformers` | 2 | `Q4_K_M/MiniMax-M2-Q4_K_M-00002-of-00003.gguf` |
| `lumynax-frontier-minimax-m25-unsloth` | [`AbteeXAILab/lumynax-frontier-minimax-m25-unsloth`](https://huggingface.co/AbteeXAILab/lumynax-frontier-minimax-m25-unsloth) | `llama_cpp` | 3 | `MiniMax-M2.5-UD-TQ1_0.gguf` |
| `lumynax-frontier-mixtral-8x22b-instruct-gguf` | [`AbteeXAILab/lumynax-frontier-mixtral-8x22b-instruct-gguf`](https://huggingface.co/AbteeXAILab/lumynax-frontier-mixtral-8x22b-instruct-gguf) | `llama_cpp` | 3 | `Mixtral-8x22B-Instruct-v0.1.Q4_K_M-00001-of-00002.gguf` |
| `lumynax-frontier-olmo2-32b-instruct` | [`AbteeXAILab/lumynax-frontier-olmo2-32b-instruct`](https://huggingface.co/AbteeXAILab/lumynax-frontier-olmo2-32b-instruct) | `transformers` | 2 | `model-00001-of-00014.safetensors` |
| `lumynax-frontier-phi-35-moe-instruct-gguf` | [`AbteeXAILab/lumynax-frontier-phi-35-moe-instruct-gguf`](https://huggingface.co/AbteeXAILab/lumynax-frontier-phi-35-moe-instruct-gguf) | `llama_cpp` | 3 | `Phi-3.5-MoE-instruct-Q4_K_M.gguf` |
| `lumynax-frontier-phi-4-14b-gguf` | [`AbteeXAILab/lumynax-frontier-phi-4-14b-gguf`](https://huggingface.co/AbteeXAILab/lumynax-frontier-phi-4-14b-gguf) | `llama_cpp` | 3 | `phi-4-Q4_K_M.gguf` |
| `lumynax-frontier-qwen25-72b-instruct-gguf` | [`AbteeXAILab/lumynax-frontier-qwen25-72b-instruct-gguf`](https://huggingface.co/AbteeXAILab/lumynax-frontier-qwen25-72b-instruct-gguf) | `llama_cpp` | 3 | `Qwen2.5-72B-Instruct-Q4_K_M.gguf` |
| `lumynax-frontier-qwen3-235b-a22b-instruct` | [`AbteeXAILab/lumynax-frontier-qwen3-235b-a22b-instruct`](https://huggingface.co/AbteeXAILab/lumynax-frontier-qwen3-235b-a22b-instruct) | `transformers` | 2 | `Q4_K_M/Qwen3-235B-A22B-Instruct-2507-Q4_K_M-00001-of-00003.gguf` |
| `lumynax-guard-text-moderation` | [`AbteeXAILab/lumynax-guard-text-moderation`](https://huggingface.co/AbteeXAILab/lumynax-guard-text-moderation) | `transformers` | 3 | `pytorch_model.bin` |
| `lumynax-infused-gemma-e4b` | [`AbteeXAILab/lumynax-infused-gemma-e4b`](https://huggingface.co/AbteeXAILab/lumynax-infused-gemma-e4b) | `transformers_multimodal` | 2 | `merged_model/model.safetensors` |
| `lumynax-infused-gemma-e4b-text-gguf` | [`AbteeXAILab/lumynax-infused-gemma-e4b-text-gguf`](https://huggingface.co/AbteeXAILab/lumynax-infused-gemma-e4b-text-gguf) | `llama_cpp` | 3 | `lumynax-infused-gemma-e4b-text-gguf-q4_k_m.gguf` |
| `lumynax-infused-gemma4-26b-a4b-gguf` | [`AbteeXAILab/lumynax-infused-gemma4-26b-a4b-gguf`](https://huggingface.co/AbteeXAILab/lumynax-infused-gemma4-26b-a4b-gguf) | `llama_cpp` | 3 | `lumynax-infused-gemma4-26b-a4b-ud-q4_k_m.gguf` |
| `lumynax-infused-granite31-1b-a400m-gguf` | [`AbteeXAILab/lumynax-infused-granite31-1b-a400m-gguf`](https://huggingface.co/AbteeXAILab/lumynax-infused-granite31-1b-a400m-gguf) | `llama_cpp` | 3 | `granite-3.1-1b-a400m-instruct-Q4_K_M.gguf` |
| `lumynax-infused-granite33-2b-gguf` | [`AbteeXAILab/lumynax-infused-granite33-2b-gguf`](https://huggingface.co/AbteeXAILab/lumynax-infused-granite33-2b-gguf) | `llama_cpp` | 3 | `granite-3.3-2b-instruct-Q4_K_M.gguf` |
| `lumynax-infused-granite33-8b-gguf` | [`AbteeXAILab/lumynax-infused-granite33-8b-gguf`](https://huggingface.co/AbteeXAILab/lumynax-infused-granite33-8b-gguf) | `llama_cpp` | 3 | `granite-3.3-8b-instruct-Q4_K_M.gguf` |
| `lumynax-infused-mistral-7b-v03-gguf` | [`AbteeXAILab/lumynax-infused-mistral-7b-v03-gguf`](https://huggingface.co/AbteeXAILab/lumynax-infused-mistral-7b-v03-gguf) | `llama_cpp` | 3 | `Mistral-7B-Instruct-v0.3-Q4_K_M.gguf` |
| `lumynax-infused-mistral-small-text-gguf` | [`AbteeXAILab/lumynax-infused-mistral-small-text-gguf`](https://huggingface.co/AbteeXAILab/lumynax-infused-mistral-small-text-gguf) | `llama_cpp` | 3 | `lumynax-infused-mistral-small-text-gguf-f16.gguf` |
| `lumynax-infused-olmo2-1b-0425-gguf` | [`AbteeXAILab/lumynax-infused-olmo2-1b-0425-gguf`](https://huggingface.co/AbteeXAILab/lumynax-infused-olmo2-1b-0425-gguf) | `llama_cpp` | 3 | `OLMo-2-0425-1B-Instruct-Q4_K_M.gguf` |
| `lumynax-infused-olmo2-7b-1124-gguf` | [`AbteeXAILab/lumynax-infused-olmo2-7b-1124-gguf`](https://huggingface.co/AbteeXAILab/lumynax-infused-olmo2-7b-1124-gguf) | `llama_cpp` | 3 | `olmo-2-1124-7B-instruct-Q4_K_M.gguf` |
| `lumynax-infused-phi-4-text-gguf` | [`AbteeXAILab/lumynax-infused-phi-4-text-gguf`](https://huggingface.co/AbteeXAILab/lumynax-infused-phi-4-text-gguf) | `llama_cpp` | 3 | `lumynax-infused-phi-4-text-gguf-f16.gguf` |
| `lumynax-infused-phi3-mini-4k-gguf` | [`AbteeXAILab/lumynax-infused-phi3-mini-4k-gguf`](https://huggingface.co/AbteeXAILab/lumynax-infused-phi3-mini-4k-gguf) | `llama_cpp` | 3 | `Phi-3-mini-4k-instruct-q4.gguf` |
| `lumynax-infused-phi4-mini-instruct-gguf` | [`AbteeXAILab/lumynax-infused-phi4-mini-instruct-gguf`](https://huggingface.co/AbteeXAILab/lumynax-infused-phi4-mini-instruct-gguf) | `llama_cpp` | 3 | `Phi-4-mini-instruct-Q4_K_M.gguf` |
| `lumynax-infused-qwen2-audio-7b` | [`AbteeXAILab/lumynax-infused-qwen2-audio-7b`](https://huggingface.co/AbteeXAILab/lumynax-infused-qwen2-audio-7b) | `transformers` | 2 | `merged_model/model-00003-of-00005.safetensors` |
| `lumynax-infused-qwen25-15b-instruct-gguf` | [`AbteeXAILab/lumynax-infused-qwen25-15b-instruct-gguf`](https://huggingface.co/AbteeXAILab/lumynax-infused-qwen25-15b-instruct-gguf) | `llama_cpp` | 3 | `qwen2.5-1.5b-instruct-q4_k_m.gguf` |
| `lumynax-infused-qwen25-3b-instruct-gguf` | [`AbteeXAILab/lumynax-infused-qwen25-3b-instruct-gguf`](https://huggingface.co/AbteeXAILab/lumynax-infused-qwen25-3b-instruct-gguf) | `llama_cpp` | 3 | `qwen2.5-3b-instruct-q4_k_m.gguf` |
| `lumynax-infused-qwen25-7b-instruct-gguf` | [`AbteeXAILab/lumynax-infused-qwen25-7b-instruct-gguf`](https://huggingface.co/AbteeXAILab/lumynax-infused-qwen25-7b-instruct-gguf) | `llama_cpp` | 3 | `qwen2.5-7b-instruct-q3_k_m.gguf` |
| `lumynax-infused-qwen25-omni-7b-voice` | [`AbteeXAILab/lumynax-infused-qwen25-omni-7b-voice`](https://huggingface.co/AbteeXAILab/lumynax-infused-qwen25-omni-7b-voice) | `transformers` | 2 | `merged_model/model-00003-of-00005.safetensors` |
| `lumynax-infused-qwen3-06b-gguf` | [`AbteeXAILab/lumynax-infused-qwen3-06b-gguf`](https://huggingface.co/AbteeXAILab/lumynax-infused-qwen3-06b-gguf) | `llama_cpp` | 3 | `Qwen3-0.6B-Q8_0.gguf` |
| `lumynax-infused-qwen3-14b-gguf` | [`AbteeXAILab/lumynax-infused-qwen3-14b-gguf`](https://huggingface.co/AbteeXAILab/lumynax-infused-qwen3-14b-gguf) | `llama_cpp` | 3 | `Qwen3-14B-Q4_K_M.gguf` |
| `lumynax-infused-qwen3-17b-gguf` | [`AbteeXAILab/lumynax-infused-qwen3-17b-gguf`](https://huggingface.co/AbteeXAILab/lumynax-infused-qwen3-17b-gguf) | `llama_cpp` | 3 | `Qwen3-1.7B-Q8_0.gguf` |
| `lumynax-infused-qwen3-30b-a3b-gguf` | [`AbteeXAILab/lumynax-infused-qwen3-30b-a3b-gguf`](https://huggingface.co/AbteeXAILab/lumynax-infused-qwen3-30b-a3b-gguf) | `llama_cpp` | 3 | `lumynax-infused-qwen3-30b-a3b-q4_k_m.gguf` |
| `lumynax-infused-qwen3-8b-gguf` | [`AbteeXAILab/lumynax-infused-qwen3-8b-gguf`](https://huggingface.co/AbteeXAILab/lumynax-infused-qwen3-8b-gguf) | `llama_cpp` | 3 | `lumynax-infused-qwen3-8b-q4_k_m.gguf` |
| `lumynax-infused-qwen3-coder-30b-a3b-gguf` | [`AbteeXAILab/lumynax-infused-qwen3-coder-30b-a3b-gguf`](https://huggingface.co/AbteeXAILab/lumynax-infused-qwen3-coder-30b-a3b-gguf) | `llama_cpp` | 3 | `lumynax-infused-qwen3-coder-30b-a3b-q4_k_m.gguf` |
| `lumynax-infused-qwen3-text-gguf` | [`AbteeXAILab/lumynax-infused-qwen3-text-gguf`](https://huggingface.co/AbteeXAILab/lumynax-infused-qwen3-text-gguf) | `llama_cpp` | 3 | `lumynax-infused-qwen3-text-gguf-f16.gguf` |
| `lumynax-infused-smollm-135m-gguf` | [`AbteeXAILab/lumynax-infused-smollm-135m-gguf`](https://huggingface.co/AbteeXAILab/lumynax-infused-smollm-135m-gguf) | `llama_cpp` | 3 | `SmolLM-135M-Instruct.Q4_K_M.gguf` |
| `lumynax-infused-smollm2-17b-gguf` | [`AbteeXAILab/lumynax-infused-smollm2-17b-gguf`](https://huggingface.co/AbteeXAILab/lumynax-infused-smollm2-17b-gguf) | `llama_cpp` | 3 | `smollm2-1.7b-instruct-q4_k_m.gguf` |
| `lumynax-infused-smollm2-360m-gguf` | [`AbteeXAILab/lumynax-infused-smollm2-360m-gguf`](https://huggingface.co/AbteeXAILab/lumynax-infused-smollm2-360m-gguf) | `llama_cpp` | 3 | `smollm2-360m-instruct-q8_0.gguf` |
| `lumynax-infused-smollm3-3b-gguf` | [`AbteeXAILab/lumynax-infused-smollm3-3b-gguf`](https://huggingface.co/AbteeXAILab/lumynax-infused-smollm3-3b-gguf) | `llama_cpp` | 3 | `SmolLM3-Q4_K_M.gguf` |
| `lumynax-infused-zephyr-7b-beta-gguf` | [`AbteeXAILab/lumynax-infused-zephyr-7b-beta-gguf`](https://huggingface.co/AbteeXAILab/lumynax-infused-zephyr-7b-beta-gguf) | `llama_cpp` | 3 | `zephyr-7b-beta.Q4_K_M.gguf` |
| `lumynax-longctx-glm4-9b-chat-1m-gguf` | [`AbteeXAILab/lumynax-longctx-glm4-9b-chat-1m-gguf`](https://huggingface.co/AbteeXAILab/lumynax-longctx-glm4-9b-chat-1m-gguf) | `llama_cpp` | 3 | `glm-4-9b-chat-1m-Q4_K_M.gguf` |
| `lumynax-longctx-prolong-512k-instruct` | [`AbteeXAILab/lumynax-longctx-prolong-512k-instruct`](https://huggingface.co/AbteeXAILab/lumynax-longctx-prolong-512k-instruct) | `transformers` | 3 | `model-00004-of-00007.safetensors` |
| `lumynax-longctx-qwen25-7b-1m-gguf` | [`AbteeXAILab/lumynax-longctx-qwen25-7b-1m-gguf`](https://huggingface.co/AbteeXAILab/lumynax-longctx-qwen25-7b-1m-gguf) | `llama_cpp` | 3 | `Qwen2.5-7B-Instruct-1M-Q4_K_M.gguf` |
| `lumynax-longctx-yi-9b-200k` | [`AbteeXAILab/lumynax-longctx-yi-9b-200k`](https://huggingface.co/AbteeXAILab/lumynax-longctx-yi-9b-200k) | `transformers` | 3 | `model-00002-of-00004.safetensors` |
| `lumynax-math-qwen25-math-7b-gguf` | [`AbteeXAILab/lumynax-math-qwen25-math-7b-gguf`](https://huggingface.co/AbteeXAILab/lumynax-math-qwen25-math-7b-gguf) | `llama_cpp` | 3 | `Qwen2.5-Math-7B-Instruct-Q4_K_M.gguf` |
| `lumynax-moe-moonlight-16b-a3b-gguf` | [`AbteeXAILab/lumynax-moe-moonlight-16b-a3b-gguf`](https://huggingface.co/AbteeXAILab/lumynax-moe-moonlight-16b-a3b-gguf) | `llama_cpp` | 3 | `lumynax-moe-moonlight-16b-a3b-iq4_xs.gguf` |
| `lumynax-moe-olmoe-1b-7b-0924-instruct-gguf` | [`AbteeXAILab/lumynax-moe-olmoe-1b-7b-0924-instruct-gguf`](https://huggingface.co/AbteeXAILab/lumynax-moe-olmoe-1b-7b-0924-instruct-gguf) | `llama_cpp` | 3 | `OLMoE-1B-7B-0924-Instruct-Q4_K_M.gguf` |
| `lumynax-moe-olmoe-1b-7b-gguf` | [`AbteeXAILab/lumynax-moe-olmoe-1b-7b-gguf`](https://huggingface.co/AbteeXAILab/lumynax-moe-olmoe-1b-7b-gguf) | `llama_cpp` | 3 | `olmoe-1b-7b-0924-instruct-q4_k_m.gguf` |
| `lumynax-multimodal-aria-25b-moe` | [`AbteeXAILab/lumynax-multimodal-aria-25b-moe`](https://huggingface.co/AbteeXAILab/lumynax-multimodal-aria-25b-moe) | `transformers_multimodal` | 2 | `model-00001-of-00012.safetensors` |
| `lumynax-multimodal-glm46v-flash` | [`AbteeXAILab/lumynax-multimodal-glm46v-flash`](https://huggingface.co/AbteeXAILab/lumynax-multimodal-glm46v-flash) | `llama_cpp_multimodal` | 2 | `lumynax-multimodal-glm46v-flash-ud-iq2_m.gguf` |
| `lumynax-multimodal-internvl3-78b-instruct` | [`AbteeXAILab/lumynax-multimodal-internvl3-78b-instruct`](https://huggingface.co/AbteeXAILab/lumynax-multimodal-internvl3-78b-instruct) | `transformers_multimodal` | 2 | `model-00001-of-00033.safetensors` |
| `lumynax-multimodal-kimi-vl-a3b-thinking` | [`AbteeXAILab/lumynax-multimodal-kimi-vl-a3b-thinking`](https://huggingface.co/AbteeXAILab/lumynax-multimodal-kimi-vl-a3b-thinking) | `llama_cpp_multimodal` | 2 | `lumynax-multimodal-kimi-vl-a3b-thinking-q4_k_m.gguf` |
| `lumynax-multimodal-llava-next-34b` | [`AbteeXAILab/lumynax-multimodal-llava-next-34b`](https://huggingface.co/AbteeXAILab/lumynax-multimodal-llava-next-34b) | `transformers_multimodal` | 2 | `model-00006-of-00015.safetensors` |
| `lumynax-multimodal-pixtral-large-124b` | [`AbteeXAILab/lumynax-multimodal-pixtral-large-124b`](https://huggingface.co/AbteeXAILab/lumynax-multimodal-pixtral-large-124b) | `transformers_multimodal` | 2 | `consolidated-00004-of-00052.safetensors` |
| `lumynax-multimodal-qwen25-vl-72b-instruct-gguf` | [`AbteeXAILab/lumynax-multimodal-qwen25-vl-72b-instruct-gguf`](https://huggingface.co/AbteeXAILab/lumynax-multimodal-qwen25-vl-72b-instruct-gguf) | `llama_cpp_multimodal` | 3 | `Qwen2.5-VL-72B-Instruct-Q4_K_M.gguf` |
| `lumynax-nz-3b` | [`AbteeXAILab/lumynax-nz-3b`](https://huggingface.co/AbteeXAILab/lumynax-nz-3b) | `transformers` | 2 | `merged_model/model-00001-of-00055.safetensors` |
| `lumynax-nz-qwen25-coder-3b-gguf` | [`AbteeXAILab/lumynax-nz-qwen25-coder-3b-gguf`](https://huggingface.co/AbteeXAILab/lumynax-nz-qwen25-coder-3b-gguf) | `llama_cpp` | 3 | `lumynax-nz-qwen25-coder-3b-q4_k_m.gguf` |
| `lumynax-ocr-trocr-large-handwritten` | [`AbteeXAILab/lumynax-ocr-trocr-large-handwritten`](https://huggingface.co/AbteeXAILab/lumynax-ocr-trocr-large-handwritten) | `transformers` | 3 | `pytorch_model.bin` |
| `lumynax-ocr-trocr-large-printed` | [`AbteeXAILab/lumynax-ocr-trocr-large-printed`](https://huggingface.co/AbteeXAILab/lumynax-ocr-trocr-large-printed) | `transformers` | 3 | `pytorch_model.bin` |
| `lumynax-reasoning-deepseek-distill-text-gguf` | [`AbteeXAILab/lumynax-reasoning-deepseek-distill-text-gguf`](https://huggingface.co/AbteeXAILab/lumynax-reasoning-deepseek-distill-text-gguf) | `llama_cpp` | 3 | `lumynax-reasoning-deepseek-distill-text-gguf-f16.gguf` |
| `lumynax-reasoning-deepseek-prover-v2-671b-gguf` | [`AbteeXAILab/lumynax-reasoning-deepseek-prover-v2-671b-gguf`](https://huggingface.co/AbteeXAILab/lumynax-reasoning-deepseek-prover-v2-671b-gguf) | `llama_cpp` | 2 | `Q4_K_M/DeepSeek-Prover-V2-671B-Q4_K_M-00003-of-00009.gguf` |
| `lumynax-reasoning-deepseek-r1-distill-llama-70b-gguf` | [`AbteeXAILab/lumynax-reasoning-deepseek-r1-distill-llama-70b-gguf`](https://huggingface.co/AbteeXAILab/lumynax-reasoning-deepseek-r1-distill-llama-70b-gguf) | `llama_cpp` | 3 | `DeepSeek-R1-Distill-Llama-70B-Q4_K_M.gguf` |
| `lumynax-reasoning-deepseek-r1-qwen-15b-gguf` | [`AbteeXAILab/lumynax-reasoning-deepseek-r1-qwen-15b-gguf`](https://huggingface.co/AbteeXAILab/lumynax-reasoning-deepseek-r1-qwen-15b-gguf) | `llama_cpp` | 3 | `DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf` |
| `lumynax-reasoning-deepseek-r1-qwen-7b-gguf` | [`AbteeXAILab/lumynax-reasoning-deepseek-r1-qwen-7b-gguf`](https://huggingface.co/AbteeXAILab/lumynax-reasoning-deepseek-r1-qwen-7b-gguf) | `llama_cpp` | 3 | `DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf` |
| `lumynax-reasoning-glm46-355b-moe` | [`AbteeXAILab/lumynax-reasoning-glm46-355b-moe`](https://huggingface.co/AbteeXAILab/lumynax-reasoning-glm46-355b-moe) | `transformers` | 2 | `Q4_K_M/GLM-4.6-Q4_K_M-00001-of-00005.gguf` |
| `lumynax-reasoning-gpt-oss-20b-gguf` | [`AbteeXAILab/lumynax-reasoning-gpt-oss-20b-gguf`](https://huggingface.co/AbteeXAILab/lumynax-reasoning-gpt-oss-20b-gguf) | `llama_cpp` | 3 | `lumynax-reasoning-gpt-oss-20b-mxfp4.gguf` |
| `lumynax-reasoning-internlm3-8b-gguf` | [`AbteeXAILab/lumynax-reasoning-internlm3-8b-gguf`](https://huggingface.co/AbteeXAILab/lumynax-reasoning-internlm3-8b-gguf) | `llama_cpp` | 3 | `internlm3-8b-instruct-Q4_K_M.gguf` |
| `lumynax-reasoning-phi4-mini-gguf` | [`AbteeXAILab/lumynax-reasoning-phi4-mini-gguf`](https://huggingface.co/AbteeXAILab/lumynax-reasoning-phi4-mini-gguf) | `llama_cpp` | 3 | `Phi-4-mini-reasoning-Q4_K_M.gguf` |
| `lumynax-reasoning-qwq-32b-gguf` | [`AbteeXAILab/lumynax-reasoning-qwq-32b-gguf`](https://huggingface.co/AbteeXAILab/lumynax-reasoning-qwq-32b-gguf) | `llama_cpp` | 3 | `qwq-32b-q4_k_m.gguf` |
| `lumynax-reranker-bge-v2-m3` | [`AbteeXAILab/lumynax-reranker-bge-v2-m3`](https://huggingface.co/AbteeXAILab/lumynax-reranker-bge-v2-m3) | `transformers` | 3 | `model.safetensors` |
| `lumynax-speech-kokoro-82m-tts` | [`AbteeXAILab/lumynax-speech-kokoro-82m-tts`](https://huggingface.co/AbteeXAILab/lumynax-speech-kokoro-82m-tts) | `transformers` | 3 | `kokoro-v1_0.pth` |
| `lumynax-speech-whisper-large-v3-turbo` | [`AbteeXAILab/lumynax-speech-whisper-large-v3-turbo`](https://huggingface.co/AbteeXAILab/lumynax-speech-whisper-large-v3-turbo) | `transformers` | 3 | `model.safetensors` |
| `lumynax-tiny` | [`AbteeXAILab/lumynax-tiny`](https://huggingface.co/AbteeXAILab/lumynax-tiny) | `transformers` | 2 | `merged_model/model.safetensors` |
| `lumynax-tiny-qwen25-05b-gguf` | [`AbteeXAILab/lumynax-tiny-qwen25-05b-gguf`](https://huggingface.co/AbteeXAILab/lumynax-tiny-qwen25-05b-gguf) | `llama_cpp` | 3 | `lumynax-tiny-qwen25-05b-q4_k_m.gguf` |
| `lumynax-translate-nllb-200-3b` | [`AbteeXAILab/lumynax-translate-nllb-200-3b`](https://huggingface.co/AbteeXAILab/lumynax-translate-nllb-200-3b) | `transformers` | 3 | `pytorch_model-00002-of-00003.bin` |

---

## Routing behavior

Every routing decision passes through ordered gates. Models that fail any gate are rejected with a documented reason.

| Gate | Rejects when |
|---|---|
| Modality match | Requested modalities are not a subset of model modalities |
| Context length | Model `context_tokens` is below `min_context_tokens` |
| Tool support | `requires_tools=true` but the model lacks tool support |
| JSON support | `requires_json=true` but the model lacks JSON support |
| License allowlist | License ID is not in the caller allowlist |
| Jurisdictional residency | `requires_local=true` and jurisdiction is not in model residency |
| Sovereignty tier | Data sensitivity requires a higher sovereignty tier |

Surviving candidates are scored on:
- Jurisdiction fit (+8)
- Task-type tag match (+7, with +10 for coder specialization, +9 for reasoning)
- Sovereignty bonus for `iwi` / `data sovereignty` keywords (+3 x tier)
- Runtime preference (GGUF/llama.cpp gets +2.5)
- Quality rank vs cost rank tradeoff

The router returns the winner plus the full rejection log so operators can see why each candidate did or did not qualify.

---

## More commands

### Local browser console and route API

```bash
MaramaRoute serve --port 8787 --open

# Serve routed requests from pulled local GGUF models.
MaramaRoute serve --port 8787 --live-local --cache-dir ./models
```

The local server exposes:

- `GET  /health`
- `GET  /v1/models`
- `GET  /v1/local/cache`
- `GET  /v1/local/health`
- `POST /v1/route`
- `POST /v1/chat/completions`

### Ask the router which model fits

```bash
MaramaRoute route --request examples/request.code-restricted.json
```

### Inspect a single model

```bash
MaramaRoute catalog --search starcoder --limit 5
MaramaRoute compare --model lumynax-coder-starcoder2-15b-gguf --model lumynax-coder-qwen25-coder-32b-gguf
```

### Run the built-in route scenario matrix

```bash
MaramaRoute matrix
```

### Generate agent and HPE/HPC helper configs

```bash
# One command writes MaramaRoute config, aliases, agent bridge files, and HPE scaffold.
MaramaRoute setup qwen25-7b --all-targets --hpe --backend vllm

# Command bridge JSON for coding-agent workspaces.
MaramaRoute agent-config --target claude-code --model qwen25-7b
MaramaRoute agent-config --target codex --model qwen25-7b
MaramaRoute agent-config --target continue --model qwen25-7b
MaramaRoute agent-config --target opencode --model qwen25-7b
MaramaRoute agent-config --target litellm --model qwen25-7b
MaramaRoute agent-config --target tabby --model qwen25-7b
MaramaRoute agent-init --target claude-code --model qwen25-7b
MaramaRoute agent-init --target codex --model qwen25-7b
MaramaRoute agent init --target claude-code --model qwen25-7b
MaramaRoute agent doctor --target claude-code --model qwen25-7b

# HPE/HPC Slurm job script, live gateway config, backend launch, and run notes.
MaramaRoute hpe plan qwen25-7b --backend vllm
MaramaRoute hpe-job qwen25-05b --mode serve > marama-route.slurm
MaramaRoute hpe-job qwen25-7b --backend vllm --gpus 1 > marama-route.slurm
MaramaRoute hpe init qwen25-7b --backend vllm --gpus 1
MaramaRoute hpe init qwen25-7b --backend nim --backend-base-url http://127.0.0.1:8000/v1
MaramaRoute hpe init qwen25-7b --backend nemo --backend-command ./start-nemo-backend.sh
MaramaRoute hpe tunnel

# Generic local command bridge config.
MaramaRoute agent-config --target generic --base-url http://127.0.0.1:8787/v1
```

### Audit receipts and registry maintenance

```bash
MaramaRoute audit record --request examples/request.code-restricted.json
MaramaRoute audit list
MaramaRoute audit export --output marama-route-audit.json
MaramaRoute update-registry --dry-run
MaramaRoute update-registry --dry-run --diff
```

### Emit an OpenCode provider config (drop into `~/.opencode/providers/`)

```bash
MaramaRoute opencode-config > ~/.opencode/providers/lumynax.json
```

### Drive it from Python

```python
from marama_route import (
    SovereignModelRouter,
    RoutingRequest,
    load_model_registry,
)
from pathlib import Path

models = load_model_registry(Path("./my_registry.json"))
router = SovereignModelRouter(models)

decision = router.route(
    RoutingRequest(
        prompt="Translate this paragraph to te reo Maori",
        task_type="general",
        jurisdiction="NZ",
        data_sensitivity="personal",   # routes only to sovereignty_tier >= 2
        requires_local=True,
    )
)

print(decision.selected_model.model_id)   # e.g. lumynax-translate-nllb-200-3b
print(decision.reasons)                    # rationale
print(decision.scores)                     # full scorecard
```

---

## Why this exists

LumynaX is built by **AbteeX AI Labs** in Auckland, Aotearoa New Zealand. Three principles drive the design:

1. **Sovereignty over convenience.** Every routing decision can be justified to a Maori data-governance reviewer, a privacy officer, or an iwi advisory board. The registry, the routing log, and the policy gates exist *for that conversation*.

2. **Local-first by default.** Tier-3+ models run on machines the data owner controls. The router never silently escalates a sensitive request to a remote frontier model.

3. **Open weights, open license, open evals.** Apache-2.0 on this routing layer. Upstream model licenses surfaced honestly per entry. No vendor lock-in.

Every model card states its provenance. Every routing decision is auditable. Every sovereignty constraint is testable.

---

## Companion products

- **[`abteex-sovereigncode`](https://pypi.org/project/abteex-sovereigncode/)** - Policy API and audit ledger for coding agents. Pairs with MaramaRoute when you need per-request policy enforcement and tamper-evident logs.
- **[LumynaX model family](https://huggingface.co/AbteeXAILab)** - 98 sovereign-tagged model repos on Hugging Face, all routable through MaramaRoute out of the box.
- **[LumynaX release monorepo](https://github.com/Aimaghsoodi/lumynax-release)** - the public release repo for MaramaRoute, SovereignCode, model scaffolds, Spaces, and publishing tooling.

---

## Links

- **PyPI:** <https://pypi.org/project/lumynax-marama-route/>
- **npm:** <https://www.npmjs.com/package/lumynax-marama-route>
- **Hugging Face:** <https://huggingface.co/AbteeXAILab/marama-route>
- **GitHub:** <https://github.com/Aimaghsoodi/lumynax-release>
- **Website:** <https://lumynax.com> | <https://abteex.com>

---

## Download stats

Live package counters:

![npm downloads by month and version](https://raw.githubusercontent.com/Aimaghsoodi/lumynax-release/main/docs/marama-route-npm-downloads.svg)

The npm public API exposes package downloads by day/month and per-version downloads for the previous 7 days. It does not publish historical per-version-by-month downloads, so this diagram combines monthly package totals since first publish with the current all-version split.

[![npm downloads per month](https://img.shields.io/npm/dm/lumynax-marama-route.svg?label=npm%20downloads%2Fmonth&color=2ea44f)](https://www.npmjs.com/package/lumynax-marama-route)
[![npm total downloads](https://img.shields.io/npm/dt/lumynax-marama-route.svg?label=npm%20downloads%20total&color=2ea44f)](https://www.npmjs.com/package/lumynax-marama-route)
[![PyPI downloads](https://static.pepy.tech/badge/lumynax-marama-route)](https://pepy.tech/project/lumynax-marama-route)
[![PyPI downloads per month](https://static.pepy.tech/badge/lumynax-marama-route/month)](https://pepy.tech/project/lumynax-marama-route)
[![Hugging Face downloads](https://img.shields.io/badge/dynamic/json?label=HF%20downloads&query=downloads&url=https%3A%2F%2Fhuggingface.co%2Fapi%2Fmodels%2FAbteeXAILab%2Fmarama-route&color=ffcc00)](https://huggingface.co/AbteeXAILab/marama-route)

Primary source: <https://github.com/Aimaghsoodi/lumynax-release>

---

## License

Apache-2.0 - see [LICENSE](LICENSE).

Upstream models retain their own licenses; check each model card before commercial deployment.

