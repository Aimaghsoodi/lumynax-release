#!/usr/bin/env bash
# 02-pull-weights: download chosen model weights from HF + register them in routes.json.
# Usage: bash 02-pull-weights.sh <slug1> [slug2 ...]
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$HERE/.."
ENV_DIR="$ROOT/env"
STATE="$ROOT/state"
WEIGHTS="$STATE/weights"
LOG="$STATE/ops.log"
source "$ENV_DIR/.env"
export HF_TOKEN

log() { echo "[$(date -u +%FT%TZ)] [pull] $*" | tee -a "$LOG"; }

[[ $# -ge 1 ]] || { echo "usage: $0 <model-slug> [more-slugs ...]"; exit 2; }

for SLUG in "$@"; do
  log "=== $SLUG ==="
  if ! python3 -c "import json,sys; r=json.load(open('$ENV_DIR/registry.json')); slugs=[m['repo_id'].split('/')[-1] for m in r['models']]; sys.exit(0 if '$SLUG' in slugs else 1)"; then
    log "  ! $SLUG not in registry — typo? See env/registry.json"; continue
  fi
  DEST="$WEIGHTS/$SLUG"
  if [[ -d "$DEST" && -n "$(ls "$DEST"/*.gguf "$DEST"/*.safetensors 2>/dev/null || true)" ]]; then
    log "  already pulled — skipping"
  else
    log "  pulling AbteeXAILab/$SLUG → $DEST"
    pip install -q huggingface_hub 2>/dev/null || true
    python3 -c "
from huggingface_hub import snapshot_download
import os
snapshot_download(repo_id='AbteeXAILab/$SLUG', local_dir='$DEST',
                  token=os.environ.get('HF_TOKEN'),
                  allow_patterns=['*.gguf','*.safetensors','*.bin','*.json','*.model','tokenizer*','config*','special_tokens_map.json','generation_config.json','quickstart.py','requirements.txt'])
" || { log "  FAILED"; continue; }
  fi
  # Add to routes.json — point at the service name we'll start in 04-serve.sh
  python3 - <<PY
import json, pathlib
slug = "$SLUG"
routes = json.loads(pathlib.Path("$ENV_DIR/routes.json").read_text())
svc = "llama-" + slug.replace("lumynax-","")[:30]
routes[slug] = f"http://{svc}:8000/v1"
pathlib.Path("$ENV_DIR/routes.json").write_text(json.dumps(routes, indent=2))
print(f"  registered route: {slug} → {svc}:8000")
PY
done

log "=== pull complete ==="
echo ""
echo "Pulled $# model(s). Next: bash 04-serve.sh"
