# Runbook · Incident response

## Severity 1 — key compromise

> *Customer reports their key appeared on GitHub / Pastebin / phishing log.*

```bash
# 1. Invalidate + rotate (5 sec)
bash scripts/07-rotate-key.sh "<customer-name>"

# 2. Audit how the leaked key was used in the last 30 days
jq -r 'select(.tenant == "<customer-slug>") | "\(.ts) \(.event) \(.model // "-")"' \
  state/audit/audit.log | head -200

# 3. If you see abnormal usage (>10× their baseline, off-hours, model fishing):
#    - export those records and send to the customer
#    - check if any models were used to retrieve sensitive data via web_search
jq 'select(.tenant == "<customer-slug>" and .event == "tool_web_search") | .query' \
  state/audit/audit.log

# 4. Send the new onboarding pack to the customer via encrypted channel
cat state/onboarding/<customer-slug>.md
```

## Severity 2 — gateway 5xx

```bash
docker compose -f compose/docker-compose.yml ps                    # which container is unhealthy?
docker compose -f compose/docker-compose.yml logs --tail 200 gateway

# Common causes
#  - api-keys.json or routes.json malformed JSON     → fix and restart gateway
#  - searxng down                                     → docker compose restart searxng
#  - backend model server OOM                         → see Sev 3 below
#  - audit log volume full                            → rotate state/audit/audit.log
```

Recovery:
```bash
docker compose -f compose/docker-compose.yml restart gateway
# Or full restart:
docker compose -f compose/docker-compose.yml down && bash scripts/04-serve.sh
```

## Severity 3 — model OOM / hangs

```bash
nvidia-smi              # is a GPU pinned at 100%?
docker compose -f compose/docker-compose.yml logs --tail 500 llama-<slug>
```

Mitigations:
1. Reduce context: edit compose entry, lower `-c 16384` → `-c 8192`, restart that service only.
2. Reduce `n-gpu-layers`: drop `-ngl -1` to a finite number to keep some layers on CPU.
3. Switch to a smaller model. Run `bash scripts/08-add-model.sh lumynax-coder-yi-coder-9b-gguf` (smaller coder) and update any routing.
4. If a customer's traffic alone is OOM'ing a model, lower their `rate_limit` in `api-keys.json` and restart gateway.

## Severity 4 — abusive traffic / cost spike

```bash
# 1. Identify the culprit
jq -r 'select(.event == "response") | .tenant' state/audit/audit.log | sort | uniq -c | sort -rn | head

# 2. Throttle them immediately
python3 -c "
import json, pathlib
p = pathlib.Path('env/api-keys.json'); d = json.loads(p.read_text())
for k, v in d.items():
    if v.get('tenant') == '<abusing-tenant>':
        v['rate_limit'] = 10  # very low until investigation
p.write_text(json.dumps(d, indent=2))
"
docker compose -f compose/docker-compose.yml restart gateway
```

## Severity 5 — model returns wrong/harmful output to a customer

> *Customer reports model said something it shouldn't have — leak, hallucination, NSFW.*

```bash
# 1. Pull the conversation from the audit log if possible (only metadata is logged by default)
jq 'select(.request_id == "<id>")' state/audit/audit.log

# 2. If the customer wants a model-level policy change:
#    - add the misbehaving model to that tenant's deny-list (extend gateway/app.py policy_check)
#    - OR raise their min_sovereignty_tier to push them onto stricter models
#    - OR add an `allow_models` allowlist to their api-key entry

# 3. File a model-card update on the underlying HF repo if you've identified a systematic issue
```

## Communication templates

```
# Status-page update (key compromise):
"[<time>] We detected a credential exposure affecting one tenant. The key was invalidated within 5 minutes. No other tenants are impacted. The affected customer has been issued a new key. Full timeline in the post-mortem."

# Status-page update (5xx incident):
"[<time>] Some requests to api.lumynax.com returned 503 between <start> and <end>. Cause: <backend-restart|cert-renewal|OOM>. Mitigation: <action>. The audit log shows N affected requests across M tenants."
```
