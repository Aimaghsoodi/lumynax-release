# Runbook · Add a model to the live API (zero downtime)

```bash
# 1. Pull weights + register route + restart only the relevant service
bash scripts/08-add-model.sh <slug>

# 2. Verify
ADMIN_KEY=$(cat state/admin-key)
curl -fsS -H "Authorization: Bearer $ADMIN_KEY" http://localhost:8080/v1/models \
  | jq -r '.data[].id' | grep <slug>

# 3. Hit it
curl -H "Authorization: Bearer $ADMIN_KEY" -H "Content-Type: application/json" \
  -d "{\"model\":\"<slug>\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}]}" \
  http://localhost:8080/v1/chat/completions | jq -r '.choices[0].message.content'
```

## Picking the right model

```bash
# Browse the full registry
jq -r '.models[] | "\(.repo_id) \(.total_params_b // "?")B \(.modalities | join(",")) tier=\(.sovereignty_tier)"' \
  env/registry.json | sort
```

Recommended additions for common asks:

| Customer asks for… | Add |
| --- | --- |
| Better reasoning | `lumynax-reasoning-qwq-32b-gguf` (needs 24+ GB VRAM) |
| Multilingual / te reo | `lumynax-translate-nllb-200-3b`, `lumynax-longctx-glm4-9b-chat-1m-gguf` |
| Vision | `lumynax-multimodal-qwen25-vl-72b-instruct-gguf` (needs 48 GB) |
| Speech-to-text | `lumynax-speech-whisper-large-v3-turbo` |
| Embeddings | `lumynax-embed-bge-m3` + `lumynax-reranker-bge-v2-m3` |
| Long-context document analysis | `lumynax-longctx-prolong-512k-instruct`, `lumynax-longctx-yi-9b-200k` |
| Frontier code | `lumynax-frontier-coder-qwen3-480b-a35b-gguf` (needs 200+ GB VRAM, multi-GPU) |

## Capacity planning

Each model server uses 1 GPU. To serve N models concurrently on M GPUs, choose models whose VRAM footprints fit. A common pattern:
- 1× H100: 70B Q4 (fully) **or** 4× 7-13B models (sharing)
- 2× H100: 200B-class MoE **or** 1× 70B + 4× smaller
- 8× H100: any single frontier MoE (Prover-V2-671B, Qwen3-Coder-480B, DeepSeek-V2.5)

## Remove a model

```bash
# Stop + remove its container, drop its route entry
docker compose -f compose/docker-compose.yml stop llama-<slug>
docker compose -f compose/docker-compose.yml rm -f llama-<slug>
python3 -c "import json,pathlib; p=pathlib.Path('env/routes.json'); d=json.loads(p.read_text()); d.pop('<slug>', None); p.write_text(json.dumps(d, indent=2))"
docker compose -f compose/docker-compose.yml restart gateway
# Optional: free disk
rm -rf state/weights/<slug>
```
