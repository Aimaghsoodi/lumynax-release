#!/usr/bin/env bash
# 06-monitor: live health + audit tail + throughput summary.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$HERE/.."
STATE="$ROOT/state"
ENV_DIR="$ROOT/env"
source "$ENV_DIR/.env"

GATEWAY="${1:-http://localhost:8080}"
ADMIN_KEY="$(cat "$STATE/admin-key" 2>/dev/null || echo "$LUMYNAX_ADMIN_KEY")"

clear
while true; do
  tput cup 0 0
  echo "=== LumynaX 2degrees monitor — $(date -u +%FT%TZ) ==="
  echo ""

  echo "» Gateway health"
  curl -fsS --max-time 3 "$GATEWAY/health" 2>/dev/null | jq -c . || echo "  (unreachable)"
  echo ""

  echo "» Models / routes"
  curl -fsS --max-time 3 -H "Authorization: Bearer $ADMIN_KEY" "$GATEWAY/v1/models" 2>/dev/null \
    | jq -r '.data[]?.id' | head -10 | sed 's/^/  /'
  echo ""

  echo "» Containers"
  docker compose -f "$ROOT/compose/docker-compose.yml" ps --format 'table {{.Service}}\t{{.Status}}\t{{.Health}}' 2>/dev/null | head -12
  echo ""

  echo "» GPU"
  if command -v nvidia-smi >/dev/null; then
    nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total --format=csv,noheader | sed 's/^/  /' | head -8
  else
    echo "  no nvidia-smi"
  fi
  echo ""

  echo "» Last 6 audit events"
  if [[ -f "$STATE/audit/audit.log" ]]; then
    tail -6 "$STATE/audit/audit.log" 2>/dev/null \
      | jq -r '"  \(.ts // "?") \(.event // "?") \(.tenant // "-") \(.model // "")"' 2>/dev/null \
      || tail -6 "$STATE/audit/audit.log"
  else
    echo "  (no audit log yet)"
  fi
  echo ""

  echo "» Requests in the last hour"
  if [[ -f "$STATE/audit/audit.log" ]]; then
    NOW=$(date +%s); HORIZON=$(( NOW - 3600 ))
    awk -v h="$HORIZON" -F'"ts":' 'NF>1 {gsub(/^[^0-9.]*/, "", $2); ts=$2+0; if (ts>h) c++} END{print "  total: " (c+0)}' "$STATE/audit/audit.log" 2>/dev/null \
      || echo "  parse skipped"
  fi
  echo ""
  echo "  Ctrl-C to exit"
  sleep 5
done
