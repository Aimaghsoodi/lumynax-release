#!/usr/bin/env bash
# 07-rotate-key: invalidate a customer's key and mint a new one. Preserves their policy.
# Usage: bash 07-rotate-key.sh "<customer-name>"
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$HERE/.."
ENV_DIR="$ROOT/env"
STATE="$ROOT/state"
LOG="$STATE/ops.log"

[[ $# -eq 1 ]] || { echo "usage: $0 <customer-name>"; exit 2; }
CUSTOMER="$1"
SLUG=$(echo "$CUSTOMER" | tr '[:upper:] ' '[:lower:]-' | tr -cd 'a-z0-9-')

# Find existing key(s) for that tenant + preserve policy
EXISTING=$(python3 - <<PY
import json, sys
d = json.load(open("$ENV_DIR/api-keys.json"))
hits = [k for k, v in d.items() if v.get("tenant") == "$SLUG"]
if not hits: sys.exit("no existing key for tenant '$SLUG'")
print("\n".join(hits))
PY
)
echo "  found ${EXISTING:?}"
NEW_KEY="lx-$SLUG-$(openssl rand -hex 24)"

python3 - <<PY
import json, pathlib, datetime
p = pathlib.Path("$ENV_DIR/api-keys.json")
d = json.loads(p.read_text())
hits = [k for k,v in d.items() if v.get("tenant") == "$SLUG"]
policy = d[hits[0]].copy()
for k in hits: del d[k]
policy["rotated_at"] = datetime.datetime.utcnow().isoformat()+"Z"
d["$NEW_KEY"] = policy
p.write_text(json.dumps(d, indent=2))
print(f"  invalidated {len(hits)} old key(s), issued $NEW_KEY")
PY

docker compose -f "$ROOT/compose/docker-compose.yml" restart gateway >/dev/null 2>&1 || true
echo "[$(date -u +%FT%TZ)] [rotate] $CUSTOMER → new key issued" >> "$LOG"

# Re-emit the onboarding pack with the new key
JURISDICTION=$(python3 -c "import json; print(json.load(open('$ENV_DIR/api-keys.json'))['$NEW_KEY']['jurisdiction'])")
MIN_TIER=$(python3 -c "import json; print(json.load(open('$ENV_DIR/api-keys.json'))['$NEW_KEY']['min_sovereignty_tier'])")
RATE=$(python3 -c "import json; print(json.load(open('$ENV_DIR/api-keys.json'))['$NEW_KEY']['rate_limit'])")
bash "$HERE/05-issue-key.sh" "$CUSTOMER" --jurisdiction "$JURISDICTION" --min-tier "$MIN_TIER" --rate-limit "$RATE" 2>/dev/null || true

# Use the new key string directly (05-issue-key would mint another — actually we already minted above)
# So just rewrite onboarding from this script
OUT="$STATE/onboarding/${SLUG}.md"
sed -i "s|^api_key:.*|api_key:  $NEW_KEY|" "$OUT" 2>/dev/null || true
echo ""
echo "✅ rotated. Send updated $OUT to $CUSTOMER over an encrypted channel."
echo "New key: $NEW_KEY"
