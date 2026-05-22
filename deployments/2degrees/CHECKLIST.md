# Day-0 checklist (do this before booting anything)

- [ ] **Compute reserved** — at least 1× H100 (or A100-80) for training; same for serving 70B-class models
- [ ] **Hostname + DNS** decided if you're exposing publicly (e.g. `api.lumynax.com` → this host)
- [ ] **TLS certificate** plan (Let's Encrypt via nginx-ingress, or upstream load balancer terminating)
- [ ] **HF token** with read access (you may need write if pushing fine-tunes)
- [ ] **Disk free** — `df -h` shows ≥400 GB free on the volume mounted at the working dir
- [ ] **Docker installed**, daemon running, GPU runtime configured (`docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi` works)
- [ ] **Outbound HTTPS allowed** to `huggingface.co`, `ghcr.io`, plus DDG/Bing/Wikipedia if SearXNG will reach them
- [ ] **Inbound port** 8080 open from your customers' networks (or behind ingress)

# Day-1 happy path

Walk these in order. Each is ≤5 min unless flagged otherwise.

- [ ] `bash scripts/00-preflight.sh` → confirm OK on every check
- [ ] `bash scripts/01-bootstrap.sh` → secrets written under `state/`
- [ ] Pick which models to serve initially. Recommended starter set:
   - `lumynax-chat-hermes-3-llama31-8b-gguf` (general chat, ~5 GB, tools)
   - `lumynax-coder-deepseek-v2-lite-16b-gguf` (code, ~10 GB, MoE 16B/2.4B)
   - `lumynax-embed-bge-m3` (embeddings, ~2 GB)
- [ ] `bash scripts/02-pull-weights.sh <slug1> <slug2> <slug3>` ← **30–60 min** depending on bandwidth
- [ ] `bash scripts/04-serve.sh` → wait for "stack healthy" message
- [ ] `curl http://localhost:8080/health` → `{"ok": true, "models": N, "routes": M}`
- [ ] `bash scripts/05-issue-key.sh "<customer>"` for each customer you're onboarding
- [ ] Mail each customer their `state/onboarding-<customer>.md`

# Day-2+ operations

- [ ] **Monitoring**: `bash scripts/06-monitor.sh` runs a live tail; consider running it in a tmux session you check daily
- [ ] **Audit**: `tail -f state/audit.log` is a hash-chained ledger of every request — feed to your SIEM
- [ ] **Cost tracking**: see `runbooks/06-cost-tracking.md` — `state/usage-by-customer.csv` is updated nightly
- [ ] **Key rotation policy**: every 90 days or on suspicion of compromise (`07-rotate-key.sh`)

# Optional but recommended

- [ ] **Fine-tune** your own model on customer-relevant data — `bash scripts/03-train.sh lora` after editing `../../training/lumynax-nz/datasets/sources.yaml` for your corpus
- [ ] **Add models** as customers ask for them — `bash scripts/08-add-model.sh <slug>` (no downtime)
- [ ] **Set up a status page** — `runbooks/05-incident.md` includes templates
- [ ] **Connect Grafana** — point at `state/audit.log` and the gateway's `/health`; dashboard JSON in `monitoring/`
