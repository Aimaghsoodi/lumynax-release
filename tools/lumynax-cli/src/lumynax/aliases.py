"""Short-name aliases for LumynaX slugs — Ollama-style 'hermes3' → 'lumynax-chat-hermes-3-llama31-8b-gguf'.

Resolution order (in `resolve()`):
  1. Exact slug match (case-insensitive, with/without 'AbteeXAILab/' prefix)
  2. Exact model_id match
  3. Built-in alias (this file)
  4. User-defined alias (~/.lumynax/aliases.toml)
  5. Unique substring match across all slugs
  6. Disambiguating prompt if multiple matches
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional
import os

# Built-in human-friendly short names. Keep these stable — users will script against them.
BUILTIN: dict[str, str] = {
    # ---- chat / general ----
    "hermes3":            "lumynax-chat-hermes-3-llama31-8b-gguf",
    "hermes":             "lumynax-chat-hermes-3-llama31-8b-gguf",
    "yi34":               "lumynax-chat-yi-15-34b-gguf",
    "yi":                 "lumynax-chat-yi-15-34b-gguf",
    # ---- frontier ----
    "qwen3-235":          "lumynax-frontier-qwen3-235b-a22b-instruct",
    "qwen3-frontier":     "lumynax-frontier-qwen3-235b-a22b-instruct",
    "qwen2.5-72":         "lumynax-frontier-qwen25-72b-instruct-gguf",
    "qwen72":             "lumynax-frontier-qwen25-72b-instruct-gguf",
    "minimax":            "lumynax-frontier-minimax-m2-230b",
    "minimax-m2":         "lumynax-frontier-minimax-m2-230b",
    "mixtral":            "lumynax-frontier-mixtral-8x22b-instruct-gguf",
    "dbrx":               "lumynax-frontier-dbrx-instruct-132b-gguf",
    "olmo32":             "lumynax-frontier-olmo2-32b-instruct",
    "olmo":               "lumynax-frontier-olmo2-32b-instruct",
    "phi4":               "lumynax-frontier-phi-4-14b-gguf",
    "phi-4":              "lumynax-frontier-phi-4-14b-gguf",
    "phi35-moe":          "lumynax-frontier-phi-35-moe-instruct-gguf",
    "glm46":              "lumynax-reasoning-glm46-355b-moe",
    "glm-4.6":            "lumynax-reasoning-glm46-355b-moe",
    # ---- coder ----
    "qwen3-coder":        "lumynax-frontier-coder-qwen3-480b-a35b-gguf",
    "qwen3-coder-480":    "lumynax-frontier-coder-qwen3-480b-a35b-gguf",
    "deepseek-v25":       "lumynax-frontier-coder-deepseek-v25-1210-gguf",
    "deepseek-coder":     "lumynax-coder-deepseek-coder-33b-gguf",
    "deepseek-coder-33":  "lumynax-coder-deepseek-coder-33b-gguf",
    "deepseek-coder-lite":"lumynax-coder-deepseek-v2-lite-16b-gguf",
    "deepseek":           "lumynax-coder-deepseek-v2-lite-16b-gguf",
    "qwen25-coder":       "lumynax-coder-qwen25-coder-32b-gguf",
    "qwen-coder":         "lumynax-coder-qwen25-coder-32b-gguf",
    "starcoder2":         "lumynax-coder-starcoder2-15b-gguf",
    "yi-coder":           "lumynax-coder-yi-coder-9b-gguf",
    "codellama":          "lumynax-coder-codellama-70b-instruct-gguf",
    "codellama70":        "lumynax-coder-codellama-70b-instruct-gguf",
    "codeqwen":           "lumynax-coder-codeqwen15-7b-chat-gguf",
    # ---- reasoning ----
    "r1":                 "lumynax-reasoning-deepseek-r1-distill-llama-70b-gguf",
    "r1-distill":         "lumynax-reasoning-deepseek-r1-distill-llama-70b-gguf",
    "qwq":                "lumynax-reasoning-qwq-32b-gguf",
    "qwq32":              "lumynax-reasoning-qwq-32b-gguf",
    "prover":             "lumynax-reasoning-deepseek-prover-v2-671b-gguf",
    "prover-v2":          "lumynax-reasoning-deepseek-prover-v2-671b-gguf",
    "gpt-oss":            "lumynax-reasoning-gpt-oss-20b-gguf",
    "math":               "lumynax-math-qwen25-math-7b-gguf",
    # ---- multimodal ----
    "qwen-vl":            "lumynax-multimodal-qwen25-vl-72b-instruct-gguf",
    "qwen25-vl":          "lumynax-multimodal-qwen25-vl-72b-instruct-gguf",
    "vision":             "lumynax-multimodal-qwen25-vl-72b-instruct-gguf",
    "internvl3":          "lumynax-multimodal-internvl3-78b-instruct",
    "pixtral":            "lumynax-multimodal-pixtral-large-124b",
    "llava":              "lumynax-multimodal-llava-next-34b",
    "aria":               "lumynax-multimodal-aria-25b-moe",
    "kimi-vl":            "lumynax-multimodal-kimi-vl-a3b-thinking",
    "glm46v":             "lumynax-multimodal-glm46v-flash",
    # ---- long context ----
    "1m":                 "lumynax-longctx-glm4-9b-chat-1m-gguf",
    "qwen-1m":            "lumynax-longctx-qwen25-7b-1m-gguf",
    "glm-1m":             "lumynax-longctx-glm4-9b-chat-1m-gguf",
    "yi-200k":            "lumynax-longctx-yi-9b-200k",
    "prolong":            "lumynax-longctx-prolong-512k-instruct",
    # ---- speech ----
    "whisper":            "lumynax-speech-whisper-large-v3-turbo",
    "asr":                "lumynax-speech-whisper-large-v3-turbo",
    "tts":                "lumynax-speech-kokoro-82m-tts",
    "kokoro":             "lumynax-speech-kokoro-82m-tts",
    "omni":               "lumynax-infused-qwen25-omni-7b-voice",
    # ---- retrieval ----
    "bge":                "lumynax-embed-bge-m3",
    "bge-m3":             "lumynax-embed-bge-m3",
    "embed":              "lumynax-embed-bge-m3",
    "nomic":              "lumynax-embed-nomic-v2-moe",
    "granite-embed":      "lumynax-embed-granite-278m-multilingual",
    "e5":                 "lumynax-embed-e5-mistral-7b",
    "rerank":             "lumynax-reranker-bge-v2-m3",
    "reranker":           "lumynax-reranker-bge-v2-m3",
    "moderation":         "lumynax-guard-text-moderation",
    "guard":              "lumynax-guard-text-moderation",
    # ---- translation ----
    "nllb":               "lumynax-translate-nllb-200-3b",
    "translate":          "lumynax-translate-nllb-200-3b",
    "te-reo":             "lumynax-translate-nllb-200-3b",
    # ---- document AI ----
    "nougat":             "lumynax-doc-nougat-base",
    "donut":              "lumynax-doc-donut-base",
    "ocr":                "lumynax-ocr-trocr-large-printed",
    "ocr-handwritten":    "lumynax-ocr-trocr-large-handwritten",
    "layout":             "lumynax-doc-layoutlmv3-base",
    "table":              "lumynax-doc-table-transformer-detection",
    # ---- tiny / nz / specialty ----
    "tiny":               "lumynax-tiny-qwen25-05b-gguf",
    "nz":                 "lumynax-nz-3b",
    "nz-coder":           "lumynax-nz-qwen25-coder-3b-gguf",
    "olmoe":              "lumynax-moe-olmoe-1b-7b-0924-instruct-gguf",
    "moonlight":          "lumynax-moe-moonlight-16b-a3b-gguf",
}


def user_aliases_path() -> Path:
    """`~/.lumynax/aliases.toml`."""
    return Path(os.environ.get("LUMYNAX_HOME", Path.home() / ".lumynax")) / "aliases.toml"


def load_user_aliases() -> dict[str, str]:
    p = user_aliases_path()
    if not p.exists(): return {}
    try:
        import tomllib  # 3.11+
        with p.open("rb") as f:
            data = tomllib.load(f)
        out = {}
        for k, v in (data.get("aliases") or {}).items():
            if isinstance(v, str): out[k.lower()] = v
        return out
    except Exception:
        return {}


def all_aliases() -> dict[str, str]:
    """Merged built-in + user, user wins on conflict."""
    out = dict(BUILTIN)
    out.update(load_user_aliases())
    return out


def resolve(query: str, all_slugs: Optional[list[str]] = None) -> tuple[Optional[str], list[str]]:
    """Resolve `query` to a slug. Returns (slug_or_None, ambiguous_matches).

    If ambiguous_matches is non-empty, the resolution was ambiguous and the
    caller should ask the user to disambiguate.
    """
    if not query: return None, []
    q = query.replace("AbteeXAILab/", "").strip().lower()

    # 1. exact slug
    if all_slugs:
        for s in all_slugs:
            if s.lower() == q: return s, []
        # 2. exact model_id (same as slug here since slug == model_id strictly)

    # 3. built-in / user alias
    aliases = all_aliases()
    if q in aliases:
        target = aliases[q]
        # If we know the slug list, verify the alias points to a real slug
        if all_slugs and target not in all_slugs:
            return None, []
        return target, []

    # 4. unique substring
    if all_slugs:
        hits = [s for s in all_slugs if q in s.lower()]
        if len(hits) == 1: return hits[0], []
        if len(hits) > 1:  return None, sorted(hits)

    return None, []


def add_alias(short: str, slug: str) -> None:
    """Persist a new alias to ~/.lumynax/aliases.toml."""
    p = user_aliases_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    existing = load_user_aliases()
    existing[short.lower()] = slug
    lines = ["[aliases]"]
    for k, v in sorted(existing.items()):
        lines.append(f'{k} = "{v}"')
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
