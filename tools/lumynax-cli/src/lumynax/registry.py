"""Load the LumynaX model registry from Hugging Face."""
from __future__ import annotations
import json, os
from pathlib import Path
from typing import Any
from huggingface_hub import hf_hub_download

from . import REGISTRY_REPO, REGISTRY_PATH

_CACHE: dict[str, Any] | None = None


def load(force_refresh: bool = False) -> dict[str, Any]:
    """Fetch the registry. Cached in-process; cached on-disk via hf cache."""
    global _CACHE
    if _CACHE is not None and not force_refresh:
        return _CACHE
    path = hf_hub_download(
        repo_id=REGISTRY_REPO,
        filename=REGISTRY_PATH,
        repo_type="model",
        force_download=force_refresh,
        token=os.environ.get("HF_TOKEN"),
    )
    _CACHE = json.loads(Path(path).read_text(encoding="utf-8"))
    return _CACHE


def models() -> list[dict[str, Any]]:
    return load()["models"]


def find(model_id: str) -> dict[str, Any] | None:
    """Look up a model by slug (with or without 'AbteeXAILab/' prefix, exact or substring match)."""
    target = model_id.replace("AbteeXAILab/", "").lower()
    for m in models():
        slug = m["repo_id"].split("/")[-1].lower()
        if slug == target or m["model_id"].lower() == target:
            return m
    # substring fallback
    matches = [m for m in models() if target in m["model_id"].lower()]
    if len(matches) == 1:
        return matches[0]
    return None


def filter_by(tier: str | None = None, modality: str | None = None,
              max_params_b: float | None = None, supports_tools: bool | None = None,
              jurisdiction: str | None = None) -> list[dict[str, Any]]:
    out = []
    for m in models():
        if tier and tier not in m["model_id"]:
            continue
        if modality and modality not in (m.get("modalities") or []):
            continue
        if max_params_b is not None and (m.get("total_params_b") or 0) > max_params_b:
            continue
        if supports_tools is not None and bool(m.get("supports_tools")) != supports_tools:
            continue
        if jurisdiction and jurisdiction not in (m.get("residency") or []):
            continue
        out.append(m)
    return out
