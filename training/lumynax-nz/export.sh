#!/usr/bin/env bash
# Convert LumynaX-NZ from safetensors → GGUF Q4_K_M + push to HF.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="${1:-$HERE/output/lumynax-nz-3b}"
REPO="${REPO:-AbteeXAILab/lumynax-nz-3b}"

[[ -d "$OUT" ]] || { echo "no model at $OUT — run train.sh first"; exit 2; }

if [[ ! -d "$HERE/llama.cpp" ]]; then
  echo "cloning llama.cpp for conversion..."
  git clone --depth 1 https://github.com/ggerganov/llama.cpp "$HERE/llama.cpp"
fi
pushd "$HERE/llama.cpp" >/dev/null
pip install -q -r requirements.txt
make -j quantize 2>/dev/null || cmake -B build && cmake --build build --target llama-quantize
popd >/dev/null

GGUF_F16="$OUT.f16.gguf"
GGUF_Q4="$OUT-Q4_K_M.gguf"
python "$HERE/llama.cpp/convert_hf_to_gguf.py" "$OUT" --outfile "$GGUF_F16" --outtype f16
"$HERE/llama.cpp/build/bin/llama-quantize" "$GGUF_F16" "$GGUF_Q4" Q4_K_M
rm -f "$GGUF_F16"

echo "uploading $OUT → $REPO ..."
hf upload "$REPO" "$OUT" .
hf upload "$REPO" "$GGUF_Q4" "$(basename "$GGUF_Q4")"
echo "✅ pushed → https://huggingface.co/$REPO"
