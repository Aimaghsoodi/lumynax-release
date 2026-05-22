#!/usr/bin/env bash
# 03-train: hand off to the LumynaX-NZ training recipe.
# Usage:  bash 03-train.sh lora        (single H100, ~3 h, ~$30)
#         bash 03-train.sh sft         (8x H100, ~6-12 h, ~$300-400)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$HERE/.."
MONOREPO="$ROOT/../.."
TRAIN_DIR="$MONOREPO/training/lumynax-nz"

MODE="${1:-lora}"
[[ -d "$TRAIN_DIR" ]] || { echo "expected training scaffold at $TRAIN_DIR"; exit 2; }

cd "$TRAIN_DIR"
echo "» installing training requirements"
pip install -q -r requirements.txt

echo "» preparing dataset"
python datasets/prepare.py --out data/

echo "» launching training ($MODE)"
bash train.sh "$MODE"

echo ""
echo "✅ training done. Next:"
echo "  python $TRAIN_DIR/eval.py --model $TRAIN_DIR/output/lumynax-nz-3b-${MODE}"
echo "  bash $TRAIN_DIR/export.sh   # converts to GGUF + pushes to HF"
echo ""
echo "Then to serve it:"
echo "  cp -r $TRAIN_DIR/output/lumynax-nz-3b-${MODE}-Q4_K_M.gguf $ROOT/state/weights/lumynax-nz-3b/"
echo "  bash $HERE/08-add-model.sh lumynax-nz-3b"
