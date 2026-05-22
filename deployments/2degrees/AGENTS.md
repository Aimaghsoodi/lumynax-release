# Instructions for AI coding assistants (Claude Code, Codex, Cursor, Aider)

You are helping deploy LumynaX in the **2degrees** environment. The user has GPU compute and wants to (a) optionally fine-tune a model and (b) serve one or more LumynaX models as an OpenAI-compatible API to real customers.

## Your operating rules

1. **Read [`CHECKLIST.md`](CHECKLIST.md) first.** It's the canonical task ordering.
2. **Always run scripts in numeric order.** `00 → 01 → 02 → 04 → 05` is the happy path. Skip numbers only when the runbook tells you to.
3. **Every script is idempotent.** Re-running is safe. If a step fails, fix the cause and re-run that step — don't skip ahead.
4. **Never commit secrets.** `env/api-keys.json`, `env/.env`, anything under `state/` is gitignored. If you see a secret in chat, advise the user to rotate it.
5. **Capture state in `state/ops.log`.** Each script appends. Read it before making decisions.
6. **The user's HF token is sensitive.** Treat it like a production credential. If the user pastes it inline, advise them to rotate after the session.
7. **Sovereignty matters.** Jurisdiction defaults to `NZ`. Don't relax that without an explicit instruction from the user.
8. **If GPU memory is insufficient for a chosen model, suggest a smaller one from the same tier** rather than letting OOM crash a serve attempt.
9. **Don't invent commands.** Every operation is wrapped in a script under `scripts/`. If a needed operation doesn't have a script, write one in the same numbered convention and add it to `CHECKLIST.md`.

## Standard task flow

When the user asks for any of these, here's what to do:

### "Deploy from scratch"
```bash
bash scripts/00-preflight.sh
bash scripts/01-bootstrap.sh
bash scripts/02-pull-weights.sh <one-or-more-model-slugs>
bash scripts/04-serve.sh
bash scripts/05-issue-key.sh "<customer-name>"
```
Stop after each step; review the printed output before continuing. Show the user the contents of `state/onboarding-<customer>.md` at the end.

### "Train LumynaX-NZ"
```bash
bash scripts/03-train.sh lora      # or 'sft' on 8x H100
# Wait. When done:
bash scripts/04-serve.sh           # picks up the new model automatically
```
Estimated wall time on 1× H100: **2–3 hours** for LoRA, **6–12 hours** for full SFT.

### "Add a model to the running stack"
```bash
bash scripts/08-add-model.sh <slug>
# Verify with:
curl -s -H "Authorization: Bearer $(cat state/admin-key)" http://localhost:8080/v1/models | jq '.data[] | .id' | grep <slug>
```

### "A customer needs an API key"
```bash
bash scripts/05-issue-key.sh "<customer-name>" --jurisdiction NZ --min-tier 3 --rate-limit 500
# Then send them state/onboarding-<customer>.md
```

### "Rotate a leaked key"
```bash
bash scripts/07-rotate-key.sh "<customer-name>"
# The script invalidates the old key and emits a new starter pack.
```

### "Something's wrong / model is misbehaving"
Open `runbooks/05-incident.md`. Common patterns:
- **Model returns garbage** → check `state/ops.log` for OOM; reduce `--n-gpu-layers` or pick smaller model
- **5xx from gateway** → `docker compose logs gateway` and check `state/ops.log` for the auth/policy chain
- **Customer key compromised** → `07-rotate-key.sh` immediately; check audit log for misuse

## Safety guardrails

- **Never disable auth.** The gateway requires Bearer tokens. Don't `--no-auth` anything.
- **Never expose the gateway port without TLS in production.** Use the nginx config in `env/nginx.conf` or your existing ingress.
- **Never reuse an admin key as a customer key.** They have different policy scopes.
- **Never push `state/` to git.** It contains keys and the audit log.

## When you're stuck

The full LumynaX docs are one directory up: `../DEPLOYMENT.md`, `../INTEGRATIONS.md`, the monorepo's root `README.md`. The repo source-of-truth: <https://github.com/Aimaghsoodi/lumynax-release>.

If a script genuinely fails for environmental reasons (e.g. host without GPU, no Docker daemon), tell the user honestly and propose a fallback (CPU-only serving for small models, etc.) rather than papering over with workarounds.
