"""Deterministic sovereign router.

Filters and scores LumynaX registry entries against a request, with explicit
rejection reasons for traceability.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None


@dataclass
class RouteDecision:
    selected: Optional[Dict[str, Any]]
    fallbacks: List[Dict[str, Any]] = field(default_factory=list)
    rejected: List[Dict[str, Any]] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "selected": self.selected,
            "fallbacks": self.fallbacks,
            "rejected": self.rejected,
            "reasons": list(self.reasons),
        }


def _load(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml", ".yml"):
        if yaml is None:
            raise RuntimeError("pyyaml is required to load YAML policies. `pip install pyyaml`.")
        return yaml.safe_load(text)
    return json.loads(text)


def load_registry(path: str | Path) -> Dict[str, Any]:
    return _load(Path(path))


def load_request(path: str | Path) -> Dict[str, Any]:
    return _load(Path(path))


def load_policy(path: str | Path) -> Dict[str, Any]:
    return _load(Path(path))


_TASK_TO_TAGS = {
    "code": {"coder", "code"},
    "reasoning": {"reasoning"},
    "multimodal": {"multimodal", "image", "audio", "voice", "vision"},
    "embedding": {"embedding", "embed", "retrieval"},
    "chat": {"general", "instruct"},
}


def _filter(model: Dict[str, Any], request: Dict[str, Any]) -> Optional[str]:
    """Return a rejection reason, or None if model is a candidate."""
    req_modalities = set(request.get("modalities", []))
    mod = set(model.get("modalities", []))
    if req_modalities and not req_modalities.issubset(mod):
        return f"modalities missing: needs {sorted(req_modalities)}, has {sorted(mod)}"

    min_ctx = request.get("min_context_tokens")
    if min_ctx and (model.get("context_tokens") or 0) < min_ctx:
        return f"context_tokens {model.get('context_tokens')} < required {min_ctx}"

    jurisdiction = request.get("jurisdiction")
    if jurisdiction and jurisdiction not in (model.get("residency") or []):
        return f"residency {model.get('residency')} does not include {jurisdiction}"

    if request.get("requires_local") and model.get("runtime") not in (
        "llama_cpp",
        "llama_cpp_multimodal",
        "transformers",
        "transformers_multimodal",
        "python_embedding",
    ):
        return f"requires_local but runtime is {model.get('runtime')}"

    if request.get("requires_tools") and not model.get("supports_tools", False):
        return "supports_tools = false"
    if request.get("requires_json") and not model.get("supports_json", False):
        return "supports_json = false"

    sensitivity = str(request.get("data_sensitivity", "")).lower()
    if sensitivity in ("restricted", "personal", "health", "iwi", "taonga"):
        if (model.get("sovereignty_tier") or 0) < 2:
            return f"sovereignty_tier {model.get('sovereignty_tier')} < 2 for sensitive data"

    return None


def _score(model: Dict[str, Any], request: Dict[str, Any]) -> float:
    quality = 6 - int(model.get("quality_rank") or 6)
    cost = 6 - int(model.get("cost_rank") or 6)
    sov = int(model.get("sovereignty_tier") or 0)
    active = float(model.get("active_params_b") or model.get("total_params_b") or 0)
    base = 2.0 * quality + 1.5 * sov + 0.5 * cost
    task = str(request.get("task_type", "")).lower()
    wanted = _TASK_TO_TAGS.get(task, set())
    tags = set(model.get("tags") or [])
    if wanted & tags:
        base += 3.0
    if request.get("requires_local") and model.get("runtime") == "llama_cpp":
        base += 1.0
    if active and active > 50:
        base -= 0.5
    return round(base, 3)


def route(registry: Dict[str, Any], request: Dict[str, Any], policy: Optional[Dict[str, Any]] = None) -> RouteDecision:
    reasons: List[str] = []
    candidates: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []

    for m in registry.get("models", []):
        reject = _filter(m, request)
        if reject:
            rejected.append({"repo_id": m.get("repo_id"), "reason": reject})
        else:
            candidates.append({**m, "_score": _score(m, request)})

    candidates.sort(key=lambda x: x["_score"], reverse=True)
    max_fallbacks = int(request.get("max_fallbacks", 3))
    if not candidates:
        reasons.append("no candidate satisfies the gates")
        return RouteDecision(selected=None, fallbacks=[], rejected=rejected, reasons=reasons)

    selected = candidates[0]
    fallbacks = candidates[1 : 1 + max_fallbacks]
    reasons.append(f"selected {selected['repo_id']} with score {selected['_score']}")
    reasons.append(f"{len(candidates) - 1} fallback candidates available, returning top {len(fallbacks)}")
    return RouteDecision(selected=selected, fallbacks=fallbacks, rejected=rejected, reasons=reasons)
