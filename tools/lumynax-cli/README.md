# lumynax — Ollama-class CLI for the LumynaX release family

```bash
pip install lumynax            # base
pip install "lumynax[gguf]"    # + llama.cpp for GGUF models
pip install "lumynax[hf]"      # + transformers / accelerate
pip install "lumynax[full]"    # everything
```

## Verbs (Ollama-equivalent + LumynaX-specific)

```bash
# Discover
lumynax list                            # browse all 98 models
lumynax list --tier coder --max-params-b 30
lumynax aliases                         # short-name → slug map (84 built-ins)
lumynax info hermes3                    # full model card (alias OK)

# Get + run
lumynax pull hermes3                    # download with progress bar
lumynax run hermes3                     # interactive REPL via the gateway
lumynax run hermes3 "kia ora"           # one-shot
lumynax rm hermes3                      # free disk

# Smart routing
lumynax route "fix this Python bug"     # MaramaRoute picks the best model
lumynax route "translate to Maori: hi" --strategy te-reo
lumynax route "..." --explain --compare 3 --format json
cat code.py | lumynax route -

# Customize (Ollama Modelfile-compatible)
lumynax create nz-legal -f Modelfile    # derive a model with system prompt + params
lumynax cp hermes3 my-hermes --system "Be terse." --temperature 0.2
lumynax show-modelfile nz-legal

# Serve as OpenAI-compatible API
lumynax serve hermes3 --port 8080

# Integrations
lumynax opencode hermes3 > ~/.opencode/providers/lumynax.json
lumynax continue hermes3
lumynax vllm qwen-coder
lumynax llama-server hermes3
lumynax lm-studio hermes3
lumynax ollama hermes3

# Ops
lumynax ps                              # running model servers
lumynax stop hermes3
lumynax refresh                         # re-fetch registry

# Config
lumynax config-show
lumynax config-set default_strategy frontier
lumynax aliases --add tinybot:lumynax-tiny-qwen25-05b-gguf

# Shell completion
lumynax completion bash >> ~/.bashrc
```

## Slash commands in the REPL

```
/clear              clear history
/save <file>        save history JSON
/load <file>        replace history from JSON
/show               session info
/set <k> <v>        temperature | max_tokens | system | gateway_url
/system <text>      replace system prompt
/tools on|off       toggle web_search tool
/switch <model>     hot-swap (history preserved)
/multiline          multi-line input ('.' on its own line to end)
/?                  this help
/exit               leave (Ctrl-D also)
```

## Aliases — 84 short names you can use anywhere

Use any of these in place of the full slug:

| Family | Aliases |
| --- | --- |
| **Chat** | `hermes3`, `hermes`, `yi34`, `yi` |
| **Frontier** | `qwen3-235`, `qwen3-frontier`, `qwen2.5-72`, `qwen72`, `minimax`, `mixtral`, `dbrx`, `olmo32`, `phi4`, `phi35-moe`, `glm46` |
| **Coder** | `qwen3-coder`, `deepseek-v25`, `deepseek-coder`, `deepseek` (lite), `qwen-coder`, `starcoder2`, `yi-coder`, `codellama`, `codeqwen` |
| **Reasoning** | `r1`, `qwq`, `prover`, `math` |
| **Vision** | `qwen-vl`, `internvl3`, `pixtral`, `llava`, `aria`, `kimi-vl`, `glm46v` |
| **Long context** | `1m`, `qwen-1m`, `glm-1m`, `yi-200k`, `prolong` |
| **Speech** | `whisper`, `tts`, `kokoro`, `omni` |
| **Retrieval** | `bge`, `nomic`, `granite-embed`, `e5`, `rerank` |
| **Translation** | `nllb`, `translate`, `te-reo` |
| **Doc AI** | `nougat`, `donut`, `ocr`, `layout`, `table` |
| **Tiny / NZ** | `tiny`, `nz`, `nz-coder`, `olmoe`, `moonlight` |

Full alias→slug table: `lumynax aliases`. Add your own: `lumynax aliases --add <short>:<slug>`.

See [`MODELS.md`](MODELS.md) for the complete 98-model catalog with metadata.

## Routing reference

See [`ROUTER.md`](ROUTER.md) — strategy presets, score formula, decision tree, Python API.

## Config

Lives at `~/.lumynax/config.toml`. Default fields:

```toml
[lumynax]
gateway_url       = "http://localhost:8080"
api_key           = "lumynax-local-dev"
default_strategy  = "balanced"
default_jurisdiction = "NZ"
streaming         = true
color             = true
```

Override per-shell with env vars `LUMYNAX_GATEWAY` and `LUMYNAX_KEY`.

## Made in Aotearoa New Zealand · AbteeX AI Labs

[abteex.com](https://abteex.com) · [lumynax.com](https://lumynax.com) · [github.com/Aimaghsoodi/lumynax-release](https://github.com/Aimaghsoodi/lumynax-release)

*Ko te mārama te tūāpapa.*
