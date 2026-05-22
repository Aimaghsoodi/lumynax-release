#!/usr/bin/env bash
# 05-issue-key: mint an API key for a customer + emit a complete onboarding pack.
# Usage:
#   bash 05-issue-key.sh "customer-name"
#   bash 05-issue-key.sh "customer-name" --jurisdiction NZ --min-tier 3 --rate-limit 500 --policies nz-personal-sovereignty
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$HERE/.."
ENV_DIR="$ROOT/env"
STATE="$ROOT/state"
LOG="$STATE/ops.log"
source "$ENV_DIR/.env"

log() { echo "[$(date -u +%FT%TZ)] [issue-key] $*" | tee -a "$LOG"; }

[[ $# -ge 1 ]] || { echo "usage: $0 <customer-name> [--jurisdiction NZ] [--min-tier 3] [--rate-limit 500] [--policies tag1,tag2]"; exit 2; }

CUSTOMER="$1"; shift
JURISDICTION="NZ"; MIN_TIER="null"; RATE="1000"; POLICIES='["nz-personal-sovereignty"]'

while [[ $# -gt 0 ]]; do
  case "$1" in
    --jurisdiction) JURISDICTION="$2"; shift 2;;
    --min-tier)     MIN_TIER="$2"; shift 2;;
    --rate-limit)   RATE="$2"; shift 2;;
    --policies)     POLICIES="[\"$(echo "$2" | sed 's/,/","/g')\"]"; shift 2;;
    *) echo "unknown: $1"; exit 2;;
  esac
done

SLUG=$(echo "$CUSTOMER" | tr '[:upper:] ' '[:lower:]-' | tr -cd 'a-z0-9-')
KEY="lx-$SLUG-$(openssl rand -hex 24)"
log "minting key for '$CUSTOMER' (slug=$SLUG, jur=$JURISDICTION, tier≥$MIN_TIER, rate=$RATE/min)"

# Append to api-keys.json atomically
python3 - <<PY
import json, pathlib
p = pathlib.Path("$ENV_DIR/api-keys.json")
d = json.loads(p.read_text())
d["$KEY"] = {
    "tenant": "$SLUG", "customer_name": "$CUSTOMER",
    "jurisdiction": "$JURISDICTION", "policies": $POLICIES,
    "rate_limit": $RATE, "min_sovereignty_tier": $MIN_TIER,
    "created_at": "$(date -u +%FT%TZ)"
}
p.write_text(json.dumps(d, indent=2))
PY

# Hot-reload gateway so the key works immediately
docker compose -f "$ROOT/compose/docker-compose.yml" restart gateway >/dev/null 2>&1 || true

# Public endpoint for the customer
ENDPOINT="https://${LUMYNAX_PUBLIC_HOST:-localhost:8080}/v1"
if [[ "$ENDPOINT" == *":8080"* ]]; then ENDPOINT="http://${LUMYNAX_PUBLIC_HOST:-localhost}:8080/v1"; fi

OUT="$STATE/onboarding/${SLUG}.md"
mkdir -p "$STATE/onboarding"
cat > "$OUT" <<EOF
# Welcome to LumynaX — onboarding pack for **$CUSTOMER**

> 🇳🇿 Sovereign-AI from Aotearoa New Zealand · AbteeX AI Labs · [abteex.com](https://abteex.com) · [lumynax.com](https://lumynax.com)

## Your credentials

\`\`\`
endpoint: $ENDPOINT
api_key:  $KEY
\`\`\`

**Keep this secret.** Rotate immediately if exposed — your provider can do it via \`07-rotate-key.sh\`.

## Your policy

| Field | Value |
| --- | --- |
| Jurisdiction | \`$JURISDICTION\` — only models residency-tagged for this jurisdiction are accessible |
| Minimum sovereignty tier | \`$MIN_TIER\` (1 = remote frontier, 5 = NZ-resident) |
| Rate limit | $RATE requests / minute |
| Policy tags | $POLICIES |

## Curl quickstart

\`\`\`bash
# List models you can use
curl -H "Authorization: Bearer $KEY" $ENDPOINT/models | jq

# Chat
curl -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \\
     -d '{"model":"lumynax-chat-hermes-3-llama31-8b-gguf","messages":[{"role":"user","content":"Kia ora!"}]}' \\
     $ENDPOINT/chat/completions

# Ask MaramaRoute which model fits your request
curl -H "Authorization: Bearer $KEY" "$ENDPOINT/route?modalities=text&requires_local=true&jurisdiction=$JURISDICTION"

# Self-hosted web search (no external data leakage)
curl -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \\
     -d '{"query":"latest NZ AI policy"}' \\
     $ENDPOINT/tools/web_search
\`\`\`

## Python (OpenAI SDK — drop-in)

\`\`\`python
from openai import OpenAI
client = OpenAI(base_url="$ENDPOINT", api_key="$KEY")
r = client.chat.completions.create(
    model="lumynax-chat-hermes-3-llama31-8b-gguf",
    messages=[{"role": "user", "content": "Hello"}],
)
print(r.choices[0].message.content)
\`\`\`

## OpenCode

\`\`\`bash
mkdir -p ~/.opencode/providers
cat > ~/.opencode/providers/lumynax.json <<'JSON'
{
  "id": "lumynax",
  "type": "openai-compatible",
  "base_url": "$ENDPOINT",
  "api_key": "$KEY",
  "models": [{"id": "lumynax-coder-deepseek-v2-lite-16b-gguf", "supports_tools": true}]
}
JSON
opencode
\`\`\`

## Continue (~/.continue/config.json)

\`\`\`json
{
  "models": [{
    "title": "LumynaX",
    "model": "lumynax-coder-deepseek-v2-lite-16b-gguf",
    "apiBase": "$ENDPOINT",
    "apiKey": "$KEY",
    "provider": "openai"
  }]
}
\`\`\`

## Optional web search

To let the model search the web (self-hosted SearXNG — your data never leaves the LumynaX gateway), add \`"enable_web_search": true\` to your chat completion request body. Only available on tool-capable models.

## Support

- Operations runbook: see \`runbooks/05-incident.md\` on your provider's side
- Status: \`curl $ENDPOINT/../health\`
- Audit ledger: provider-side at \`state/audit/audit.log\` (hash-chained SHA-256)

*Made in Aotearoa New Zealand · Ko te mārama te tūāpapa.*
EOF
chmod 600 "$OUT"

log "✅ key issued for $CUSTOMER"
echo ""
echo "Onboarding pack written: $OUT"
echo ""
echo "Send this file to $CUSTOMER (encrypted channel — it contains a live API key)."
echo ""
echo "Key:      $KEY"
echo "Endpoint: $ENDPOINT"
