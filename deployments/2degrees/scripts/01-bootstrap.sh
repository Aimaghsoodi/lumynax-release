#!/usr/bin/env bash
# 01-bootstrap: generate secrets, write configs, create state/.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$HERE/.."
ENV_DIR="$ROOT/env"
STATE="$ROOT/state"
LOG="$STATE/ops.log"

mkdir -p "$STATE" "$STATE/weights" "$STATE/audit" "$STATE/onboarding"
chmod 700 "$STATE"

log() { echo "[$(date -u +%FT%TZ)] [bootstrap] $*" | tee -a "$LOG"; }

# .gitignore so state/ never leaks
cat > "$ROOT/.gitignore" <<EOF
state/
env/.env
env/api-keys.json
env/routes.json
env/registry.json
*.log
EOF

# .env
if [[ ! -f "$ENV_DIR/.env" ]]; then
  log "generating .env"
  SEARXNG_SECRET="$(openssl rand -hex 32)"
  ADMIN_KEY="lx-admin-$(openssl rand -hex 24)"
  cat > "$ENV_DIR/.env" <<EOF
# Generated $(date -u +%FT%TZ). Do not commit.
SEARXNG_SECRET=$SEARXNG_SECRET
LUMYNAX_ADMIN_KEY=$ADMIN_KEY
HF_TOKEN=${HF_TOKEN:-}
LUMYNAX_PUBLIC_HOST=${LUMYNAX_PUBLIC_HOST:-localhost}
EOF
  chmod 600 "$ENV_DIR/.env"
else
  log ".env exists, keeping"
fi

# api-keys.json — seed with admin key
if [[ ! -f "$ENV_DIR/api-keys.json" ]]; then
  log "seeding api-keys.json with admin key"
  ADMIN_KEY="$(grep '^LUMYNAX_ADMIN_KEY=' "$ENV_DIR/.env" | cut -d= -f2)"
  cat > "$ENV_DIR/api-keys.json" <<EOF
{
  "$ADMIN_KEY": {
    "tenant": "admin",
    "jurisdiction": "NZ",
    "policies": ["allow-all"],
    "rate_limit": 0,
    "min_sovereignty_tier": null,
    "created_at": "$(date -u +%FT%TZ)"
  }
}
EOF
  chmod 600 "$ENV_DIR/api-keys.json"
  echo "$ADMIN_KEY" > "$STATE/admin-key"
  chmod 600 "$STATE/admin-key"
fi

# routes.json — empty initially
[[ -f "$ENV_DIR/routes.json" ]] || echo '{}' > "$ENV_DIR/routes.json"

# pull live registry
if [[ ! -f "$ENV_DIR/registry.json" ]]; then
  log "fetching live registry from HF"
  curl -fsSL https://huggingface.co/AbteeXAILab/marama-route/resolve/main/configs/lumynax_model_registry.json \
    -o "$ENV_DIR/registry.json"
fi

N_MODELS=$(python3 -c "import json; print(len(json.load(open('$ENV_DIR/registry.json'))['models']))")
log "registry has $N_MODELS models available to serve"

log "=== bootstrap complete ==="
echo ""
echo "Generated:"
echo "  $ENV_DIR/.env"
echo "  $ENV_DIR/api-keys.json (admin key in $STATE/admin-key)"
echo "  $ENV_DIR/routes.json"
echo "  $ENV_DIR/registry.json ($N_MODELS models)"
echo ""
echo "Next: bash 02-pull-weights.sh <model-slug-1> <model-slug-2> …"
echo "Pick from the registry — recommended starter:"
echo "  lumynax-chat-hermes-3-llama31-8b-gguf"
echo "  lumynax-coder-deepseek-v2-lite-16b-gguf"
echo "  lumynax-embed-bge-m3"
