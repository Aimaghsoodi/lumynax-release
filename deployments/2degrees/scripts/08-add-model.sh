#!/usr/bin/env bash
# 08-add-model: pull a new model and add it to the running stack without downtime.
# Usage: bash 08-add-model.sh <slug>
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$HERE/.."
ENV_DIR="$ROOT/env"
STATE="$ROOT/state"
LOG="$STATE/ops.log"

[[ $# -eq 1 ]] || { echo "usage: $0 <model-slug>"; exit 2; }
SLUG="$1"

echo "» pulling weights"
bash "$HERE/02-pull-weights.sh" "$SLUG"

echo "» regenerating compose with new service"
bash "$HERE/04-serve.sh"   # idempotent: regenerates compose, restarts only changed services

echo ""
echo "✅ $SLUG is live."
echo "Verify: curl -s -H \"Authorization: Bearer \$(cat $STATE/admin-key)\" http://localhost:8080/v1/models | jq -r '.data[].id' | grep $SLUG"
echo "[$(date -u +%FT%TZ)] [add-model] $SLUG live" >> "$LOG"
