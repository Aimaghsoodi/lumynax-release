# Deploying LumynaX in an HPE environment

Three deployment paths, picked by your operating model:

| Path | When | What you get |
|---|---|---|
| **Single-node Docker** | ProLiant DL/Apollo with NVIDIA GPU(s), 1 box | Gateway + SearXNG + 3 sample models in `docker compose up` |
| **HPE GreenLake / OpenShift / vanilla Kubernetes** | Multi-node cluster | Helm chart deploys gateway + SearXNG + N model servers behind an Ingress |
| **Air-gapped bare metal** | No internet, fully sovereign | Same Helm chart with pre-pulled images and pre-mirrored weights |

All three converge on **one OpenAI-compatible API endpoint** that fronts every LumynaX model and a self-hosted **web_search** tool that respects sovereignty.

---

## What's deployed

```
                                     ┌──────────────┐
clients ──HTTPS──► [Ingress] ──► [LumynaX Gateway] ──┼──► llama-server (model A) ──► /v1/chat
   (OpenCode,                          ▲ ▲           │      (GGUF)
    Continue,                          │ │           ├──► llama-server (model B)
    your code,                policy │ │ audit      ├──► vLLM (model C, safetensors)
    cursor, etc.)            (capsule)│ │ (sha256)   ├──► vLLM (model D)
                                      │ │           ▼
                                  per-tenant     [SearXNG]  ◄── web_search tool
                                  API keys      self-hosted
                                                search index
```

- **Gateway** is the only public surface. It speaks OpenAI's HTTP shape on `/v1/*`.
- **SovereignCode policy gates** run on every request before forwarding to a backend.
- **SearXNG** is private to the cluster — models call `web_search` and get internet results without any external SDK or third-party tracker.
- **Audit log** is hash-chained (SHA-256 over canonical JSON) and written to a PVC/volume.

---

## Path 1 — Single-node Docker (fastest start)

```bash
git clone https://github.com/Aimaghsoodi/lumynax-release
cd lumynax-release/deployments

# 1. Provide API keys (rotate the examples first)
cp gateway/config/api-keys.example.json gateway/config/api-keys.json
cp gateway/config/routes.example.json   gateway/config/routes.json

# 2. Fetch the live registry once (becomes the gateway's model catalog)
curl -fsSL https://huggingface.co/AbteeXAILab/marama-route/resolve/main/configs/lumynax_model_registry.json \
  -o gateway/config/registry.json

# 3. Set a SearXNG secret and start
export SEARXNG_SECRET=$(openssl rand -hex 32)
docker compose up -d

# 4. Verify
curl -s http://localhost:8080/health
curl -s -H "Authorization: Bearer lumynax-local-dev" http://localhost:8080/v1/models | jq '.data[0:3]'
```

**Test the chat endpoint:**

```bash
curl -s http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer lumynax-local-dev" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "lumynax-coder-deepseek-v2-lite-16b-gguf",
    "messages": [{"role":"user","content":"Print hello world in Rust."}]
  }' | jq -r '.choices[0].message.content'
```

**Test with web_search enabled:**

```bash
curl -s http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer lumynax-local-dev" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "lumynax-chat-hermes-3-llama31-8b-gguf",
    "enable_web_search": true,
    "messages": [{"role":"user","content":"What did Aotearoa New Zealand announce on AI policy this week? Cite sources."}]
  }' | jq -r '.choices[0].message.content'
```

---

## Path 2 — HPE Kubernetes / OpenShift / GreenLake

```bash
cd deployments/k8s/helm

# 1. Customize values.yaml — set ingress host, TLS issuer, api keys, routes,
#    and the list of model servers you want.
vim lumynax/values.yaml

# 2. Pre-stage HF token if any models are gated (rare)
kubectl create namespace lumynax
kubectl -n lumynax create secret generic hf-token --from-literal=token=$HF_TOKEN

# 3. Install
helm install -n lumynax lumynax ./lumynax \
  --set searxng.secret=$(openssl rand -hex 32) \
  --set-file gateway_config.apiKeysJson=./api-keys.prod.json \
  --set-file gateway_config.routesJson=./routes.prod.json

# 4. Verify
kubectl -n lumynax get pods
kubectl -n lumynax port-forward svc/lumynax-gateway 8080:8080
curl -s -H "Authorization: Bearer <your-key>" http://localhost:8080/v1/models
```

Each entry under `modelServers:` in `values.yaml` becomes its own Deployment + Service + PVC. The init container does `huggingface_hub.snapshot_download` to pull weights onto the PVC the first time it spins up. After that, restarts are fast — weights are cached on the volume.

### Scaling

- **Gateway**: stateless, set `gateway.replicas` to whatever your traffic needs. Behind an HPA driven by CPU or request rate.
- **Model servers**: each is single-replica by default (LLMs need lots of GPU per pod). For higher throughput, replicate behind the same Service; vLLM handles continuous batching natively.
- **SearXNG**: stateless, replicate freely.

### Storage

Each model PVC defaults to 30 GiB for 13B-class Q4 GGUF. Larger:
- 70B GGUF: 40-50 GiB
- 70B safetensors bf16: 150 GiB
- Frontier MoE Q4 (235B-480B): 130-300 GiB
- Frontier MoE bf16: 500GB-1TB

Use HPE GreenLake block storage with **ReadWriteMany** if you want multiple model-server replicas sharing one weight volume.

---

## Path 3 — Air-gapped bare metal

If the HPE environment has no outbound internet:

1. **Pre-pull container images** on a connected host:
   ```bash
   docker pull lumynax/gateway:0.2.0
   docker pull searxng/searxng:latest
   docker pull ghcr.io/ggerganov/llama.cpp:server
   docker pull python:3.11-slim
   docker pull curlimages/curl:8.10.1
   docker save -o lumynax-images.tar lumynax/gateway:0.2.0 searxng/searxng:latest \
     ghcr.io/ggerganov/llama.cpp:server python:3.11-slim curlimages/curl:8.10.1
   ```
   Transfer `lumynax-images.tar` to the air-gapped registry; `docker load` and re-tag for your internal registry.

2. **Pre-mirror weights** to internal storage with `lumynax download`:
   ```bash
   for m in lumynax-coder-deepseek-v2-lite-16b-gguf lumynax-chat-hermes-3-llama31-8b-gguf; do
     lumynax download "$m" --out-dir /share/lumynax-models/"$m"
   done
   rsync -av /share/lumynax-models air-gapped:/share/
   ```

3. **Update the gateway's `registry.json`** to a static copy (no live HF fetch). Set `gateway_config.registryUrl` to a file path served by an internal HTTP cache, or bake the registry into the ConfigMap directly via `--set-file gateway_config.registry=registry.json` (you'll need a small chart-template tweak to consume that).

4. **Configure SearXNG engines** to your internal search index (Solr/Elasticsearch wrapper) instead of external engines — edit `web-search/settings.yml`.

---

## Web search — sovereignty notes

SearXNG aggregates search engines server-side. By default it queries DuckDuckGo, Bing, Brave, Wikipedia, GitHub, arXiv, Google. Each query goes through your SearXNG container, then out to those engines. **End-user IPs are never exposed to the upstream engines** — they only see SearXNG's IP.

If "fully sovereign" means **no outbound traffic at all**:
- Run an internal crawler (Yacy, Kagi-on-prem, or a custom Solr index) and configure SearXNG to query only that.
- Or disable `web_search` per-tenant via `api-keys.json` (omit the policy that enables it).

The gateway's `web_search` tool is **off by default** — clients have to set `"enable_web_search": true` in the request body, and the model has to support tools, and the tenant's policy has to permit it.

---

## Per-tenant API keys & policies

`api-keys.json` shape:

```json
{
  "sk-<random>": {
    "tenant": "engineering",
    "jurisdiction": "NZ",
    "policies": ["nz-personal-sovereignty"],
    "rate_limit": 1000,
    "min_sovereignty_tier": 3
  }
}
```

Fields:
- `tenant`: organizational unit shown in audit log
- `jurisdiction`: requests use this to filter models — only models whose `residency` includes the jurisdiction pass the gate
- `min_sovereignty_tier`: drop any model below this tier (1 = remote frontier, 5 = NZ-resident local)
- `policies`: free-form tags consumed by `policy_check()` in `gateway/app.py` — extend as you wish

Rotate keys: edit the ConfigMap (or file) and `kubectl rollout restart deploy/lumynax-gateway`.

---

## Observability

- **Audit log**: `GATEWAY_AUDIT_LOG` — JSONL, hash-chained. Tail or ship to your SIEM.
- **Health**: `GET /health` returns `{ok:true, models:N, routes:M}`
- **Metrics**: not enabled by default — add `prometheus-fastapi-instrumentator` to `gateway/requirements.txt` and instrument if you want `/metrics`.

---

## Hardware sizing cheat sheet (NVIDIA, llama.cpp Q4_K_M)

| Model | GPU | VRAM | Notes |
|---|---|---|---|
| 7B / 8B (Hermes-3, CodeQwen, Qwen2.5-7B-1M) | A10 / L4 / RTX 4090 | 8-12 GB | CPU also fine, slower |
| 13-16B (Yi-Coder, Mistral, Phi-4, DeepSeek-Coder-V2-Lite) | L40S / A40 / 3090 | 12-20 GB | |
| 30-34B (Yi-1.5-34B, Qwen2.5-Coder-32B, QwQ-32B, LLaVA-Next-34B) | L40S / A100-40 | 24-40 GB | |
| 70B (CodeLlama, R1-Distill-Llama, Qwen2.5-72B) | A100-80 / H100 | 48-80 GB | |
| Frontier MoE Q4 (Qwen3-235B, MiniMax-M2, GLM-4.6-355B) | 2-4× A100-80 / H100 | 200-400 GB | tensor-parallel |
| 671B MoE Q4 (DeepSeek-Prover-V2, DeepSeek-V3) | 4-8× H100 | 500-700 GB | high-end serving only |

For HPE GreenLake AI Compute: 8x H100 nodes serve any single model in the family. The 7B-30B tier runs comfortably on a 1× L40S node.
