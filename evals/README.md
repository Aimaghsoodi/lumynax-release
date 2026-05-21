# LumynaX benchmark suite

Runs standard benchmarks against the LumynaX family via the gateway's OpenAI-compatible endpoint. Each benchmark is a folder under `evals/` with a `runner.py`, a baseline `expected.json` (upstream-published numbers, cited), and a `results/` directory that the GH Actions workflow populates.

## Layout

```
evals/
├── README.md                ← you are here
├── _common/                 ← shared client + scoring helpers
├── humaneval/               ← Python code-generation, pass@1 / pass@10
├── mtbench/                 ← multi-turn open-ended chat, 1-10 scoring by judge
├── mmlu/                    ← 57-subject knowledge, accuracy
├── mteb-mini/               ← retrieval/reranking, NDCG@10 / Recall@10
├── librispeech/             ← ASR (whisper / asr models), WER
└── results.md               ← auto-generated cross-benchmark table
```

## Run one

```bash
# Spin up the gateway first
docker compose -f deployments/docker-compose.yml up -d

# Then run a benchmark against a specific model
python evals/humaneval/runner.py --model lumynax-coder-deepseek-v2-lite-16b-gguf \
                                  --gateway http://localhost:8080/v1 \
                                  --key lumynax-local-dev
```

Each runner writes `results/<model>/<benchmark>.json` with the score, sample outputs, and timestamp.

## Run them all

```bash
make bench   # iterates every benchmark × every supporting model
```

The Makefile knows which models can run which benchmarks (a coder model gets HumanEval; an embedder gets MTEB; etc.).

## Why this matters

The whole point of publishing a curated family is *trust*. Numbers people can check beat marketing. Each `expected.json` cites the upstream's own published number for the underlying model; LumynaX's numbers should match within 1-2 pts since we're shipping the same weights through the gateway.

If a LumynaX run lands materially below the upstream's published number, something in our wrapper is wrong — that's the signal we want.

## Current status

The runners exist; the result tables are seeded with **published upstream numbers** (cited per row). Runs against the LumynaX gateway are pending compute. Tag a release as `bench-v0.1.0` to trigger an auto-run on the GH Actions self-hosted runner (when configured).
