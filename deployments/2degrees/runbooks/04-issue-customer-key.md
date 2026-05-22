# Runbook · Issue an API key to a customer

## Quick (default policy)

```bash
bash scripts/05-issue-key.sh "Acme Corp"
```

Defaults: NZ jurisdiction, min sovereignty tier null (any model), 1000 req/min, policy `nz-personal-sovereignty`.

## Custom policy

```bash
bash scripts/05-issue-key.sh "Acme Corp" \
  --jurisdiction NZ \
  --min-tier 3 \
  --rate-limit 500 \
  --policies "nz-personal-sovereignty,allow-tools"
```

## What the customer gets

`state/onboarding/<customer-slug>.md` — a complete starter pack:
- Endpoint URL + API key
- curl examples for `chat`, `route`, `web_search`
- Python OpenAI SDK snippet
- OpenCode + Continue configs
- Their policy summary (jurisdiction, tier, rate)

**Send via an encrypted channel** (Signal / PGP-encrypted email / shared password manager). The pack contains a live secret.

## What they can do once they have it

```python
from openai import OpenAI
client = OpenAI(base_url="https://api.lumynax.com/v1", api_key="lx-acme-corp-...")
# Drop-in OpenAI SDK — every standard method works
```

## Limits to set per-tenant

| Field | When to set | Example |
| --- | --- | --- |
| `jurisdiction` | Customer is in / serves a specific country | `NZ`, `AU`, `global` |
| `min_sovereignty_tier` | Customer policy says "no remote frontier models" | `3` (drops Qwen3-235B, MiniMax-M2, GLM-4.6) |
| `rate_limit` | Per-customer ceiling, requests/minute | `500` for small, `5000` for enterprise |
| `policies` | Custom policy tags consumed by gateway/app.py | `["allow-training"]` to permit `for_training` requests |

## Track usage

The audit log (`state/audit/audit.log`) records every request with `tenant`, `model`, `event`. To produce a daily usage report:

```bash
jq -r 'select(.event == "response") | "\(.ts) \(.tenant) \(.model)"' state/audit/audit.log \
  | awk -F' ' '{print substr($1,1,10), $2}' | sort | uniq -c | sort -rn
```

See `runbooks/06-cost-tracking.md` for billing-grade aggregation.

## Revoke

```bash
bash scripts/07-rotate-key.sh "Acme Corp"
# old key invalidated; new pack at state/onboarding/acme-corp.md
```

To revoke without re-issue: edit `env/api-keys.json`, delete the entry, `docker compose restart gateway`.
