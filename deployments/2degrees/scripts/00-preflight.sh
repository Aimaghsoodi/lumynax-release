#!/usr/bin/env bash
# 00-preflight: verify GPU + Docker + disk + network are sane before doing anything else.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$HERE/.."
mkdir -p "$ROOT/state"
LOG="$ROOT/state/ops.log"

log()  { local m="[$(date -u +%FT%TZ)] [preflight] $*"; echo "$m" | tee -a "$LOG"; }
ok()   { echo -e "  \033[32m✓\033[0m $*"; }
warn() { echo -e "  \033[33m!\033[0m $*"; }
fail() { echo -e "  \033[31m✗\033[0m $*"; FAIL=1; }

FAIL=0
log "=== preflight start ==="

echo "» OS"
uname -a
case "$(uname -s)" in
  Linux) ok "Linux";;
  *) fail "expected Linux; got $(uname -s)";;
esac

echo "» Docker"
if command -v docker >/dev/null && docker info >/dev/null 2>&1; then
  ok "docker $(docker --version | awk '{print $3}')"
  if docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi >/dev/null 2>&1; then
    ok "docker GPU runtime works"
  else
    fail "docker can't see GPUs. Install nvidia-container-toolkit and restart docker."
  fi
else
  fail "docker not installed or daemon not running"
fi

echo "» Docker Compose"
docker compose version >/dev/null 2>&1 && ok "$(docker compose version | head -1)" || fail "docker compose v2 missing"

echo "» NVIDIA driver + GPU"
if command -v nvidia-smi >/dev/null; then
  ok "$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -1)"
  GPUS=$(nvidia-smi --query-gpu=count --format=csv,noheader | head -1)
  ok "$GPUS GPU(s) visible"
else
  warn "nvidia-smi not on PATH — CPU-only mode possible but only for tiny models"
fi

echo "» Disk"
AVAIL_GB=$(df -BG "$ROOT" | tail -1 | awk '{print $4}' | tr -d 'G')
if [[ "$AVAIL_GB" -ge 400 ]]; then
  ok "$AVAIL_GB GB free at $ROOT"
elif [[ "$AVAIL_GB" -ge 100 ]]; then
  warn "$AVAIL_GB GB free — enough for small models only; need 400+ GB for the curated starter set"
else
  fail "$AVAIL_GB GB free — need at least 100 GB to start"
fi

echo "» Outbound HTTPS"
for host in huggingface.co ghcr.io duckduckgo.com; do
  if curl -fsS --max-time 5 "https://$host/" >/dev/null 2>&1; then
    ok "reach $host"
  else
    warn "no reach to $host — verify firewall if downloads later fail"
  fi
done

echo "» HF token"
if [[ -z "${HF_TOKEN:-}" ]]; then
  warn "HF_TOKEN is not set. Export it: 'export HF_TOKEN=hf_...' (read-only is fine)"
else
  ok "HF_TOKEN present"
fi

echo "» Tools"
for t in curl jq openssl python3 git; do
  command -v "$t" >/dev/null && ok "$t" || fail "$t missing"
done

log "=== preflight end (fail=$FAIL) ==="
if [[ "$FAIL" -ne 0 ]]; then
  echo ""
  echo "Preflight FAILED. Fix the ✗ items above, then re-run."
  exit 1
fi
echo ""
echo "Preflight OK. Next: bash 01-bootstrap.sh"
