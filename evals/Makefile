# Bench runner. Requires gateway up at http://localhost:8080.
GATEWAY ?= http://localhost:8080/v1
KEY     ?= lumynax-local-dev

.PHONY: bench bench-coders bench-chat bench-collate

bench: bench-coders bench-chat bench-collate

bench-coders:
	@for m in lumynax-coder-deepseek-v2-lite-16b-gguf lumynax-coder-codellama-70b-instruct-gguf \
	          lumynax-coder-qwen25-coder-32b-gguf lumynax-coder-starcoder2-15b-gguf \
	          lumynax-coder-yi-coder-9b-gguf; do \
	  python humaneval/runner.py --model $$m --gateway $(GATEWAY) --key $(KEY) || true; \
	done

bench-chat:
	@for m in lumynax-frontier-qwen25-72b-instruct-gguf lumynax-frontier-olmo2-32b-instruct \
	          lumynax-chat-yi-15-34b-gguf lumynax-frontier-phi-4-14b-gguf \
	          lumynax-chat-hermes-3-llama31-8b-gguf; do \
	  python mmlu/runner.py --model $$m --gateway $(GATEWAY) --key $(KEY) --limit-per-subject 5 || true; \
	done

bench-collate:
	python _common/collate.py > results.md
	@echo "results.md updated"
