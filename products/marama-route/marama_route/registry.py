from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _text_tuple(value: object, *, default: tuple[str, ...] = ()) -> tuple[str, ...]:
    if value in (None, ""):
        return default
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (list, tuple, set)):
        return tuple(str(item).strip() for item in value if str(item).strip())
    return (str(value).strip(),)


@dataclass(frozen=True, slots=True)
class ModelEndpoint:
    model_id: str
    repo_id: str
    family: str
    runtime: str
    modalities: tuple[str, ...] = ("text",)
    context_tokens: int = 4096
    jurisdiction: str = "NZ"
    residency: tuple[str, ...] = ("NZ",)
    license_id: str = "see_model_card"
    quantization: str = "see_manifest"
    primary_artifact: str = ""
    active_params_b: float | None = None
    total_params_b: float | None = None
    quality_rank: int = 5
    cost_rank: int = 5
    sovereignty_tier: int = 2
    supports_tools: bool = False
    supports_json: bool = False
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> ModelEndpoint:
        return cls(
            model_id=str(payload.get("model_id") or payload.get("repo_id") or ""),
            repo_id=str(payload.get("repo_id") or payload.get("model_id") or ""),
            family=str(payload.get("family") or "lumynax"),
            runtime=str(payload.get("runtime") or "llama_cpp"),
            modalities=_text_tuple(payload.get("modalities"), default=("text",)),
            context_tokens=int(payload.get("context_tokens") or 4096),
            jurisdiction=str(payload.get("jurisdiction") or "NZ").upper(),
            residency=tuple(str(item).upper() for item in _text_tuple(payload.get("residency"), default=("NZ",))),
            license_id=str(payload.get("license_id") or "see_model_card"),
            quantization=str(payload.get("quantization") or "see_manifest"),
            primary_artifact=str(payload.get("primary_artifact") or ""),
            active_params_b=(
                float(payload["active_params_b"]) if payload.get("active_params_b") is not None else None
            ),
            total_params_b=(
                float(payload["total_params_b"]) if payload.get("total_params_b") is not None else None
            ),
            quality_rank=int(payload.get("quality_rank") or 5),
            cost_rank=int(payload.get("cost_rank") or 5),
            sovereignty_tier=int(payload.get("sovereignty_tier") or 2),
            supports_tools=bool(payload.get("supports_tools", False)),
            supports_json=bool(payload.get("supports_json", False)),
            tags=tuple(item.lower() for item in _text_tuple(payload.get("tags"))),
            metadata=dict(payload.get("metadata") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "repo_id": self.repo_id,
            "family": self.family,
            "runtime": self.runtime,
            "modalities": list(self.modalities),
            "context_tokens": self.context_tokens,
            "jurisdiction": self.jurisdiction,
            "residency": list(self.residency),
            "license_id": self.license_id,
            "quantization": self.quantization,
            "primary_artifact": self.primary_artifact,
            "active_params_b": self.active_params_b,
            "total_params_b": self.total_params_b,
            "quality_rank": self.quality_rank,
            "cost_rank": self.cost_rank,
            "sovereignty_tier": self.sovereignty_tier,
            "supports_tools": self.supports_tools,
            "supports_json": self.supports_json,
            "tags": list(self.tags),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class RoutingRequest:
    prompt: str
    task_type: str = "general"
    modalities: tuple[str, ...] = ("text",)
    jurisdiction: str = "NZ"
    data_sensitivity: str = "internal"
    min_context_tokens: int = 4096
    requires_local: bool = True
    requires_tools: bool = False
    requires_json: bool = False
    license_allowlist: tuple[str, ...] = ()
    max_fallbacks: int = 3
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> RoutingRequest:
        return cls(
            prompt=str(payload.get("prompt") or ""),
            task_type=str(payload.get("task_type") or "general").lower(),
            modalities=tuple(item.lower() for item in _text_tuple(payload.get("modalities"), default=("text",))),
            jurisdiction=str(payload.get("jurisdiction") or "NZ").upper(),
            data_sensitivity=str(payload.get("data_sensitivity") or "internal").lower(),
            min_context_tokens=int(payload.get("min_context_tokens") or 4096),
            requires_local=bool(payload.get("requires_local", True)),
            requires_tools=bool(payload.get("requires_tools", False)),
            requires_json=bool(payload.get("requires_json", False)),
            license_allowlist=tuple(item.lower() for item in _text_tuple(payload.get("license_allowlist"))),
            max_fallbacks=int(payload.get("max_fallbacks") or 3),
            metadata=dict(payload.get("metadata") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt": self.prompt,
            "task_type": self.task_type,
            "modalities": list(self.modalities),
            "jurisdiction": self.jurisdiction,
            "data_sensitivity": self.data_sensitivity,
            "min_context_tokens": self.min_context_tokens,
            "requires_local": self.requires_local,
            "requires_tools": self.requires_tools,
            "requires_json": self.requires_json,
            "license_allowlist": list(self.license_allowlist),
            "max_fallbacks": self.max_fallbacks,
            "metadata": dict(self.metadata),
        }


def load_model_registry(path: Path) -> tuple[ModelEndpoint, ...]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    raw_models = payload.get("models") if isinstance(payload, dict) else payload
    if not isinstance(raw_models, list):
        raise ValueError(f"Expected model list in {path}")
    return tuple(ModelEndpoint.from_payload(item) for item in raw_models if isinstance(item, dict))
