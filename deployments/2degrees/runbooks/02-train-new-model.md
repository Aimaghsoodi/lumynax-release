# Runbook · Train a new model

**Goal:** fine-tune a small base on your data, end up with a GGUF you can serve.

## Choose your base + recipe

| Recipe | Hardware | Wall time | Cost (rented) | Best for |
| --- | --- | --- | --- | --- |
| LoRA on Qwen2.5-3B | 1× H100 / A100-80 | 2-3 h | ~$8-30 | Quick domain adaptation |
| Full SFT on Qwen2.5-3B | 8× H100 | 6-12 h | ~$300-400 | Deeper specialization |
| LoRA on Qwen2.5-7B | 1× H100 | 4-6 h | ~$15-60 | Stronger base |
| LoRA on Qwen2.5-14B / Phi-4-14B | 1× H100 (BS=1) or 2× H100 | 12-18 h | ~$50-150 | Frontier-ish on domain |

## Prepare your data

Edit `../../training/lumynax-nz/datasets/sources.yaml` to point at your corpora. The included scaffold has stubs for NZ Hansard, Statutes, NLLB mi↔en, RNZ-CC, NZ uni open courseware, and tikanga (gated on iwi consultation).

To inject your own data:
1. Drop JSONL records like `{"text": "your text"}` into `../../training/lumynax-nz/data/raw/<source>.jsonl`
2. Add the source to `sources.yaml`
3. Re-run `python ../../training/lumynax-nz/datasets/prepare.py --out ../../training/lumynax-nz/data/`

## Train

```bash
bash scripts/03-train.sh lora        # single H100
bash scripts/03-train.sh sft         # 8× H100
bash scripts/03-train.sh resume      # if it crashed
```

The training scaffold lives at `training/lumynax-nz/` (monorepo-wide). It uses `accelerate` + `trl` + `peft` + `bitsandbytes` and writes checkpoints into `training/lumynax-nz/output/`.

## Evaluate

```bash
python ../../training/lumynax-nz/eval.py --model ../../training/lumynax-nz/output/lumynax-nz-3b-lora
```

This runs a quick NZ trivia + te reo translation check. For a proper benchmark:
```bash
cd ../../evals
make bench   # against the gateway once your new model is being served
```

## Export to GGUF + add to the live stack

```bash
bash ../../training/lumynax-nz/export.sh                       # writes Q4_K_M.gguf
mkdir -p state/weights/lumynax-nz-3b
cp ../../training/lumynax-nz/output/*.Q4_K_M.gguf state/weights/lumynax-nz-3b/
bash scripts/08-add-model.sh lumynax-nz-3b                     # adds to running gateway
```

## Push to AbteeXAILab on Hugging Face

```bash
hf upload AbteeXAILab/lumynax-nz-3b ../../training/lumynax-nz/output/lumynax-nz-3b
hf upload AbteeXAILab/lumynax-nz-3b state/weights/lumynax-nz-3b/lumynax-nz-3b-Q4_K_M.gguf
```

Replace the placeholder in the live registry by editing `AbteeXAILab/marama-route/configs/lumynax_model_registry.json` to mark `lumynax-nz-3b` as `package_state: "self-trained"` with a new `metadata.training_date`.
