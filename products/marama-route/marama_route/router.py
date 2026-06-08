from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .registry import ModelEndpoint, RoutingRequest

HIGH_SENSITIVITY = frozenset({"personal", "restricted", "health", "iwi", "taonga"})


@dataclass(frozen=True, slots=True)
class RouteDecision:
    selected_model: ModelEndpoint | None
    fallback_models: tuple[ModelEndpoint, ...]
    rejected: tuple[dict[str, str], ...]
    reasons: tuple[str, ...]
    scores: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_model": self.selected_model.to_dict() if self.selected_model else None,
            "fallback_models": [model.to_dict() for model in self.fallback_models],
            "rejected": list(self.rejected),
            "reasons": list(self.reasons),
            "scores": dict(self.scores),
        }


class SovereignModelRouter:
    def __init__(self, models: tuple[ModelEndpoint, ...]) -> None:
        self.models = models

    def route(self, request: RoutingRequest) -> RouteDecision:
        accepted: list[ModelEndpoint] = []
        rejected: list[dict[str, str]] = []
        requested_modalities = set(request.modalities)
        license_allowlist = set(request.license_allowlist)

        for model in self.models:
            model_modalities = set(item.lower() for item in model.modalities)
            if not requested_modalities.issubset(model_modalities):
                rejected.append({"model_id": model.model_id, "reason": "modality_mismatch"})
                continue
            if model.context_tokens < request.min_context_tokens:
                rejected.append({"model_id": model.model_id, "reason": "context_too_small"})
                continue
            if request.requires_tools and not model.supports_tools:
                rejected.append({"model_id": model.model_id, "reason": "tools_required"})
                continue
            if request.requires_json and not model.supports_json:
                rejected.append({"model_id": model.model_id, "reason": "json_required"})
                continue
            if license_allowlist and model.license_id.lower() not in license_allowlist:
                rejected.append({"model_id": model.model_id, "reason": "license_not_allowed"})
                continue
            if request.requires_local and request.jurisdiction not in model.residency:
                rejected.append({"model_id": model.model_id, "reason": "residency_mismatch"})
                continue
            if request.data_sensitivity in HIGH_SENSITIVITY and model.sovereignty_tier < 2:
                rejected.append({"model_id": model.model_id, "reason": "sovereignty_tier_too_low"})
                continue
            accepted.append(model)

        scores = {model.model_id: self._score(model, request) for model in accepted}
        ranked = tuple(sorted(accepted, key=lambda model: (scores[model.model_id], model.model_id), reverse=True))
        selected = ranked[0] if ranked else None
        fallbacks = ranked[1 : 1 + request.max_fallbacks]
        reasons = self._reasons(selected, request)
        return RouteDecision(
            selected_model=selected,
            fallback_models=fallbacks,
            rejected=tuple(rejected),
            reasons=reasons,
            scores=scores,
        )

    def _score(self, model: ModelEndpoint, request: RoutingRequest) -> float:
        score = 0.0
        tags = set(model.tags)
        prompt_lower = request.prompt.lower()
        if request.jurisdiction in model.residency:
            score += 8.0
        if request.task_type in tags or request.task_type in model.family.lower():
            score += 7.0
        if request.task_type == "code" and ("coder" in model.model_id or "coder" in tags):
            score += 10.0
        if request.task_type == "reasoning" and ("reasoning" in model.model_id or "reasoning" in tags):
            score += 9.0
        if "iwi" in prompt_lower or "data sovereignty" in prompt_lower:
            score += 3.0 * model.sovereignty_tier
        if "gguf" in model.runtime.lower() or model.runtime == "llama_cpp":
            score += 2.5
        if model.supports_json and request.requires_json:
            score += 3.0
        if model.supports_tools and request.requires_tools:
            score += 3.0
        score += max(0, 10 - model.quality_rank) * 1.7
        score -= model.cost_rank * 0.25
        if model.active_params_b is not None and model.active_params_b <= 8:
            score += 0.5
        return round(score, 4)

    def _reasons(self, selected: ModelEndpoint | None, request: RoutingRequest) -> tuple[str, ...]:
        if selected is None:
            return ("no model satisfied sovereignty and capability constraints",)
        reasons = [
            f"selected `{selected.model_id}` for task_type `{request.task_type}`",
            f"residency `{request.jurisdiction}` satisfied",
            f"runtime `{selected.runtime}`",
        ]
        if request.data_sensitivity in HIGH_SENSITIVITY:
            reasons.append("high-sensitivity routing kept inside sovereign tier constraints")
        return tuple(reasons)
