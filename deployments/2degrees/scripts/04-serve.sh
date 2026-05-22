#!/usr/bin/env bash
# 04-serve: generate compose file from pulled models + start gateway + searxng + all model servers.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$HERE/.."
ENV_DIR="$ROOT/env"
STATE="$ROOT/state"
WEIGHTS="$STATE/weights"
COMPOSE="$ROOT/compose/docker-compose.yml"
LOG="$STATE/ops.log"

log() { echo "[$(date -u +%FT%TZ)] [serve] $*" | tee -a "$LOG"; }

source "$ENV_DIR/.env"
export SEARXNG_SECRET

# Generate compose file from the pulled weights
log "generating $COMPOSE from $WEIGHTS"
mkdir -p "$ROOT/compose"

cat > "$COMPOSE" <<'YAML'
services:
  gateway:
    image: ghcr.io/aimaghsoodi/lumynax-gateway:latest
    ports: ["8080:8080"]
    volumes:
      - ../env:/data:ro
      - ../state/audit:/var/log/lumynax
    environment:
      GATEWAY_REGISTRY_PATH: /data/registry.json
      GATEWAY_API_KEYS_PATH: /data/api-keys.json
      GATEWAY_ROUTES_PATH:   /data/routes.json
      GATEWAY_AUDIT_LOG:     /var/log/lumynax/audit.log
      SEARXNG_URL: http://searxng:8080
    depends_on: [searxng]
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 5s
      retries: 3

  searxng:
    image: searxng/searxng:latest
    expose: ["8080"]
    volumes:
      - ../../web-search/settings.yml:/etc/searxng/settings.yml:ro
    environment:
      SEARXNG_SECRET: ${SEARXNG_SECRET:?set in .env}
    restart: unless-stopped
YAML

# Append one llama-server service per pulled GGUF model
python3 - <<PY >> "$COMPOSE"
import json, os, glob
from pathlib import Path
routes = json.loads(Path("$ENV_DIR/routes.json").read_text())
for slug, url in routes.items():
    weights_dir = Path("$WEIGHTS") / slug
    if not weights_dir.exists(): continue
    ggufs = sorted(weights_dir.rglob("*.gguf"))
    if not ggufs:
        # vLLM path (safetensors)
        svc = "vllm-" + slug.replace("lumynax-","")[:30]
        print(f"""
  {svc}:
    image: vllm/vllm-openai:latest
    expose: ["8000"]
    volumes:
      - ../state/weights/{slug}:/model:ro
    command: ["--model","/model","--port","8000","--host","0.0.0.0","--max-model-len","16384","--dtype","auto"]
    deploy: {{resources: {{reservations: {{devices: [{{capabilities: [gpu]}}]}}}}}}
    restart: unless-stopped""")
        continue
    primary = ggufs[0]
    rel = primary.relative_to(weights_dir.parent.parent)
    svc = "llama-" + slug.replace("lumynax-","")[:30]
    print(f"""
  {svc}:
    image: ghcr.io/ggerganov/llama.cpp:server
    expose: ["8000"]
    volumes:
      - ../state/weights:/weights:ro
    command: ["--host","0.0.0.0","--port","8000","-c","16384","-ngl","-1","-m","/weights/{slug}/{primary.relative_to(weights_dir)}"]
    deploy: {{resources: {{reservations: {{devices: [{{capabilities: [gpu]}}]}}}}}}
    restart: unless-stopped""")
PY

log "starting stack"
docker compose -f "$COMPOSE" --env-file "$ENV_DIR/.env" up -d

log "waiting for gateway /health"
for i in $(seq 1 90); do
  if curl -fsS http://localhost:8080/health 2>/dev/null | grep -q '"ok":true'; then
    log "  healthy after ${i}s"; break
  fi
  sleep 2
  [[ $i -eq 90 ]] && { log "  gateway never healthy"; docker compose -f "$COMPOSE" logs gateway; exit 1; }
done

echo ""
echo "✅ stack healthy"
echo "   gateway:  http://localhost:8080"
echo "   admin key: $STATE/admin-key"
echo ""
echo "Smoke test:"
echo "   curl -H \"Authorization: Bearer \$(cat $STATE/admin-key)\" http://localhost:8080/v1/models | jq"
echo ""
echo "Next: bash 05-issue-key.sh \"<customer-name>\""
