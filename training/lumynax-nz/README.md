# LumynaX-NZ — a 3B model fine-tuned on Aotearoa New Zealand corpora

This is the **real** LumynaX-NZ recipe. Run it on an 8× H100 node (rentable for ~$24/hr on Lambda / RunPod / CoreWeave) and you'll get a usable 3B base specialised on NZ Hansard, Statutes, NZ News (CC-BY sources), and Te Reo Māori parallel data from NLLB.

Estimated cost (Q4 2026 pricing):
- **Single-node 1× H100** (LoRA only, 1.5 epochs): ~$30, 2-3 hours
- **8× H100** (full SFT, 3 epochs): ~$300-400, 6-12 hours
- **Output**: 3B safetensors + GGUF Q4_K_M, ~6 GB on disk

## Recipe

```bash
cd training/lumynax-nz

# 1. Prepare datasets — pulls public Hansard, Statutes, NZ news (open-access), NLLB-mi
python datasets/prepare.py --out data/

# 2. Launch training (QLoRA on Qwen2.5-3B base, or any apache-2.0 base)
bash train.sh

# 3. Evaluate on NZ-specific holdout + standard benchmarks
python eval.py --model output/lumynax-nz-3b

# 4. Convert to GGUF + push to HF
bash export.sh
```

## Why these sources

| Corpus | Why | Size |
| --- | --- | --- |
| **NZ Hansard** (Parliament proceedings 1854-present, public domain) | Formal NZ English register, gov terminology, te reo loanwords in context | ~3 GB text |
| **NZ Statutes** (legislation.govt.nz, Crown copyright, free to reuse with attribution) | Legal precision, NZ legal lexicon | ~600 MB text |
| **NZ News-CC** (RNZ podcast transcripts + commons-licensed NZ news) | Current-affairs Kiwi English | ~200 MB text |
| **NLLB-200 mi↔en parallel** (Meta, CC-BY-NC for research) | Te Reo Māori translation pairs | ~80k pairs |
| **NZ University open coursework** (Te Whare Wānanga o Otāgo etc) | Domain breadth (engineering, law, biosci, social sci) | ~400 MB text |
| **Tikanga & matāuranga Māori** (only public sources, with iwi attribution) | Kaupapa context | ~50 MB text |

Total ~4.3 GB of clean NZ-context text. Sized to deepen Qwen2.5-3B's NZ + te reo capacity without catastrophic forgetting.

## Base choice

**`Qwen/Qwen2.5-3B-Instruct`** — Apache-2.0, fits on a single H100 with LoRA, already 95% English with multilingual coverage including Māori. Alternative bases that work with this scaffold: `microsoft/Phi-3.5-mini-instruct`, `meta-llama/Llama-3.2-3B-Instruct` (gated — avoid), `allenai/OLMo-2-1B-1124-Instruct` (fully open).

## Sovereignty

- **No private NZ government data is included.** Every source is publicly licensed.
- **Iwi/Māori attribution is explicit** in `datasets/sources.yaml` — if any source asks to be removed, run `python datasets/prepare.py --exclude <source_id>` and re-train.
- **The output model is published under Apache-2.0** matching the Qwen base. The fine-tune deltas (LoRA adapters) ship separately so anyone can re-apply or modify.
- **Provenance JSON** at `output/provenance.json` records every dataset shard, its hash, its source URL, its licence.

## Output

After training, you get:
- `output/lumynax-nz-3b/` — full merged safetensors model
- `output/lumynax-nz-3b-lora/` — just the LoRA adapters
- `output/lumynax-nz-3b-Q4_K_M.gguf` — quantised for llama.cpp / Ollama
- `output/provenance.json` — full data + training audit chain
- `output/eval.md` — NZ-specific eval report

Push to `AbteeXAILab/lumynax-nz-3b` (replacing the placeholder there now):

```bash
hf upload AbteeXAILab/lumynax-nz-3b output/lumynax-nz-3b
```

## Made in Aotearoa New Zealand

By **AbteeX AI Labs**. [abteex.com](https://abteex.com) · [lumynax.com](https://lumynax.com)

*Ko te mārama te tūāpapa. Kia mau ki te mōhio o nehe — hold to the knowledge of old.*
