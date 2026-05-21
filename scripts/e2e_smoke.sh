#!/usr/bin/env bash
# End-to-end smoke test: brings up Docker Compose, hits every gateway endpoint,
# validates responses against expected shape, tears down.
#
# Usage:  bash scripts/e2e_smoke.sh
#         bash scripts/e2e_smoke.sh --keep         # don't tear down on exit
#         bash scripts/e2e_smoke.sh --gpu          # use GPU-capable models
#
# Requires: docker + docker compose v2 + curl + jq

set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE"

KEEP=0
GPU=0
for arg in "$@"; do
  case "$arg" in
    --keep) KEEP=1 ;;
    --gpu)  GPU=1 ;;
  esac
done

GATEWAY="http://localhost:8080"
KEY="lumynax-local-dev"
HDR=(-H "Authorization: Bearer $KEY" -H "Content-Type: application/json")

cleanup() {
  if [[ $KEEP -eq 0 ]]; then
    echo "===== tearing down =====" >&2
    docker compose -f deployments/docker-compose.yml down -v 2>/dev/null || true
  else
    echo "===== --keep set, leaving stack up =====" >&2
  fi
}
trap cleanup EXIT

assert_eq() { [[ "$1" == "$2" ]] || { echo "FAIL: expected '$2', got '$1'"; exit 1; }; }
assert_contains() { grep -q "$2" <<< "$1" || { echo "FAIL: '$1' missing '$2'"; exit 1; }; }

echo "===== 1. preflight ====="
docker --version
docker compose version
command -v curl >/dev/null
command -v jq >/dev/null

echo "===== 2. ensure config files exist ====="
mkdir -p deployments/gateway/config
[[ -f deployments/gateway/config/api-keys.json ]] || \
  cp deployments/gateway/config/api-keys.example.json deployments/gateway/config/api-keys.json
[[ -f deployments/gateway/config/routes.json ]] || \
  cp deployments/gateway/config/routes.example.json deployments/gateway/config/routes.json
[[ -f deployments/gateway/config/registry.json ]] || curl -fsSL \
  https://huggingface.co/AbteeXAILab/marama-route/resolve/main/configs/lumynax_model_registry.json \
  -o deployments/gateway/config/registry.json

echo "===== 3. start stack (gateway + searxng only — skip model servers without GPU) ====="
if [[ $GPU -eq 1 ]]; then
  docker compose -f deployments/docker-compose.yml up -d
else
  docker compose -f deployments/docker-compose.yml up -d gateway searxng
fi

echo "===== 4. wait for gateway /health ====="
for i in $(seq 1 60); do
  if curl -fsS "$GATEWAY/health" >/dev/null 2>&1; then
    echo "  gateway healthy after ${i}s"; break
  fi
  [[ $i -eq 60 ]] && { echo "FAIL: gateway never became healthy"; docker compose -f deployments/docker-compose.yml logs gateway; exit 1; }
  sleep 1
done

echo "===== 5. /health shape ====="
health=$(curl -fsS "$GATEWAY/health")
echo "  $health"
assert_eq "$(jq -r '.ok' <<<"$health")" "true"
model_count=$(jq -r '.models' <<<"$health")
echo "  models in registry: $model_count"
[[ "$model_count" -ge 90 ]] || { echo "FAIL: expected ≥90 models, got $model_count"; exit 1; }

echo "===== 6. /v1/models (auth + list shape) ====="
models=$(curl -fsS "${HDR[@]}" "$GATEWAY/v1/models")
data_count=$(jq -r '.data | length' <<<"$models")
echo "  /v1/models returned $data_count entries"
[[ "$data_count" -ge 1 ]] || { echo "FAIL: empty model list"; exit 1; }
first_id=$(jq -r '.data[0].id' <<<"$models")
echo "  first id: $first_id"
assert_contains "$first_id" "lumynax-"

echo "===== 7. /v1/models without auth → 401 ====="
code=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY/v1/models")
assert_eq "$code" "401"

echo "===== 8. /v1/route (MaramaRoute scoring) ====="
pick=$(curl -fsS "${HDR[@]}" "$GATEWAY/v1/route?modalities=text&requires_local=true&jurisdiction=NZ")
chosen=$(jq -r '.model' <<<"$pick")
echo "  router picked: $chosen"
assert_contains "$chosen" "lumynax-"

echo "===== 9. /v1/tools/web_search ====="
search=$(curl -fsS "${HDR[@]}" -d '{"query":"Aotearoa New Zealand AI policy 2026","max_results":3}' \
  "$GATEWAY/v1/tools/web_search")
results_n=$(jq -r '.results | length' <<<"$search")
echo "  web_search returned $results_n results"
[[ "$results_n" -ge 1 ]] || { echo "WARN: search returned 0 (engine may be down) — non-fatal"; }

if [[ $GPU -eq 1 ]]; then
  echo "===== 10. /v1/chat/completions (real model) ====="
  body='{"model":"lumynax-chat-hermes-3-llama31-8b-gguf","messages":[{"role":"user","content":"Reply with exactly: SMOKE-OK"}],"max_tokens":16}'
  resp=$(curl -fsS "${HDR[@]}" -d "$body" "$GATEWAY/v1/chat/completions")
  content=$(jq -r '.choices[0].message.content' <<<"$resp")
  echo "  model said: $content"
  assert_contains "$content" "SMOKE-OK"
else
  echo "===== 10. /v1/chat/completions  [skipped: no --gpu flag] ====="
  echo "         re-run with --gpu after starting at least one llama-* service"
fi

echo ""
echo "===== ✅ SMOKE PASSED ====="
