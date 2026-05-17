# LumynaX MaramaRoute Architecture

## North Star

MaramaRoute should become the sovereign control plane for all LumynaX model use. A developer should be able to send a request to one endpoint and get a model that is capable, licensed, resident, auditable, and aligned with the sensitivity of the data.

## Control Plane

```text
Client request
  -> Request classifier
  -> Sovereignty and license gates
  -> LumynaX registry
  -> Scoring and fallback planner
  -> Runtime adapter
  -> Audit ledger
  -> Response
```

## API Surface

Planned API:

- `GET /v1/models`
- `POST /v1/chat/completions`
- `POST /v1/embeddings`
- `POST /v1/route`
- `GET /v1/route/{decision_id}`

The first implementation focuses on deterministic route decisions from a registry file.

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
| P1 OpenAI-compatible API | `/v1/models`, `/v1/route`, `/v1/chat/completions` wrapper. |
| P2 Live runtime adapters | llama.cpp, llama-cpp-python, Transformers, embedding, multimodal adapters. |
| P3 Tenant policy packs | Per-customer region, license, sensitivity, and model allowlist rules. |
| P4 Evaluation loop | Quality, acceptance, speed, and safety metrics by model. |
| P5 Hosted control plane | Private customer gateway with signed route/audit records. |

## Aesthetic Direction

The public surface should match AbteeX/LumynaX:

- Warm white paper.
- Black editorial typography.
- Amber route and status markers.
- Thin rules, mono labels, and compact evidence tables.
- No generic model marketplace neon theme.
