# Runtime integrations — LumynaX × your tools

98 LumynaX models, plugged into the runtimes you already use. Every model exposes an **OpenAI-compatible** HTTP endpoint via one of three paths.

## Compatibility matrix

| Runtime | GGUF models | Safetensors models | Notes |
|---|---|---|---|
| **llama.cpp** / `llama-server` | ✅ native | — | The default for any `*-gguf` repo. OpenAI-compatible at `/v1`. |
| **Ollama** | ✅ via `ollama/Modelfile` | — | `ollama create lumynax-<slug> -f ollama/Modelfile && ollama run lumynax-<slug>` |
| **LM Studio** | ✅ search by repo name | partial (MLX on Mac) | LM Studio auto-discovers any HF `*-gguf` repo when you paste the slug. |
| **vLLM** | partial (gguf flag) | ✅ native | `vllm serve AbteeXAILab/<slug>` for transformers/safetensors models. |
| **text-generation-webui** | ✅ | ✅ | Standard loader works against the HF repo. |
| **OpenWebUI** | ✅ via llama.cpp | ✅ via vLLM | Point OpenWebUI at the local OpenAI endpoint. |
| **OpenCode** (sst/opencode) | ✅ | ✅ | Use `lumynax opencode <slug>` to emit a provider config. |
| **Continue / Cursor / Aider** | ✅ | ✅ | Any OpenAI-compatible client works once the server is up. |

## One-line server with the LumynaX CLI

```bash
pip install lumynax
lumynax serve lumynax-coder-deepseek-v2-lite-16b-gguf   # auto-detect, start OpenAI server on :8080
lumynax serve lumynax-frontier-qwen25-72b-instruct-gguf --port 8000
lumynax serve lumynax-multimodal-internvl3-78b-instruct --backend vllm
```

The CLI picks **llama.cpp** for GGUF repos and **vLLM** (falling back to transformers) for safetensors repos. All servers expose the same `/v1/chat/completions` shape, so the same client code works against any LumynaX model.

## Direct: llama.cpp server (GGUF)

```bash
pip install "llama-cpp-python[server]"
hf download AbteeXAILab/lumynax-coder-deepseek-v2-lite-16b-gguf --local-dir m
python -m llama_cpp.server --model m/DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf --port 8080 --n_ctx 16384
# Now POST to http://localhost:8080/v1/chat/completions
```

## Direct: vLLM (safetensors)

```bash
pip install vllm
vllm serve AbteeXAILab/lumynax-frontier-olmo2-32b-instruct \
  --port 8000 --max-model-len 4096 --dtype auto
# Same OpenAI-compatible /v1 endpoints
```

vLLM-ready repos in the family (safetensors, no GGUF dependency):

- `lumynax-frontier-qwen3-235b-a22b-instruct` · `lumynax-frontier-minimax-m2-230b`
- `lumynax-frontier-olmo2-32b-instruct` · `lumynax-multimodal-internvl3-78b-instruct`
- `lumynax-multimodal-pixtral-large-124b` · `lumynax-multimodal-llava-next-34b`
- `lumynax-multimodal-aria-25b-moe` · `lumynax-reasoning-glm46-355b-moe`
- `lumynax-longctx-prolong-512k-instruct` · `lumynax-longctx-yi-9b-200k`
- All speech / OCR / doc / embed / reranker / guard models (Whisper, Nougat, Donut, TrOCR, LayoutLM, Table-Transformer, BGE-reranker, Nomic-embed, Granite-embed, Text-Moderation, NLLB-200, Kokoro)

## Direct: Ollama

Every repo ships `ollama/Modelfile` referencing the GGUF mirror on HF:

```bash
hf download AbteeXAILab/lumynax-chat-hermes-3-llama31-8b-gguf --local-dir m
cd m
ollama create lumynax-hermes-3 -f ollama/Modelfile
ollama run lumynax-hermes-3
```

## Direct: LM Studio

Open LM Studio → **Discover** → paste a LumynaX slug (e.g. `AbteeXAILab/lumynax-frontier-mixtral-8x22b-instruct-gguf`) and pick the Q4_K_M shard. LM Studio auto-loads, exposes an OpenAI server on `http://localhost:1234/v1`.

For safetensors repos that don't have a GGUF, LM Studio won't load them directly — use the `lumynax serve` path or vLLM.

## OpenCode integration

```bash
lumynax serve lumynax-coder-deepseek-v2-lite-16b-gguf --port 8080 &
lumynax opencode lumynax-coder-deepseek-v2-lite-16b-gguf > ~/.opencode/providers/lumynax.json
opencode   # picks up the local provider
```

The emitted JSON points OpenCode at the local OpenAI server with LumynaX-flavoured system prompt:

```json
{
  "id": "lumynax-deepseek-v2-lite",
  "type": "openai-compatible",
  "base_url": "http://localhost:8080/v1",
  "api_key": "lumynax-local",
  "models": [
    { "id": "lumynax-coder-deepseek-v2-lite-16b-gguf",
      "context_window": 163840,
      "supports_tools": true,
      "supports_json": true }
  ],
  "system": "You are LumynaX, the AbteeX AI Labs assistant. Ko te marama te tuapapa..."
}
```

OpenCode then talks to the local server with the right system prompt and tool schemas — no cloud, no per-token cost, no jurisdiction risk.

## Routing first, then serving

The full LumynaX architecture is **MaramaRoute → SovereignCode policy → model server**:

```bash
# 1. Ask MaramaRoute to pick the right model for your request
lumynax route "fix this Python bug" --local --tools
# → returns: lumynax-coder-deepseek-v2-lite-16b-gguf

# 2. Serve that model
lumynax serve lumynax-coder-deepseek-v2-lite-16b-gguf

# 3. Wire your client (OpenCode / Continue / Cursor / your code) to localhost:8080
```

For multi-model routing (where the model changes per request based on the prompt), put a thin OpenAI-compatible router in front that calls `lumynax route` per request and forwards to the selected model's server. The SovereignCode gateway in `products/sovereigncode/` does exactly this with policy gates in front.

## Hardware notes

- **GGUF Q4_K_M** runs on consumer hardware (16 GB VRAM handles up to 13B, 24 GB up to 30B, 48 GB up to 70B, CPU fallback always available)
- **safetensors bf16 frontier MoE** (Qwen3-235B, DeepSeek-V3, GLM-4.6, MiniMax-M2) wants multi-GPU or A100/H100 territory
- **Multimodal safetensors** (Pixtral-Large, InternVL3-78B, LLaVA-Next-34B) wants 80+ GB VRAM for full precision; use GGUF mirrors for smaller setups
- **Embedders / OCR / safety classifiers** all fit on CPU or 8 GB GPU comfortably

## Mac / MLX

For Apple Silicon, LM Studio supports MLX format. Most LumynaX upstreams have community MLX mirrors (`mlx-community/<original-name>`); we don't currently mirror those into the org but the model cards link out to them where they exist.
