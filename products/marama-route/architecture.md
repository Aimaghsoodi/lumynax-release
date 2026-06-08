# LumynaX MaramaRoute Architecture

## North Star

MaramaRoute is the sovereign control plane for LumynaX model use. A developer should be able to install one package, open a conversational model picker, list the AbteeXAILab Hugging Face catalog, pull a selected model, route governed requests, and run local GGUF weights when the local runtime is installed.

## Control Plane

```text
Operator request
  -> Bundled LumynaX registry
  -> Capability, sovereignty, license, and residency gates
  -> Scoring and fallback planner
  -> Local cache / Hugging Face pull
  -> Runtime adapter
  -> Audit receipt
```

## API Surface

Implemented surface:

- `GET /health`
- `GET /v1/models`
- `POST /v1/route`
- `POST /v1/chat/completions`
- `GET /api/health`
- `GET /api/models`
- `POST /api/route`
- `POST /api/catalog`
- `POST /api/compare`
- `POST /api/matrix`
- `POST /api/opencode-config`

The CLI surface also includes `chat`, `catalog`, `models`, `analytics`, `pull`, `local`, `run`, `route`, `dry-run`, `compare`, `matrix`, `ui`, and `serve`.

## Scoring Signals

| Signal | Reason |
| --- | --- |
| Residency match | Keeps governed data inside approved regions. |
| Sovereignty tier | Allows policy packs to enforce stronger local controls. |
| Task tags | Routes code, reasoning, embedding, and multimodal tasks to specialised models. |
| Runtime | Prefers local GGUF / llama.cpp for sensitive work. |
| Quality rank | Keeps stronger models ahead when policy allows them. |
| Cost rank | Avoids oversized models when smaller models are sufficient. |
| Active parameters | Helps sparse MoE models compete when active footprint is small. |

## Launch Milestones

| Milestone | Outcome |
| --- | --- |
| P0 scaffold | Registry, router, CLI, examples, docs, tests. |
| P1 local catalog | Full AbteeXAILab Hugging Face model list bundled in the package. |
| P2 model pull | On-demand artifact download into the MaramaRoute cache. |
| P3 conversational CLI | Model picker, pull prompt, and terminal chat loop. |
| P4 local run | GGUF execution through `llama-cpp-python` for pulled models. |
| P5 tenant policy packs | Per-customer region, license, sensitivity, and model allowlist rules. |
| P6 evaluation loop | Quality, acceptance, speed, and safety metrics by model. |
| P7 hosted control plane | Private customer gateway with signed route/audit records. |

## Aesthetic Direction

The public surface should match AbteeX/LumynaX:

- Warm white paper.
- Black editorial typography.
- Amber route and status markers.
- Thin rules, mono labels, and compact evidence tables.
- No generic model marketplace theme.
