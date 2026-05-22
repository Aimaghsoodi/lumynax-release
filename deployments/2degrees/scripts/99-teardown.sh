#!/usr/bin/env bash
# 99-teardown: stop the stack. By default keeps weights + audit. --purge wipes everything.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$HERE/.."

PURGE=0
[[ "${1:-}" == "--purge" ]] && PURGE=1

echo "» stopping stack"
docker compose -f "$ROOT/compose/docker-compose.yml" down

if [[ $PURGE -eq 1 ]]; then
  echo "» PURGE: wiping state/, env/api-keys.json, env/.env"
  read -p "Really wipe customer keys + audit ledger? type 'WIPE': " ans
  [[ "$ans" == "WIPE" ]] || { echo "aborted"; exit 1; }
  rm -rf "$ROOT/state" "$ROOT/env/api-keys.json" "$ROOT/env/.env" "$ROOT/env/routes.json"
  rm -f "$ROOT/compose/docker-compose.yml"
fi

echo "✅ down."
[[ $PURGE -eq 1 ]] && echo "All state wiped. Re-run 01-bootstrap.sh to start over."
