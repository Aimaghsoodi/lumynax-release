# LumynaX MaramaRoute Product Blueprint

## One-Sentence Product

MaramaRoute is an OpenRouter-style model router for LumynaX releases that gives
apps one OpenAI-compatible endpoint while enforcing residency, capability,
license, sensitivity, and fallback rules.

## Core User Jobs

| User | Job | MaramaRoute Response |
| --- | --- | --- |
| SovereignCode | Select a resident coding model for a governed workspace. | Code task route with NZ residency and JSON/tool gates. |
| Internal app | Call one endpoint instead of hard-coding model ids. | `/v1/models`, `/v1/route`, and `/v1/chat/completions` contract. |
| Operator | Know why a model was selected or rejected. | Route decision with scores, reasons, rejections, and request hash. |
| Model publisher | Add new LumynaX releases without changing every client. | Registry compiler and aliases. |
| Enterprise tenant | Restrict models by region, license, runtime, and sensitivity. | Future tenant policy packs and allowlists. |

## Router Product Pillars

1. One endpoint: OpenAI-compatible clients can point at MaramaRoute.
2. Sovereign default: New Zealand residency is the default route constraint.
3. Model provenance: every selectable model carries repo, artifact, license,
   runtime, modality, context, and validation metadata.
4. Deterministic audit: decisions are explainable and repeatable for the same
   registry and request.
5. Runtime independence: route selection is separate from the backend that runs
   llama.cpp, Transformers, embeddings, speech, or multimodal models.

## Minimum Gateway Loop

```text
client sends OpenAI chat request
  -> parse route hints
  -> infer task and modalities
  -> apply capability gates
  -> apply sovereignty and license gates
  -> score accepted models
  -> return selected model and fallbacks
  -> future: invoke runtime adapter
  -> return OpenAI-compatible response with route metadata
```

## Model Alias Strategy

| Alias | Intended Use | Route Bias |
| --- | --- | --- |
| `lumynax/auto` | General application calls. | Best resident general model. |
| `lumynax/code` | Coding agents and repo work. | Coder tags, JSON support, tool support. |
| `lumynax/reasoning` | Planning, analysis, evaluation. | Reasoning tags and stronger quality rank. |
| `lumynax/multimodal` | Image plus text requests. | Multimodal runtime and policy-permitted residency. |
| `lumynax/local` | Sensitive tenant work. | Local GGUF or resident runtime only. |

## Runtime Adapters To Build Next

| Adapter | Purpose | First Implementation |
| --- | --- | --- |
| llama.cpp HTTP | Run GGUF models behind a local or tenant endpoint. | Forward OpenAI chat payload with selected model path. |
| Transformers | Run safetensors or multimodal packages. | Python worker with model cache and VRAM guard. |
| Embeddings | Serve retrieval models. | `/v1/embeddings` compatible response. |
| Speech | Serve Whisper/Kokoro-style packages. | Separate speech endpoints after text route is stable. |
| Hosted LumynaX | Private hosted runtime. | Tenant auth, quotas, and audit export. |

## Commercial Controls

| Control | Why it matters |
| --- | --- |
| API keys | Required for OpenCode, IDEs, and internal apps. |
| Tenant quotas | Prevent runaway local or hosted compute spend. |
| Model allowlists | Keep restricted tenants away from unsuitable models. |
| Route metadata | Lets customers prove why a model was used. |
| Prompt retention flag | Supports privacy-sensitive deployments by default. |
| Registry signing | Prevents silent model substitution. |

## First Non-Negotiables

- Do not silently route restricted NZ data to a non-resident model.
- Do not pick a model that lacks required modality, JSON, or tool support.
- Do not hide rejection reasons from route metadata.
- Do not retain prompts by default for high-sensitivity routes.
- Do not let runtime adapters substitute models outside the route decision.
