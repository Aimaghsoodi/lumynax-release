# 2degrees Deployment — train, serve, share LumynaX

Self-contained kit to take you from **a fresh login on the compute host** to **issuing API keys to real users in under 90 minutes**.

> Project codename: **2degrees**. Folder works on any Linux GPU host — bare metal, OpenShift node, or a rented box. No vendor-specific code, no external dependencies beyond Docker + Hugging Face access.

## Layout

```
deployments/2degrees/
├── README.md              ← you are here
├── AGENTS.md              ← instructions for Claude Code / Codex assistants
├── CHECKLIST.md           ← day-0 preflight + day-1 operations list
├── env/
│   ├── .env.example
│   ├── api-keys.example.json
│   └── routes.example.json
├── scripts/               ← numbered, idempotent, all bash
│   ├── 00-preflight.sh    ← hardware + software checks
│   ├── 01-bootstrap.sh    ← directories, configs, secrets
│   ├── 02-pull-weights.sh ← fetch chosen models from HF
│   ├── 03-train.sh        ← kick off LumynaX-NZ (or any model) training
│   ├── 04-serve.sh        ← bring up gateway + SearXNG + model servers
│   ├── 05-issue-key.sh    ← mint an API key for a customer + emit a starter pack
│   ├── 06-monitor.sh      ← health, audit tail, throughput
│   ├── 07-rotate-key.sh   ← rotate a customer's key
│   ├── 08-add-model.sh    ← add a new model to the running stack
│   └── 99-teardown.sh
├── compose/
│   └── docker-compose.yml ← overlay for this environment
├── helm/
│   └── values.yaml        ← if you're on K8s
├── runbooks/
│   ├── 01-day-zero.md
│   ├── 02-train-new-model.md
│   ├── 03-add-model-to-api.md
│   ├── 04-issue-customer-key.md
│   ├── 05-incident.md
│   └── 06-cost-tracking.md
└── monitoring/
    └── grafana-dashboard.json
```

## 90-minute happy path (first day)

```bash
# Log in to the compute host, then:
git clone https://github.com/Aimaghsoodi/lumynax-release
cd lumynax-release/deployments/2degrees

bash scripts/00-preflight.sh         # 1 min — verify GPU + Docker + disk + network
bash scripts/01-bootstrap.sh         # 2 min — generate secrets, write configs
bash scripts/02-pull-weights.sh \    # 30-60 min depending on bandwidth
     lumynax-chat-hermes-3-llama31-8b-gguf \
     lumynax-coder-deepseek-v2-lite-16b-gguf
bash scripts/04-serve.sh             # 5 min — start gateway + searxng + 2 model servers
bash scripts/05-issue-key.sh "first-customer" --rate-limit 1000   # 30 s
bash scripts/06-monitor.sh           # tail logs + show throughput
```

After `05-issue-key.sh`, you have a **complete onboarding pack** for the customer (key, curl example, OpenAI-SDK snippet, OpenCode config, Continue config). Mail it to them.

## What you can actually do from here

| Goal | Command |
| --- | --- |
| **Serve any of the 98 published LumynaX models as an OpenAI-compatible API** | `02-pull-weights.sh <slug>` → `04-serve.sh` → `05-issue-key.sh <customer>` |
| **Train a new model on your data** | `03-train.sh` |
| **Add a model to a running stack without downtime** | `08-add-model.sh <slug>` |
| **Issue per-customer API keys with jurisdiction + sovereignty policies** | `05-issue-key.sh <customer> --jurisdiction NZ --min-tier 3 --rate-limit 500` |
| **Rotate a leaked key** | `07-rotate-key.sh <customer>` |
| **Track usage + cost per customer** | see `runbooks/06-cost-tracking.md` |
| **Respond to an incident (key compromise / model misbehaviour)** | `runbooks/05-incident.md` |

## Architecture (what you're standing up)

```
customers ──HTTPS──► nginx (TLS) ──► gateway:8080 ──┬─► llama-server (Hermes-3)
   (OpenCode,           ▲                            ├─► llama-server (DeepSeek-Coder)
    Continue,           │                            ├─► vllm-server (Pixtral / InternVL3)
    Cursor, …)    per-customer                      ├─► searxng (private web search)
                  API key + policy                   └─► [more on demand via 08-add-model]
                  + hash-chained audit
```

## Pre-requisites

- **Linux GPU host** with NVIDIA driver + CUDA (any vendor — bare metal, cloud, on-prem)
- **Docker 24+** with `--gpus all` support
- **400-1000 GB free disk** for model weights (depends which models you pick)
- **HF token** with read access (rotate if it's been leaked)
- **Open ports**: 8080 (gateway), 443 (if TLS terminating yourself)
- **Optional**: a public DNS name for the API endpoint

## Cost expectations

Per H100 on Lambda / RunPod / CoreWeave / similar:
- **Training** LumynaX-NZ-3B LoRA: ~$8-30 single-shot
- **Serving** a 7B-30B model: ~$2-4/hour while up
- **Serving** a 70B model: ~$4-8/hour
- **Serving** a 670B MoE (Prover-V2): needs 8× H100, ~$25-50/hour

For most customer-facing usage, a single H100 + a curated 3-5 models covers it.

## Need help mid-deployment

`AGENTS.md` in this folder is a system prompt for Claude Code / Codex. Open a session, point it at this folder, and it'll drive everything:

```bash
# At the deployment host, with the cloned monorepo, start your AI assistant
# pointed at this directory. It will read AGENTS.md and CHECKLIST.md and
# walk you through every step, fixing problems as they arise.
```

Made in Aotearoa New Zealand · AbteeX AI Labs · [abteex.com](https://abteex.com) · [lumynax.com](https://lumynax.com)
