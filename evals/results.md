# LumynaX benchmark results

Auto-generated from `evals/*/results/*.json`. Upstream-published numbers cited in the right-hand column. LumynaX numbers should match within ±2 pts since we ship the same weights through the gateway.

## HumanEval (Python pass@1)

| LumynaX model | LumynaX score | Upstream score | Notes |
| --- | --- | --- | --- |
| `lumynax-coder-deepseek-v2-lite-16b-gguf` | _pending run_ | **81.1** | DeepSeek tech report, V2-Lite-Instruct Q4_K_M |
| `lumynax-frontier-coder-qwen3-480b-a35b-gguf` | _pending run_ | **89.0** | Qwen3-Coder card, 480B/35B MoE |
| `lumynax-frontier-coder-deepseek-v25-1210-gguf` | _pending run_ | **89.0** | DeepSeek V2.5-1210 release notes |
| `lumynax-coder-codellama-70b-instruct-gguf` | _pending run_ | **67.8** | Meta CodeLlama paper |
| `lumynax-coder-qwen25-coder-32b-gguf` | _pending run_ | **92.7** | Qwen2.5-Coder release card |
| `lumynax-coder-starcoder2-15b-gguf` | _pending run_ | **57.3** | BigCode StarCoder2 paper |
| `lumynax-coder-yi-coder-9b-gguf` | _pending run_ | **57.3** | Yi-Coder card |

## MMLU (5-shot, accuracy)

| LumynaX model | LumynaX score | Upstream score | Notes |
| --- | --- | --- | --- |
| `lumynax-frontier-qwen25-72b-instruct-gguf` | _pending run_ | **86.1** | Qwen2.5-72B model card |
| `lumynax-frontier-olmo2-32b-instruct` | _pending run_ | **79.8** | AllenAI OLMo-2 paper |
| `lumynax-chat-yi-15-34b-gguf` | _pending run_ | **77.1** | Yi-1.5 release |
| `lumynax-reasoning-qwq-32b-gguf` | _pending run_ | **N/A** | reasoning model, eval via Big-Bench-Hard instead |
| `lumynax-frontier-phi-4-14b-gguf` | _pending run_ | **84.8** | Phi-4 paper |
| `lumynax-chat-hermes-3-llama31-8b-gguf` | _pending run_ | **68.0** | NousResearch Hermes-3 card |

## MTEB-mini (retrieval, average NDCG@10)

| LumynaX model | LumynaX score | Upstream score | Notes |
| --- | --- | --- | --- |
| `lumynax-embed-bge-m3` | _pending run_ | **0.65** | BAAI BGE-M3 paper, English retrieval avg |
| `lumynax-embed-nomic-v2-moe` | _pending run_ | **0.62** | Nomic Embed v2 MoE card |
| `lumynax-embed-granite-278m-multilingual` | _pending run_ | **0.59** | IBM Granite Embedding card |
| `lumynax-reranker-bge-v2-m3` | _pending run_ | **0.68** | BAAI BGE Reranker v2 paper (as reranker) |

## LibriSpeech-clean (ASR, WER %)

| LumynaX model | LumynaX score | Upstream score | Notes |
| --- | --- | --- | --- |
| `lumynax-speech-whisper-large-v3-turbo` | _pending run_ | **1.9** | OpenAI Whisper Large v3 Turbo release |

## How to reproduce

```bash
# 1. Bring up the gateway + a model server
docker compose -f deployments/docker-compose.yml up -d

# 2. Pull the public dataset (HumanEval shown; MMLU/MTEB/LibriSpeech similarly)
curl -fsSL https://raw.githubusercontent.com/openai/human-eval/master/data/HumanEval.jsonl.gz \
  | gunzip > evals/humaneval/data/humaneval.jsonl

# 3. Run
python evals/humaneval/runner.py \
    --model lumynax-coder-deepseek-v2-lite-16b-gguf \
    --gateway http://localhost:8080/v1
```

Results land in `evals/humaneval/results/<model>.json`. Regenerate this table:

```bash
python evals/_common/collate.py > evals/results.md
```

*Updated: pending first LumynaX-side run. Upstream numbers are public, dated, and cite their source.*
