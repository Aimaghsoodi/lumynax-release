# Finalize — what's done, what's left, what you do next

## ✅ Done (this commit and prior)

| Layer | Status |
| --- | --- |
| 98 models on `huggingface.co/AbteeXAILab` — weights + scaffold + NZ branding | ✅ |
| 98 GitHub repos under `github.com/aimaghsoodi/lumynax-*` | ✅ |
| Monorepo `Aimaghsoodi/lumynax-release` (every product, deployment, tool) | ✅ |
| 6 HF Collections grouping the family by tier | ✅ |
| 3 Spaces (sovereigncode-demo, marama-route-demo, lumynax-live-demo) | ✅ live, gateway-aware |
| `abteex.com` + `lumynax.com` static landing pages | ✅ built and pushed; GH Pages enabled; awaiting DNS |
| Gateway (FastAPI · auth · policy · audit · web_search) | ✅ **10/10 pytest passing** |
| SearXNG self-hosted web-search | ✅ wired to gateway |
| Docker Compose + Helm chart | ✅ |
| `lumynax-cli` v0.3.0 (run / route / serve / opencode / continue / vllm / lm-studio / ollama) | ✅ wheel builds clean |
| `lumynax-gateway` ops CLI (up / down / status / logs / add-model / helm-*) | ✅ |
| `lumynax-mcp` MCP server for Claude Desktop / Cursor / Zed | ✅ wheel builds clean |
| GitHub Actions: tests, gateway container, PyPI publish, nightly drift | ✅ 4 workflows |
| Architecture SVG + scannable README | ✅ |
| HumanEval + MMLU runners; shared client; collate.py; results.md table | ✅ |
| LumynaX-NZ training scaffold (QLoRA + SFT, datasets/sources.yaml, eval.py, export.sh) | ✅ |
| Smoke test (`scripts/e2e_smoke.sh`) | ✅ |

## ⏳ What requires your action (cannot be automated from here)

### 1. PyPI trusted publishing (one-time, ~5 min)

So `pip install lumynax` and `pip install lumynax-mcp` work for everyone:

1. Visit https://pypi.org/manage/account/publishing/
2. **Add a new pending publisher** for project `lumynax`:
   - PyPI Project Name: `lumynax`
   - Owner: `Aimaghsoodi`
   - Repository name: `lumynax-release`
   - Workflow name: `publish-pypi.yml`
   - Environment name: *(leave blank)*
3. Add a second pending publisher for project `lumynax-mcp` (same settings, project name `lumynax-mcp`).
4. Re-run the GH Actions workflow: `gh workflow run publish-pypi.yml --repo Aimaghsoodi/lumynax-release`

### 2. DNS for `lumynax.com` + `abteex.com` (~5 min per domain)

For each domain at your registrar (Cloudflare / Namecheap / etc):

- **A records** (apex domain) → `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`
- Or **ALIAS / ANAME** → `aimaghsoodi.github.io`

HTTPS auto-issues via Let's Encrypt within ~10 min after DNS propagates. The CNAME files are already in both repos.

### 3. Rotate the HF token (~1 min, overdue)

`hf_mSe…` has been in chat history for many turns.

```bash
# 1. Visit https://huggingface.co/settings/tokens — delete the old one, create a new one
# 2. Update any env or secret store that uses it
gh secret set HF_TOKEN --repo Aimaghsoodi/lumynax-release --body 'hf_NEW_TOKEN'
```

### 4. Smoke test on a real Docker host (~5 min)

```bash
git clone https://github.com/Aimaghsoodi/lumynax-release
cd lumynax-release
bash scripts/e2e_smoke.sh           # 30 s — validates gateway, auth, routing, web_search
bash scripts/e2e_smoke.sh --gpu     # adds a real chat completion (needs GPU + ~10 GB disk for a small model)
```

### 5. Claude Desktop / Cursor / Zed wiring (~2 min, once `lumynax-mcp` is on PyPI)

```bash
pip install lumynax-mcp
```

Edit your MCP client's config (paths shown for Claude Desktop on macOS):

```json
// ~/Library/Application Support/Claude/claude_desktop_config.json
{
  "mcpServers": {
    "lumynax": {
      "command": "lumynax-mcp",
      "env": {
        "LUMYNAX_GATEWAY_URL": "http://localhost:8080/v1",
        "LUMYNAX_GATEWAY_KEY": "lumynax-local-dev"
      }
    }
  }
}
```

Restart the client. Claude (or Cursor / Zed) now sees the 98-model registry as callable tools: `lumynax_route`, `lumynax_chat`, `lumynax_list`, `lumynax_info`, `lumynax_web_search`.

### 6. The flagship — train LumynaX-NZ-3B (~3 hours · ~$30)

```bash
# 1. Rent a single H100 from Lambda / RunPod / CoreWeave (~$3/hr)
ssh root@<rented-host>
git clone https://github.com/Aimaghsoodi/lumynax-release
cd lumynax-release/training/lumynax-nz
pip install -r requirements.txt

# 2. Prepare data (NLLB mi↔en + your fetched corpora; see datasets/sources.yaml)
python datasets/prepare.py --out data/

# 3. Train
bash train.sh lora        # ~2-3h on a single H100, ~$8 if you grab a spot instance

# 4. Evaluate
python eval.py --model output/lumynax-nz-3b-lora

# 5. Convert to GGUF and push to HF (replaces the placeholder there)
bash export.sh
```

After this, the registry's `lumynax-nz-3b` is a **real model you trained**, not a placeholder. That's the moment LumynaX becomes "a lab," not "a curated mirror."

### 7. Benchmark run (~half a day on a rented GPU)

Once you have a server with disk and a GPU:

```bash
cd lumynax-release
docker compose -f deployments/docker-compose.yml up -d
# Wait for at least one llama-* model server to finish weight download
cd evals
make bench   # iterates HumanEval + MMLU across coder/chat tiers
```

The `results.md` table populates with **LumynaX vs upstream** deltas. If anything is more than 2pts below upstream, that's a real bug — file it.

---

## What "perfect" looks like after the 7 items above

- `pip install lumynax` works from anywhere — discovers, downloads, runs, routes, serves any of the 98 models
- `pip install lumynax-mcp` + 4 lines of config wires LumynaX into Claude Desktop / Cursor / Zed
- `lumynax.com` and `abteex.com` resolve to the brand sites with HTTPS
- `evals/results.md` shows LumynaX numbers ± 2pts of upstream — proof the gateway is faithful
- `AbteeXAILab/lumynax-nz-3b` is a **real** NZ-fine-tuned model with provenance, eval scores, GGUF + safetensors

The codebase is *done*. The 7 actions above are deployment-side and take maybe 2–4 hours total of your time (plus 3 hours of unattended H100 for the training).

Made in Aotearoa New Zealand · AbteeX AI Labs · [abteex.com](https://abteex.com) · [lumynax.com](https://lumynax.com)

*Ko te mārama te tūāpapa.*
