---
license: apache-2.0
library_name: custom
tags:
- abteex-ai-labs
- lumynax
- marama-route
- model-router
- sovereign-ai
- governance
- new-zealand
- aotearoa
- openrouter-alternative
- local-first
language:
- en
- mi
---

# LumynaX MaramaRoute

<!-- abteex-marama-route-card:v1 -->

<p align="center"><em>Sovereign intelligence, held in the light.</em></p>
<p align="center"><em>Ko te mārama te tūāpapa &mdash; the light is the foundation.</em></p>

<p align="center">
  <strong>A sovereign model router for the LumynaX release family.</strong><br/>
  AbteeX AI Labs &mdash; Aotearoa New Zealand.
</p>

<p align="center">
  <a href="#what-it-is">What it is</a> &middot;
  <a href="#quickstart">Quickstart</a> &middot;
  <a href="#routing-contract">Routing contract</a> &middot;
  <a href="#scoring-signals">Scoring</a> &middot;
  <a href="#registry">Registry</a> &middot;
  <a href="#roadmap">Roadmap</a> &middot;
  <a href="#companion-products">Companions</a>
</p>

![MaramaRoute](https://img.shields.io/badge/LumynaX-MaramaRoute-e08a2c?style=for-the-badge) ![Stage scaffold](https://img.shields.io/badge/stage-product%20scaffold-0a0a0b?style=for-the-badge) ![Runtime python](https://img.shields.io/badge/runtime-python%203.10%2B-726b62?style=for-the-badge) ![License Apache 2.0](https://img.shields.io/badge/license-Apache--2.0-9a5416?style=for-the-badge) ![Card v1](https://img.shields.io/badge/card-v1-111827?style=for-the-badge)

## What It Is

**LumynaX MaramaRoute** is the AbteeX AI Labs sovereign model router for LumynaX releases. It is similar in spirit to OpenRouter, but it is *not* a general marketplace. It is a **LumynaX-first** routing layer that selects models based on sovereignty, residency, license, runtime, modality, task fit, context length, and operational risk.

> *Marama* = light, clarity. The router brings the right model into the light for the work at hand.

## What It Routes To

- Local GGUF models.
- MoE and frontier-style LumynaX packages.
- Multimodal LumynaX packages (text + image / audio / voice).
- Embedding and retrieval models.
- Reasoning and coding variants.
- Future tenant-specific sovereign models.

The bundled registry covers **50 models** across the [AbteeXAILab](https://huggingface.co/AbteeXAILab) family.

## Quickstart

Clone the repo:

```bash
hf download AbteeXAILab/marama-route --local-dir marama-route --repo-type model
cd marama-route
pip install -r requirements.txt
```

Route a **restricted code** request (requires local runtime, NZ residency):

```bash
python -m marama_route.cli route \
  --registry configs/lumynax_model_registry.json \
  --request examples/request.code-restricted.json
```

Expected: a LumynaX coder or Qwen-family GGUF package with NZ residency constraints satisfied, plus an ordered list of fallbacks.

Route a **public multimodal** request:

```bash
python -m marama_route.cli route \
  --registry configs/lumynax_model_registry.json \
  --request examples/request.multimodal-public.json
```

Expected: a multimodal LumynaX package with `text + image` modalities.

## Routing Contract

Every request is evaluated through ordered gates:

| Gate | Purpose |
| --- | --- |
| **Capability** | Modalities, context length, tool use, JSON mode, task fit. |
| **Sovereignty** | Jurisdiction, residency, data sensitivity, local runtime requirement. |
| **License** | Optional license allowlist and model-card provenance. |
| **Runtime** | `llama.cpp`, Transformers, embedding, multimodal, or hosted adapter. |
| **Score** | Quality, cost, active parameters, task tags, and fallback strength. |
| **Audit** | Decision, rejected models, selected model, and fallbacks are recorded. |

## Scoring Signals

| Signal | Reason |
| --- | --- |
| Residency match | Keeps governed data inside approved regions. |
| Sovereignty tier | Allows policy packs to enforce stronger local controls. |
| Task tags | Routes code, reasoning, embedding, and multimodal tasks to specialised models. |
| Runtime | Prefers local GGUF / `llama.cpp` for sensitive work. |
| Quality rank | Keeps stronger models ahead when policy allows them. |
| Cost rank | Avoids oversized models when smaller models are sufficient. |
| Active parameters | Helps sparse MoE models compete when active footprint is small. |

## Registry

The registry (`configs/lumynax_model_registry.json`) is a flat array of model entries. Each entry carries:

| Field | Meaning |
| --- | --- |
| `repo_id` | Hugging Face repository id. |
| `family` | Upstream family (`qwen`, `gemma`, `phi`, `granite`, `olmo`, `mistral`, `deepseek`, `embedding`, ...). |
| `runtime` | `llama_cpp`, `transformers`, `python_embedding`, `llama_cpp_multimodal`, ... |
| `modalities` | `text`, `image`, `audio`, `embedding`. |
| `context_tokens` | Max context window. |
| `jurisdiction` / `residency` | Where the model is approved to run. |
| `sovereignty_tier` | 1 (open) &rarr; 5 (strict). |
| `quality_rank` / `cost_rank` | Routing scorer inputs. |
| `supports_tools` / `supports_json` | Capability flags. |
| `total_params_b` / `active_params_b` | Total / active parameter counts. |

Refresh the registry from a fresh HF card report:

```bash
python -m marama_route.build_registry --report path/to/hf-model-card-report.json --out configs/lumynax_model_registry.json
```

## Planned API Surface

| Endpoint | Purpose |
| --- | --- |
| `GET /v1/models` | List candidate models. |
| `POST /v1/route` | Return a deterministic route decision. |
| `GET /v1/route/{decision_id}` | Retrieve a stored decision. |
| `POST /v1/chat/completions` | OpenAI-compatible completions wrapper. |
| `POST /v1/embeddings` | Embedding wrapper. |

The first implementation focuses on the **deterministic router and CLI** &mdash; the HTTP gateway ships in P1.

## Roadmap

| Milestone | Outcome |
| --- | --- |
| **P0 scaffold** *(now)* | Registry, router, CLI, examples, docs, tests. |
| **P1 OpenAI-compatible API** | `/v1/models`, `/v1/route`, `/v1/chat/completions` wrapper. |
| **P2 Live runtime adapters** | `llama.cpp`, `llama-cpp-python`, Transformers, embedding, multimodal. |
| **P3 Tenant policy packs** | Per-customer region, license, sensitivity, allowlist rules. |
| **P4 Evaluation loop** | Quality, acceptance, speed, safety metrics per model. |
| **P5 Hosted control plane** | Private customer gateway with signed route + audit records. |

## Companion Products

| Product | Purpose |
| --- | --- |
| [AbteeX SovereignCode](https://huggingface.co/AbteeXAILab/sovereigncode) | Local-first coding agent with Data Capsule policy. Uses MaramaRoute for every model call. |
| [LumynaX Live Demo](https://huggingface.co/spaces/AbteeXAILab/lumynax-live-demo) | Public browser demo. |
| [MaramaRoute Live](https://huggingface.co/spaces/AbteeXAILab/marama-route-demo) | Interactive router &mdash; paste a request, see the selected model and fallbacks. |
| [AbteeXAILab on Hugging Face](https://huggingface.co/AbteeXAILab) | The full LumynaX release family. |

## Aotearoa Kaupapa

MaramaRoute is built in and for Aotearoa New Zealand. Routing is not just performance &mdash; it is *kaitiakitanga*: guardianship of where data goes, which model touches it, and what audit trail remains.

## Limitations & Responsible Use

- The router enforces declared registry metadata and policy. It cannot detect undeclared licence or residency issues.
- The current release is a *product scaffold*. The hosted gateway, runtime adapters, and tenant policy server ship in P1–P5.
- For high-impact routing, pair MaramaRoute with [SovereignCode](https://huggingface.co/AbteeXAILab/sovereigncode) policy enforcement and human review.

---

<p align="center"><em>Local roots, global work. &middot; Sovereignty is a design property, not a deployment option.</em></p>
<p align="center"><sub>AbteeX AI Labs &middot; <a href="https://abteex.com">abteex.com</a> &middot; <a href="https://lumynax.com">lumynax.com</a> &middot; <a href="https://huggingface.co/AbteeXAILab">huggingface.co/AbteeXAILab</a></sub></p>
