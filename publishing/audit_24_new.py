"""Audit the 24 new repos for weight completeness."""
import os, json
from pathlib import Path
from huggingface_hub import HfApi
api = HfApi(token=os.environ["HF_TOKEN"])

PACKS = {
    "A": ["lumynax-speech-whisper-large-v3-turbo","lumynax-speech-kokoro-82m-tts","lumynax-reranker-bge-v2-m3","lumynax-guard-text-moderation","lumynax-math-qwen25-math-7b-gguf","lumynax-translate-nllb-200-3b","lumynax-coder-deepseek-v2-lite-16b-gguf","lumynax-chat-hermes-3-llama31-8b-gguf"],
    "C": ["lumynax-doc-nougat-base","lumynax-doc-donut-base","lumynax-ocr-trocr-large-printed","lumynax-ocr-trocr-large-handwritten","lumynax-doc-layoutlmv3-base","lumynax-doc-table-transformer-detection","lumynax-embed-nomic-v2-moe","lumynax-embed-granite-278m-multilingual"],
    "B": ["lumynax-frontier-qwen25-72b-instruct-gguf","lumynax-frontier-olmo2-32b-instruct","lumynax-chat-yi-15-34b-gguf","lumynax-reasoning-internlm3-8b-gguf","lumynax-multimodal-aria-25b-moe","lumynax-multimodal-llava-next-34b","lumynax-reasoning-qwq-32b-gguf","lumynax-frontier-phi-4-14b-gguf"],
}
WEIGHT_EXT = (".gguf",".safetensors",".bin",".pt",".pth",".onnx")

problems = []
for pk, repos in PACKS.items():
    print(f"\n=== Pack {pk} ===")
    for r in repos:
        full = f"AbteeXAILab/{r}"
        try:
            info = api.repo_info(full, files_metadata=True)
            weights = [(s.rfilename, s.size or 0) for s in info.siblings if s.rfilename.lower().endswith(WEIGHT_EXT)]
            total = sum(s for _,s in weights)
            print(f"  {r:<55} {len(weights):>3} files {total/1e9:>6.2f} GB")
            if total == 0:
                problems.append((full, "no weights"))
        except Exception as e:
            print(f"  {r}: ERR {e}")
            problems.append((full, str(e)[:80]))
print()
print(f"=== {len(problems)} repos with issues ===")
for r, p in problems: print(f"  {r}: {p}")
