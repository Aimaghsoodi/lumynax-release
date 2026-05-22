# Runbook · Cost tracking

The audit log is the source of truth. Every request has `tenant`, `model`, `event`, `ts`. Add a nightly cron that aggregates it into `state/usage-by-customer.csv` for billing.

## Token estimates per request

For models, count `prompt_tokens + completion_tokens` from the upstream backend response. The gateway proxies these unchanged. To capture them, set the gateway env var `GATEWAY_AUDIT_USAGE=1` (already supported — the gateway will emit `usage` field in the response audit record when set).

## Nightly aggregation cron

```bash
# /etc/cron.daily/lumynax-usage
#!/bin/bash
LOG=/path/to/lumynax-release/deployments/2degrees/state/audit/audit.log
OUT=/path/to/lumynax-release/deployments/2degrees/state/usage-by-customer.csv

# CSV: date, tenant, model, n_requests, total_tokens
jq -r 'select(.event == "response") | [
    (.ts | sub("T.*"; "")),
    .tenant // "-",
    .model // "-",
    (.usage.prompt_tokens + .usage.completion_tokens // 0)
] | @csv' "$LOG" \
  | awk -F, '{key=$1","$2","$3; req[key]++; tok[key]+=$4} END{for(k in req) print k","req[k]","tok[k]}' \
  | sort > "$OUT"
```

## Per-customer monthly invoice

```bash
# Tokens consumed by tenant 'acme-corp' in May 2026
awk -F, '$1 ~ /^2026-05/ && $2 == "acme-corp" {tot+=$5} END{print "tokens:", tot+0}' \
  state/usage-by-customer.csv

# Or compute cost at, say, $0.0005/1k tokens
awk -F, '$1 ~ /^2026-05/ && $2 == "acme-corp" {tot+=$5} END{printf "USD: %.2f\n", tot/1000*0.0005}' \
  state/usage-by-customer.csv
```

## Cost-per-model on your side

Self-hosted means most cost is fixed (GPU hours). Add a `cost_per_hour` column to a CSV you maintain:

```csv
model,gpu_class,cost_per_hour_usd
lumynax-chat-hermes-3-llama31-8b-gguf,A10,0.60
lumynax-coder-deepseek-v2-lite-16b-gguf,L40S,1.20
lumynax-frontier-qwen25-72b-instruct-gguf,H100,3.20
```

Multiply by uptime per day (gateway audit log shows when each backend was queried). The gross margin = (token-based customer billing) − (GPU hours × cost) per model.

## Quick reports

```bash
# Top 10 tenants by requests in the last 7 days
jq -r 'select(.event == "response" and (.ts | sub("T.*"; "") >= "'$(date -u -d '7 days ago' +%F)'")) | .tenant' \
  state/audit/audit.log | sort | uniq -c | sort -rn | head

# Top 10 models by requests in the last 7 days
jq -r 'select(.event == "response" and (.ts | sub("T.*"; "") >= "'$(date -u -d '7 days ago' +%F)'")) | .model' \
  state/audit/audit.log | sort | uniq -c | sort -rn | head

# Requests denied (policy gates triggered)
jq -r 'select(.event == "policy_deny") | "\(.ts) \(.tenant) \(.model) \(.reason)"' \
  state/audit/audit.log | tail -50
```
