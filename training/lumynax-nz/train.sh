#!/usr/bin/env bash
# LumynaX-NZ training launcher. One command, three modes.
#
# Single H100 LoRA (cheap, fast):
#   bash train.sh lora
#
# 8x H100 full SFT (proper):
#   bash train.sh sft
#
# Resume after crash:
#   bash train.sh resume
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="${1:-lora}"
BASE="${BASE_MODEL:-Qwen/Qwen2.5-3B-Instruct}"
OUT="$HERE/output/lumynax-nz-3b"

# Sanity
command -v accelerate >/dev/null || { echo "install: pip install accelerate transformers peft datasets bitsandbytes trl"; exit 2; }
[[ -d "$HERE/data" ]] || { echo "run datasets/prepare.py first"; exit 2; }

case "$MODE" in
  lora)
    echo "===== LumynaX-NZ LoRA on $BASE ====="
    accelerate launch --config_file "$HERE/configs/accelerate-single.yaml" \
      "$HERE/scripts/train_qlora.py" \
        --base_model "$BASE" \
        --data_dir "$HERE/data" \
        --output_dir "$OUT-lora" \
        --epochs 1.5 \
        --learning_rate 2e-4 \
        --batch_size 8 \
        --gradient_accumulation_steps 4 \
        --max_seq_len 4096 \
        --lora_r 64 --lora_alpha 128 \
        --bf16
    ;;
  sft)
    echo "===== LumynaX-NZ full SFT on $BASE (8x H100) ====="
    accelerate launch --config_file "$HERE/configs/accelerate-8gpu.yaml" \
      "$HERE/scripts/train_sft.py" \
        --base_model "$BASE" \
        --data_dir "$HERE/data" \
        --output_dir "$OUT" \
        --epochs 3 \
        --learning_rate 1e-5 \
        --batch_size 16 \
        --gradient_accumulation_steps 2 \
        --max_seq_len 4096 \
        --bf16 --gradient_checkpointing
    ;;
  resume)
    LAST_CKPT=$(ls -dt "$OUT"-*/checkpoint-* 2>/dev/null | head -1 || true)
    [[ -n "$LAST_CKPT" ]] || { echo "no checkpoint to resume from"; exit 2; }
    echo "resuming from $LAST_CKPT"
    accelerate launch --config_file "$HERE/configs/accelerate-8gpu.yaml" \
      "$HERE/scripts/train_sft.py" --resume_from "$LAST_CKPT"
    ;;
  *)
    echo "usage: $0 [lora|sft|resume]"; exit 2 ;;
esac

echo ""
echo "===== ✅ training complete — output at $OUT ====="
echo "next: python $HERE/eval.py --model $OUT"
echo "      bash $HERE/export.sh"
