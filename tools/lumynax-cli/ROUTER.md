# LumynaX Router — reference

`lumynax route` picks the best model in the 98-model family for a given prompt + constraints. It does six things in this order:

1. **Analyze** the prompt — detects code, vision, audio, math, te reo, long-context, tool intent, JSON intent
2. **Gate** every model in the registry on six rules: forbid, modality, sovereignty/residency, capability (tools/json/context/size), and per-strategy hard requirements
3. **Score** survivors by `quality × sovereignty × cost + task_match + context_headroom + family_bonus − size_penalty` with **strategy-tuned weights**
4. **Rank** and pick the top
5. **Explain** the decision (every gate, every component, every reject reason)
6. **Render** the result (`pretty` / `json` / `slug` / `openai-stub`)

## Quick reference

```bash
lumynax route "fix this bug"                          # plain
lumynax route --strategy coder "fix this bug"         # bias toward coder family
lumynax route --strategy te-reo "translate hello"     # bias toward NLLB / GLM-1M
lumynax route --strategy frontier --no-local "..."    # best quality, ignore locality
lumynax route --strategy cheap --max-params-b 10 ...  # cheapest path
cat code.py | lumynax route -                          # stdin
lumynax route "..." --format slug                      # pipeable
lumynax route "..." --format json                      # machine-readable
lumynax route "..." --format openai-stub               # ready-to-curl command
lumynax route "..." --explain --show-rejected 5        # debug mode
lumynax route "..." --compare 5                        # top-5 side-by-side
lumynax route "..." --why-not lumynax-frontier-qwen3-235b-a22b-instruct
```

## Strategy presets

| Strategy | Quality | Sovereignty | Cost | Task | Notes |
| --- | ---: | ---: | ---: | ---: | --- |
| **balanced** *(default)* | 2.0 | 1.5 | 0.5 | 3.0 | Sensible default |
| **cheap** | 1.0 | 1.0 | 3.0 | 2.0 | Heavy cost penalty + 10B+ models penalized |
| **frontier** | 4.0 | 0.5 | 0.1 | 2.0 | Quality dominates |
| **local-only** | 1.5 | 4.0 | 0.5 | 3.0 | Forces sovereignty tier ≥ 3 |
| **coder** | 2.5 | 1.0 | 0.5 | 5.0 | Big task-match bonus for "coder" tag |
| **vision** | 2.5 | 1.0 | 0.5 | 5.0 | Big task-match bonus for "vision" tag |
| **reasoning** | 3.0 | 1.0 | 0.3 | 5.0 | Favors QwQ / Prover-V2 / R1-Distill / Phi-3.5-MoE |
| **te-reo** | 2.0 | 2.0 | 0.5 | 5.0 | Favors NLLB-200 / GLM-4-1M / Qwen-1M |

## What the prompt analyzer detects

For each prompt, the analyzer reports:

| Signal | Examples | Effect |
| --- | --- | --- |
| `is_code` | triple-backticks, `def foo`, language names | adds `coder` task-tag |
| `is_math` | `prove that`, `theorem`, `∫`, `\frac` | adds `math` + `reasoning` tags |
| `is_reasoning` | `think step by step`, `prove`, math | adds `reasoning` tag |
| `needs_vision` | `![]()`, `<img>`, `describe this image`, `.jpg` | adds `vision` modality + tag |
| `needs_audio` | `.mp3`, `transcribe`, `audio recording` | adds `audio` modality + tag |
| `needs_tools` | `call the X function`, `web search`, `invoke` | sets `requires_tools=true` |
| `needs_json` | `return as JSON`, `valid JSON`, `response_format` | sets `requires_json=true` |
| `is_translation` | `translate to <lang>` | adds `translate` + target-lang tag |
| `contains_te_reo` | te reo Māori phrases or "translate to Māori" | adds `te-reo` tag |
| `is_long_context` | estimated > 32k tokens | sets `min_context` to 2× estimated |
| `is_embedding_task` | `embed`, `cosine similarity`, `rerank` | adds `embedding` tag |

These are heuristics (regex) — they're fast and they're **transparent**. If a heuristic mis-fires, just override with the corresponding CLI flag (`--no-tools`, `--modalities text`, etc.).

## Score breakdown

For each surviving candidate, the score is the sum of these components:

| Component | Formula | Note |
| --- | --- | --- |
| `quality` | (6 − quality_rank) × weights.quality | quality_rank 1=best, 5=worst |
| `sovereignty` | sovereignty_tier × weights.sovereignty | 1=remote, 5=NZ-local |
| `cost` | (6 − cost_rank) × weights.cost | 1=cheapest, 5=priciest |
| `task_match` | matched_tags × weights.task_match | overlap of (analysis + hint + strategy) ∩ model.tags |
| `ctx_headroom` | min(2, log2(model_ctx / needed_ctx)) | small bonus for spare context |
| `family` | +2.0 if `--prefer-family` matches | else 0 |
| `size_penalty` | strategy=cheap penalises 20B+ models | else 0 |

Use `--compare N` to see the components side-by-side for the top N.

## Output formats

```bash
lumynax route "..." --format pretty       # default — rich UI, score breakdown, runners-up
lumynax route "..." --format json         # one-line JSON for machine consumption
lumynax route "..." --format slug         # just the slug, perfect for pipes
lumynax route "..." --format openai-stub  # a copy-pasteable curl
```

## Common patterns

### Route then run

```bash
SLUG=$(lumynax route "fix the bug in this code" --format slug)
lumynax run $SLUG -i
```

### Use the picked model with curl

```bash
lumynax route "code review please" --format openai-stub
# prints:
# curl ... -d '{"model":"lumynax-coder-...","messages":[...]}'
```

### Build a smart frontend that hits MaramaRoute

```python
from lumynax.router import Router, Strategy
from lumynax.registry import models

r = Router(models=models())
d = r.route(user_prompt,
            strategy=Strategy.BALANCED,
            jurisdiction=tenant.jurisdiction,
            requires_local=tenant.requires_local)
print("Picked:", d.slug, "score:", d.score)
print("Why:", d.breakdown.components)
print("Detected:", d.analysis.task_tags())
```

### Compare two strategies on the same prompt

```bash
lumynax route "fix bug" --strategy balanced --compare 1
lumynax route "fix bug" --strategy frontier --compare 1
```

### Debug "why didn't it pick X"

```bash
lumynax route "..." --why-not lumynax-frontier-qwen3-235b-a22b-instruct
# → "❌ rejected at gate 'residency': residency=['NZ','AU','global'] excludes <something>"
# Or:
# → "🥈 ranked 3rd (score 11.5 vs pick 14.2)"
```

## API (Python)

```python
from lumynax.router import Router, Strategy
from lumynax.registry import models

r = Router(models=models())

d = r.route(
    prompt="```python\ndef bug():\n  pass\n``` fix this",
    strategy=Strategy.CODER,
    jurisdiction="NZ",
    requires_local=True,
)

print(d.slug)             # lumynax-coder-deepseek-v2-lite-16b-gguf
print(d.score)            # 14.2
print(d.breakdown.components)
print(d.analysis.is_code) # True
print(d.runners_up[0].repo_id)

for rej in d.rejected[:5]:
    print(rej.repo_id, rej.gate, rej.reason)
```

## Gateway endpoint

The same router runs inside the gateway at `GET /v1/route`:

```bash
curl -H "Authorization: Bearer $KEY" \
  "http://localhost:8080/v1/route?modalities=text&requires_local=true&jurisdiction=NZ"
```

Note: the gateway currently does a simpler version of the scoring (no prompt analysis). To get the full router behaviour over HTTP, call `lumynax route ...` on the host, or upgrade the gateway to import `lumynax.router.Router` (TODO).

## Tested

```bash
cd tools/lumynax-cli
pytest tests/test_router.py -v
# 24/24 passing — analyzer + scorer + gates + renderers
```

## Made in Aotearoa New Zealand · AbteeX AI Labs

[abteex.com](https://abteex.com) · [lumynax.com](https://lumynax.com) · *Ko te mārama te tūāpapa.*
