# MaramaRoute Gateway Contract

## Goal

Expose the LumynaX model registry through a familiar OpenAI/OpenRouter-style
surface while keeping routing constrained by New Zealand residency, sensitivity,
runtime, capability, and audit requirements.

## Endpoint Plan

| Endpoint | Status | Purpose |
| --- | --- | --- |
| `GET /v1/models` | CLI dry-run implemented | Return OpenAI-compatible model list from the LumynaX registry. |
| `POST /v1/route` | deterministic router implemented | Return selected model, fallbacks, rejections, reasons, and scores. |
| `POST /v1/chat/completions` | CLI dry-run implemented | Accept OpenAI-compatible chat payload, route it, then future-forward to runtime. |
| `POST /v1/embeddings` | planned | Route embedding calls to LumynaX embedding models. |
| `GET /v1/route/{decision_id}` | planned | Retrieve route metadata without storing sensitive prompt text by default. |

## Chat Request Extensions

Standard OpenAI-compatible fields are accepted:

- `model`
- `messages`
- `tools`
- `response_format`
- `stream`
- `temperature`
- `max_tokens`

MaramaRoute-specific routing hints live under `route`, `routing`, or
`metadata.marama_route`:

```json
{
  "model": "lumynax/auto",
  "messages": [{ "role": "user", "content": "Refactor this Python function." }],
  "route": {
    "jurisdiction": "NZ",
    "data_sensitivity": "restricted",
    "task_type": "code",
    "requires_local": true,
    "requires_json": true,
    "max_fallbacks": 3
  }
}
```

If routing hints are missing, MaramaRoute defaults to:

| Field | Default |
| --- | --- |
| `jurisdiction` | `NZ` |
| `data_sensitivity` | `internal` |
| `requires_local` | `true` |
| `min_context_tokens` | `4096` |
| `max_fallbacks` | `3` |

## Response Metadata

The dry-run chat response is shaped like a chat completion and includes
`marama_route` metadata:

```json
{
  "object": "chat.completion",
  "model": "lumynax-coder-qwen25-7b-instruct-gguf",
  "choices": [{ "finish_reason": "route_only" }],
  "marama_route": {
    "dry_run": true,
    "selected_model": {},
    "fallback_models": [],
    "rejected_count": 12,
    "reasons": [],
    "scores": {},
    "request_hash": "..."
  }
}
```

The future live gateway should replace `route_only` with the actual backend
finish reason and keep the route metadata attached for audit.

## Routing Gates

1. Modalities: text, image, audio, embedding, vision.
2. Context length.
3. Tool and JSON support.
4. License allowlist.
5. Residency and `requires_local`.
6. Sovereignty tier for high-sensitivity data.
7. Task, runtime, quality, cost, and active-parameter score.

## Runtime Adapter Contract

A runtime adapter receives:

| Field | Meaning |
| --- | --- |
| `selected_model` | Registry entry selected by the router. |
| `chat_payload` | Original OpenAI-compatible payload. |
| `route_decision` | Full route decision for audit and fallback. |
| `tenant_policy` | Future policy pack with quotas and allowlists. |

It must return an OpenAI-compatible response and must not silently substitute a
model outside the route decision.
