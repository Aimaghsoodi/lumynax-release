"""Router core — turns (prompt + filters + strategy) into a Decision.

Six gates run in order on every candidate. Each gate that rejects a model
records WHY. The Router returns a Decision with the pick, score breakdown,
ranked alternates, and a full rejection ledger.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Optional

from .analyze import PromptAnalysis, analyze


class Strategy(str, Enum):
    """Preset weight bundles for scoring."""
    BALANCED  = "balanced"
    CHEAP     = "cheap"          # heavy cost penalty, smaller models
    FRONTIER  = "frontier"       # quality > everything
    LOCAL     = "local-only"     # sovereignty tier ≥ 4 mandatory
    CODER     = "coder"          # bias toward coder family + tool support
    VISION    = "vision"         # bias toward multimodal
    REASONING = "reasoning"      # bias toward QwQ / Prover / R1 / Phi-3.5-MoE
    TE_REO    = "te-reo"         # bias toward NLLB + GLM-4 / Qwen 1M


# Strategy → score-weight overrides
_WEIGHTS: dict[Strategy, dict[str, float]] = {
    Strategy.BALANCED:  {"quality": 2.0, "sovereignty": 1.5, "cost": 0.5, "task_match": 3.0},
    Strategy.CHEAP:     {"quality": 1.0, "sovereignty": 1.0, "cost": 3.0, "task_match": 2.0},
    Strategy.FRONTIER:  {"quality": 4.0, "sovereignty": 0.5, "cost": 0.1, "task_match": 2.0},
    Strategy.LOCAL:     {"quality": 1.5, "sovereignty": 4.0, "cost": 0.5, "task_match": 3.0},
    Strategy.CODER:     {"quality": 2.5, "sovereignty": 1.0, "cost": 0.5, "task_match": 5.0},
    Strategy.VISION:    {"quality": 2.5, "sovereignty": 1.0, "cost": 0.5, "task_match": 5.0},
    Strategy.REASONING: {"quality": 3.0, "sovereignty": 1.0, "cost": 0.3, "task_match": 5.0},
    Strategy.TE_REO:    {"quality": 2.0, "sovereignty": 2.0, "cost": 0.5, "task_match": 5.0},
}


@dataclass
class Rejection:
    repo_id: str
    gate: str
    reason: str


@dataclass
class ScoreBreakdown:
    repo_id: str
    title: str
    total: float
    components: dict[str, float]
    matched_tags: list[str]


@dataclass
class Decision:
    pick: Optional[dict] = None
    score: float = 0.0
    breakdown: Optional[ScoreBreakdown] = None
    runners_up: list[ScoreBreakdown] = field(default_factory=list)
    rejected: list[Rejection] = field(default_factory=list)
    analysis: Optional[PromptAnalysis] = None
    strategy: Strategy = Strategy.BALANCED
    n_candidates: int = 0

    @property
    def slug(self) -> Optional[str]:
        if self.pick is None: return None
        return self.pick["repo_id"].split("/")[-1]


@dataclass
class Router:
    """Stateless router. Pass in the model list once; call .route(prompt, ...) many times."""
    models: list[dict]
    weights: Optional[dict[str, float]] = None

    def route(self,
              prompt: str = "",
              modalities: Optional[list[str]] = None,
              requires_local: bool = False,
              requires_tools: Optional[bool] = None,
              requires_json: Optional[bool] = None,
              jurisdiction: str = "NZ",
              max_params_b: float = 0.0,
              min_context: int = 0,
              strategy: Strategy = Strategy.BALANCED,
              task_hint: str = "",
              prefer_family: Optional[str] = None,
              forbid_slugs: Optional[list[str]] = None) -> Decision:
        analysis = analyze(prompt) if prompt else PromptAnalysis()
        d = Decision(analysis=analysis, strategy=strategy)

        # Strategy → modality / requirement upgrades from prompt analysis
        mods = set(modalities or ["text"])
        if analysis.needs_vision: mods.add("vision")
        if analysis.needs_audio:  mods.add("audio")

        if requires_tools is None:
            requires_tools = analysis.needs_tools
        if requires_json is None:
            requires_json  = analysis.needs_json

        if strategy == Strategy.LOCAL:
            requires_local = True

        # Long-context auto-bump
        ctx_needed = max(min_context, analysis.estimated_tokens * 2 if analysis.is_long_context else min_context)

        # Per-strategy task tag boost set
        task_tags = set(analysis.task_tags())
        if task_hint: task_tags.add(task_hint.lower())
        if strategy == Strategy.CODER:     task_tags.add("coder")
        if strategy == Strategy.VISION:    task_tags.add("vision")
        if strategy == Strategy.REASONING: task_tags.add("reasoning")
        if strategy == Strategy.TE_REO:    task_tags.update({"te-reo","translate","long-context"})

        weights = self.weights or _WEIGHTS[strategy]
        forbid = set(forbid_slugs or [])

        candidates: list[ScoreBreakdown] = []

        for m in self.models:
            slug = m["repo_id"].split("/")[-1]

            # ---- Gate 1: explicit forbid ----
            if slug in forbid:
                d.rejected.append(Rejection(m["repo_id"], "forbid", "explicitly forbidden")); continue

            # ---- Gate 2: modality ----
            mods_have = set(m.get("modalities") or [])
            missing = [x for x in mods if x not in mods_have]
            if missing:
                d.rejected.append(Rejection(m["repo_id"], "modality", f"missing {missing}")); continue

            # ---- Gate 3: sovereignty / jurisdiction ----
            tier = int(m.get("sovereignty_tier") or 5)
            if requires_local and tier < 3:
                d.rejected.append(Rejection(m["repo_id"], "sovereignty", f"tier={tier} < required local")); continue
            residency = m.get("residency") or []
            if jurisdiction and jurisdiction not in residency:
                d.rejected.append(Rejection(m["repo_id"], "residency", f"residency={residency} excludes {jurisdiction}")); continue

            # ---- Gate 4: capability requirements ----
            if requires_tools and not m.get("supports_tools"):
                d.rejected.append(Rejection(m["repo_id"], "capability", "no tools")); continue
            if requires_json and not m.get("supports_json"):
                d.rejected.append(Rejection(m["repo_id"], "capability", "no json")); continue
            if ctx_needed and (m.get("context_tokens") or 0) < ctx_needed:
                d.rejected.append(Rejection(m["repo_id"], "context", f"ctx={m.get('context_tokens')} < {ctx_needed}")); continue
            if max_params_b > 0 and (m.get("total_params_b") or 0) > max_params_b:
                d.rejected.append(Rejection(m["repo_id"], "size", f"params={m.get('total_params_b')}B > {max_params_b}B")); continue

            # ---- Gate 5: prefer-family soft filter ----
            if prefer_family and prefer_family.lower() not in (m.get("family") or "").lower():
                # not a hard reject; soft penalty applied in scoring
                pass

            # ---- Gate 6: scoring ----
            q  = int(m.get("quality_rank")    or 5)   # 1=best, 5=worst
            s  = int(m.get("sovereignty_tier") or 3)  # higher = more sovereign
            c  = int(m.get("cost_rank")        or 5)  # 1=cheapest, 5=priciest

            comp_q = (6 - q) * weights["quality"]
            comp_s = s * weights["sovereignty"]
            comp_c = (6 - c) * weights["cost"]

            # task-tag match bonus
            model_tags = set((t.lower() for t in (m.get("tags") or [])))
            model_tags |= set(m["model_id"].lower().split("-"))
            matched = sorted(task_tags & model_tags)
            comp_task = len(matched) * weights["task_match"]

            # Bonus: context headroom — if asked is well under model's capacity, small reward
            ctx_headroom = (m.get("context_tokens") or 4096) / max(ctx_needed, 4096)
            comp_ctx = min(2.0, math.log2(max(ctx_headroom, 1.0)))

            # Bonus: family preference
            comp_fam = 0.0
            if prefer_family and prefer_family.lower() in (m.get("family") or "").lower():
                comp_fam = 2.0

            # Penalty: oversized for cheap strategy
            comp_size_pen = 0.0
            if strategy == Strategy.CHEAP and (m.get("total_params_b") or 0) > 20:
                comp_size_pen = -(math.log10((m.get("total_params_b") or 1)) - 1)  # ≈ −0.3 for 30B, −1 for 200B

            total = comp_q + comp_s + comp_c + comp_task + comp_ctx + comp_fam + comp_size_pen

            candidates.append(ScoreBreakdown(
                repo_id=m["repo_id"],
                title=m.get("title") or slug,
                total=round(total, 3),
                components={
                    "quality":     round(comp_q, 2),
                    "sovereignty": round(comp_s, 2),
                    "cost":        round(comp_c, 2),
                    "task_match":  round(comp_task, 2),
                    "ctx_headroom": round(comp_ctx, 2),
                    "family":      round(comp_fam, 2),
                    "size_penalty": round(comp_size_pen, 2),
                },
                matched_tags=matched,
            ))

        candidates.sort(key=lambda x: -x.total)
        d.n_candidates = len(candidates) + len(d.rejected)
        if candidates:
            top = candidates[0]
            d.breakdown = top
            d.score = top.total
            d.pick = next(m for m in self.models if m["repo_id"] == top.repo_id)
            d.runners_up = candidates[1:6]
        return d
