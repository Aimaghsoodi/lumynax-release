# lumynax — CLI for the LumynaX release family

```bash
pip install lumynax            # base install (registry + download)
pip install "lumynax[gguf]"    # add llama-cpp for GGUF models
pip install "lumynax[hf]"      # add transformers / accelerate
pip install "lumynax[full]"    # everything
```

## Commands

```bash
lumynax list                                # show all 98+ models
lumynax list --tier frontier --modality text --max-params-b 100
lumynax info lumynax-frontier-qwen3-235b-a22b-instruct
lumynax download lumynax-tiny --no-weights  # scaffold-only
lumynax route "explain transformers" --local --tools
lumynax run lumynax-chat-hermes-3-llama31-8b-gguf -i
lumynax refresh                             # re-fetch the registry
```

Auth: set `HF_TOKEN` for higher rate limits (not required for public reads).

Registry lives at `AbteeXAILab/marama-route` on Hugging Face. The CLI mirrors
**MaramaRoute** scoring locally so `lumynax route <prompt>` returns the same
pick the production router would.
