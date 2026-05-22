"""Renderers — pretty, json, slug, openai-stub, why-not, compare.

All take a Decision and return a string (or print to a rich Console)."""
from __future__ import annotations

import json
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich.syntax import Syntax

from .core import Decision, Rejection


# ---- pretty ----
def pretty(d: Decision, *, show_analysis: bool = True, show_rejected: int = 0) -> str:
    """Rich-formatted human output. Returns nothing — prints to a Console."""
    c = Console()
    if d.pick is None:
        c.print(Panel.fit(
            f"[red bold]NO CANDIDATE[/red bold]\n\nAll {d.n_candidates} models failed at least one gate.",
            title="MaramaRoute",
            border_style="red",
        ))
        if d.rejected:
            t = Table(title="Why each was rejected", show_lines=False)
            t.add_column("slug", style="cyan")
            t.add_column("gate", style="yellow")
            t.add_column("reason")
            for r in d.rejected[:show_rejected or 10]:
                t.add_row(r.repo_id.split("/")[-1], r.gate, r.reason)
            c.print(t)
        return ""

    p = d.pick
    tp = p.get("total_params_b"); ap = p.get("active_params_b")
    params = f"{tp}B" + (f" / {ap}Ba" if ap else "") if tp else "—"
    header = (
        f"[bold green]🎯 {p.get('title','')}\n"
        f"[cyan]{p['repo_id']}[/cyan]\n"
        f"score: [yellow]{d.score:.2f}[/yellow]   strategy: [magenta]{d.strategy.value}[/magenta]\n\n"
        f"params: {params}    ctx: {p.get('context_tokens')}    "
        f"modalities: {', '.join(p.get('modalities') or [])}    "
        f"sovereignty: tier {p.get('sovereignty_tier')}    license: {p.get('license_id')}"
    )
    c.print(Panel.fit(header, title="MaramaRoute pick", border_style="green"))

    if show_analysis and d.analysis and d.analysis.confidence > 0:
        a = d.analysis
        bits = []
        if a.is_code: bits.append(f"[cyan]code[/cyan]" + (f" ({', '.join(a.code_langs)})" if a.code_langs else ""))
        if a.is_math: bits.append("[cyan]math[/cyan]")
        if a.is_reasoning: bits.append("[cyan]reasoning[/cyan]")
        if a.is_translation: bits.append(f"[cyan]translate→{a.translate_target}[/cyan]")
        if a.contains_te_reo: bits.append("[magenta]te-reo[/magenta]")
        if a.needs_vision: bits.append("[cyan]vision[/cyan]")
        if a.needs_audio: bits.append("[cyan]audio[/cyan]")
        if a.is_long_context: bits.append(f"[cyan]long-context (~{a.estimated_tokens} tokens)[/cyan]")
        if a.needs_tools: bits.append("[cyan]tools[/cyan]")
        if a.needs_json: bits.append("[cyan]json[/cyan]")
        if bits:
            c.print(Panel.fit("Detected: " + " · ".join(bits) + f"\nConfidence: {a.confidence:.2f}",
                              title="Prompt analysis", border_style="yellow"))

    # Score breakdown
    if d.breakdown:
        t = Table(title="Score breakdown", show_lines=False)
        t.add_column("component", style="cyan")
        t.add_column("value", justify="right", style="white")
        for k, v in d.breakdown.components.items():
            t.add_row(k, f"{v:+.2f}")
        t.add_row("[bold]total[/bold]", f"[bold]{d.breakdown.total:.2f}[/bold]")
        if d.breakdown.matched_tags:
            t.caption = f"matched tags: {', '.join(d.breakdown.matched_tags)}"
        c.print(t)

    # Runners-up
    if d.runners_up:
        t = Table(title=f"Runners-up (next {len(d.runners_up)})", show_lines=False)
        t.add_column("slug", style="cyan")
        t.add_column("score", justify="right")
        t.add_column("matched tags")
        for r in d.runners_up:
            t.add_row(r.repo_id.split("/")[-1], f"{r.total:.2f}",
                      ", ".join(r.matched_tags) if r.matched_tags else "—")
        c.print(t)

    if show_rejected and d.rejected:
        t = Table(title=f"Sample rejections (first {show_rejected})", show_lines=False)
        t.add_column("slug", style="dim cyan")
        t.add_column("gate", style="yellow")
        t.add_column("reason", style="dim")
        for r in d.rejected[:show_rejected]:
            t.add_row(r.repo_id.split("/")[-1], r.gate, r.reason)
        c.print(t)
    return ""


# ---- JSON ----
def as_json(d: Decision) -> str:
    p = d.pick
    return json.dumps({
        "pick":  p["repo_id"].split("/")[-1] if p else None,
        "repo_id": p["repo_id"] if p else None,
        "score": d.score,
        "strategy": d.strategy.value,
        "n_candidates": d.n_candidates,
        "components": d.breakdown.components if d.breakdown else None,
        "matched_tags": d.breakdown.matched_tags if d.breakdown else [],
        "runners_up": [{"slug": r.repo_id.split("/")[-1], "score": r.total,
                         "matched_tags": r.matched_tags} for r in d.runners_up],
        "analysis": {
            "is_code": d.analysis.is_code if d.analysis else False,
            "is_math": d.analysis.is_math if d.analysis else False,
            "is_translation": d.analysis.is_translation if d.analysis else False,
            "translate_target": d.analysis.translate_target if d.analysis else None,
            "contains_te_reo": d.analysis.contains_te_reo if d.analysis else False,
            "needs_vision": d.analysis.needs_vision if d.analysis else False,
            "needs_audio": d.analysis.needs_audio if d.analysis else False,
            "is_long_context": d.analysis.is_long_context if d.analysis else False,
            "code_langs": d.analysis.code_langs if d.analysis else [],
            "estimated_tokens": d.analysis.estimated_tokens if d.analysis else 0,
            "confidence": d.analysis.confidence if d.analysis else 0.0,
            "task_tags": d.analysis.task_tags() if d.analysis else [],
        },
        "rejected_count_by_gate": _count_gates(d.rejected),
    }, indent=2)


def _count_gates(rs: list[Rejection]) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in rs: out[r.gate] = out.get(r.gate, 0) + 1
    return out


# ---- slug (pipeable) ----
def slug_only(d: Decision) -> str:
    return d.slug or ""


# ---- OpenAI stub for piping into curl ----
def openai_stub(d: Decision, gateway_url: str = "http://localhost:8080/v1") -> str:
    if not d.slug: return "# no pick"
    return f'''curl -fsS {gateway_url}/chat/completions \\
  -H "Authorization: Bearer $LUMYNAX_KEY" -H "Content-Type: application/json" \\
  -d '{{"model":"{d.slug}","messages":[{{"role":"user","content":"YOUR PROMPT HERE"}}]}}' '''


# ---- why-not specific slug ----
def why_not(d: Decision, target_slug: str) -> str:
    target_slug = target_slug.replace("AbteeXAILab/", "")
    full = f"AbteeXAILab/{target_slug}"
    for r in d.rejected:
        if r.repo_id == full:
            return f"❌ {target_slug} was rejected at gate '{r.gate}': {r.reason}"
    # It might have been picked, or be a runner-up
    if d.pick and d.pick["repo_id"] == full:
        return f"✅ {target_slug} WAS picked (score {d.score:.2f})"
    for r in d.runners_up:
        if r.repo_id == full:
            place = d.runners_up.index(r) + 2  # 1-indexed, after pick
            return f"🥈 {target_slug} survived all gates but was rank {place} (score {r.total:.2f} vs pick {d.score:.2f})"
    return f"⚠️ {target_slug} was not even in the candidate pool. Did you misspell the slug?"


# ---- compare top-N ----
def compare_top(d: Decision, n: int = 3) -> str:
    c = Console()
    rows = [d.breakdown] + d.runners_up if d.breakdown else d.runners_up
    rows = rows[:n]
    if not rows:
        return ""
    t = Table(title=f"Top {len(rows)} candidates — strategy {d.strategy.value}", show_lines=True)
    t.add_column("rank", justify="right", style="bold")
    t.add_column("slug", style="cyan")
    t.add_column("total", justify="right", style="green")
    for k in (d.breakdown.components if d.breakdown else {}).keys():
        t.add_column(k, justify="right", style="dim")
    t.add_column("matched", style="magenta")
    for i, r in enumerate(rows, 1):
        row = [str(i), r.repo_id.split("/")[-1], f"{r.total:.2f}"]
        for k in r.components:
            row.append(f"{r.components[k]:+.2f}")
        row.append(", ".join(r.matched_tags) if r.matched_tags else "—")
        t.add_row(*row)
    c.print(t)
    return ""
