"""Retry the 3 failed model cards from v6 push."""
import json, os, sys
from pathlib import Path
sys.path.insert(0, r"S:\hf-publish")
from generate_cards_v6 import process_model, REGISTRY_PATH

FAILED = {
    "AbteeXAILab/lumynax-frontier-minimax-m25-unsloth",
    "AbteeXAILab/lumynax-infused-mistral-small-text-gguf",
    "AbteeXAILab/lumynax-reasoning-deepseek-distill-text-gguf",
}
registry = json.loads(Path(REGISTRY_PATH).read_text(encoding="utf-8"))
for m in registry["models"]:
    if m["repo_id"] in FAILED:
        print(process_model(m))
