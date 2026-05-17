"""MaramaRoute Live — interactive sovereign router demo (v2 polish)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import gradio as gr
from huggingface_hub import hf_hub_download


# ---------- Embedded router ----------
@dataclass
class RouteDecision:
    selected: Optional[Dict[str, Any]]
    fallbacks: List[Dict[str, Any]] = field(default_factory=list)
    rejected: List[Dict[str, Any]] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"selected": self.selected, "fallbacks": self.fallbacks, "rejected": self.rejected, "reasons": self.reasons}


_TASK_TO_TAGS = {
    "code": {"coder", "code"}, "reasoning": {"reasoning"},
    "multimodal": {"multimodal", "image", "audio", "voice", "vision"},
    "embedding": {"embedding", "embed", "retrieval"}, "chat": {"general", "instruct"},
}


def _filter(model: Dict[str, Any], request: Dict[str, Any]) -> Optional[str]:
    req_mod = set(request.get("modalities", []))
    mod = set(model.get("modalities", []))
    if req_mod and not req_mod.issubset(mod):
        return f"modalities missing: needs {sorted(req_mod)}, has {sorted(mod)}"
    if request.get("min_context_tokens") and (model.get("context_tokens") or 0) < request["min_context_tokens"]:
        return f"context_tokens {model.get('context_tokens')} < required {request['min_context_tokens']}"
    if request.get("jurisdiction") and request["jurisdiction"] not in (model.get("residency") or []):
        return f"residency {model.get('residency')} does not include {request['jurisdiction']}"
    if request.get("requires_local") and model.get("runtime") not in ("llama_cpp", "llama_cpp_multimodal", "transformers", "transformers_multimodal", "python_embedding"):
        return f"requires_local but runtime is {model.get('runtime')}"
    if request.get("requires_tools") and not model.get("supports_tools", False):
        return "supports_tools = false"
    if request.get("requires_json") and not model.get("supports_json", False):
        return "supports_json = false"
    if str(request.get("data_sensitivity", "")).lower() in ("restricted", "personal", "health", "iwi", "taonga"):
        if (model.get("sovereignty_tier") or 0) < 2:
            return f"sovereignty_tier {model.get('sovereignty_tier')} < 2 for sensitive data"
    return None


def _score(model: Dict[str, Any], request: Dict[str, Any]) -> float:
    q = 6 - int(model.get("quality_rank") or 6)
    c = 6 - int(model.get("cost_rank") or 6)
    s = int(model.get("sovereignty_tier") or 0)
    active = float(model.get("active_params_b") or model.get("total_params_b") or 0)
    base = 2.0 * q + 1.5 * s + 0.5 * c
    wanted = _TASK_TO_TAGS.get(str(request.get("task_type", "")).lower(), set())
    if wanted & set(model.get("tags") or []):
        base += 3.0
    if request.get("requires_local") and model.get("runtime") == "llama_cpp":
        base += 1.0
    if active and active > 50:
        base -= 0.5
    return round(base, 3)


def route(registry: Dict[str, Any], request: Dict[str, Any]) -> RouteDecision:
    candidates, rejected = [], []
    for m in registry.get("models", []):
        why = _filter(m, request)
        if why:
            rejected.append({"repo_id": m.get("repo_id"), "reason": why})
        else:
            candidates.append({**m, "_score": _score(m, request)})
    candidates.sort(key=lambda x: x["_score"], reverse=True)
    if not candidates:
        return RouteDecision(None, [], rejected, ["no candidate satisfies the gates"])
    sel = candidates[0]
    max_fb = int(request.get("max_fallbacks", 3))
    return RouteDecision(sel, candidates[1 : 1 + max_fb], rejected, [f"selected {sel['repo_id']} (score {sel['_score']})"])


REGISTRY_PATH = Path(__file__).parent / "lumynax_model_registry.json"


def load_registry() -> Dict[str, Any]:
    if REGISTRY_PATH.exists():
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    path = hf_hub_download(repo_id="AbteeXAILab/marama-route", filename="configs/lumynax_model_registry.json", repo_type="model")
    return json.loads(Path(path).read_text(encoding="utf-8"))


REGISTRY = load_registry()
MODEL_COUNT = len(REGISTRY.get("models", []))


EXAMPLE_CODE = {
    "prompt": "Refactor this private Python service and explain the diff.",
    "task_type": "code", "modalities": ["text"], "jurisdiction": "NZ",
    "data_sensitivity": "restricted", "min_context_tokens": 4096,
    "requires_local": True, "requires_tools": False, "requires_json": True, "max_fallbacks": 3,
}
EXAMPLE_REASON = {
    "prompt": "Plan a multi-step migration of a legacy data pipeline.",
    "task_type": "reasoning", "modalities": ["text"], "jurisdiction": "NZ",
    "data_sensitivity": "restricted", "min_context_tokens": 8192,
    "requires_local": True, "requires_tools": True, "requires_json": True, "max_fallbacks": 3,
}
EXAMPLE_MULTIMODAL = {
    "prompt": "Describe this image and draft a short public caption.",
    "task_type": "multimodal", "modalities": ["text", "image"], "jurisdiction": "NZ",
    "data_sensitivity": "public", "min_context_tokens": 4096,
    "requires_local": False, "requires_tools": False, "requires_json": False, "max_fallbacks": 3,
}
EXAMPLE_EMBEDDING = {
    "prompt": "Index our internal policy corpus.",
    "task_type": "embedding", "modalities": ["text"], "jurisdiction": "NZ",
    "data_sensitivity": "restricted", "min_context_tokens": 4096,
    "requires_local": True, "max_fallbacks": 3,
}
EXAMPLE_TINY = {
    "prompt": "Smoke test on a low-spec laptop.",
    "task_type": "chat", "modalities": ["text"], "jurisdiction": "NZ",
    "data_sensitivity": "public", "min_context_tokens": 2048,
    "requires_local": True, "requires_json": False, "max_fallbacks": 3,
}


HERO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 220" role="img" aria-label="MaramaRoute architecture">
  <defs><marker id="ar2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="#e08a2c"/></marker></defs>
  <rect width="1280" height="220" fill="#fffefa"/>
  <rect x="0" y="0" width="1280" height="3" fill="#0a0a0b"/>
  <text x="64" y="32" font-family="ui-monospace,Menlo,Consolas,monospace" font-size="11" font-weight="700" letter-spacing="0.2em" fill="#9a5416">MARAMAROUTE · SIX-GATE SOVEREIGN ROUTER</text>
  <g font-family="ui-monospace,Menlo,Consolas,monospace" font-size="11" font-weight="700" letter-spacing="0.14em" fill="#fff7ed" text-anchor="middle">
    <g transform="translate(60,80)"><rect width="170" height="80" rx="12" ry="12" fill="#e08a2c" stroke="#9a5416" stroke-width="1.4"/><text x="85" y="36" font-family="Georgia,serif" font-size="18" font-weight="500" fill="#0a0a0b">Capability</text><text x="85" y="60">MODE · CTX · JSON</text></g>
    <g transform="translate(255,80)"><rect width="170" height="80" rx="12" ry="12" fill="#e08a2c" stroke="#9a5416" stroke-width="1.4"/><text x="85" y="36" font-family="Georgia,serif" font-size="18" font-weight="500" fill="#0a0a0b">Sovereignty</text><text x="85" y="60">RESIDENCY · TIER</text></g>
    <g transform="translate(450,80)"><rect width="170" height="80" rx="12" ry="12" fill="#e08a2c" stroke="#9a5416" stroke-width="1.4"/><text x="85" y="36" font-family="Georgia,serif" font-size="18" font-weight="500" fill="#0a0a0b">License</text><text x="85" y="60">ALLOWLIST</text></g>
    <g transform="translate(645,80)"><rect width="170" height="80" rx="12" ry="12" fill="#e08a2c" stroke="#9a5416" stroke-width="1.4"/><text x="85" y="36" font-family="Georgia,serif" font-size="18" font-weight="500" fill="#0a0a0b">Runtime</text><text x="85" y="60">LLAMA.CPP · HF</text></g>
    <g transform="translate(840,80)"><rect width="170" height="80" rx="12" ry="12" fill="#e08a2c" stroke="#9a5416" stroke-width="1.4"/><text x="85" y="36" font-family="Georgia,serif" font-size="18" font-weight="500" fill="#0a0a0b">Score</text><text x="85" y="60">QUALITY · COST</text></g>
    <g transform="translate(1035,80)"><rect width="170" height="80" rx="12" ry="12" fill="#0a0a0b" stroke="#0a0a0b" stroke-width="1.4"/><text x="85" y="36" font-family="Georgia,serif" font-size="18" font-weight="500" fill="#fffefa">Audit</text><text x="85" y="60" fill="#e08a2c">DECISION RECORD</text></g>
  </g>
  <g stroke="#e08a2c" stroke-width="2" fill="none">
    <path d="M232 120 L253 120" marker-end="url(#ar2)"/>
    <path d="M427 120 L448 120" marker-end="url(#ar2)"/>
    <path d="M622 120 L643 120" marker-end="url(#ar2)"/>
    <path d="M817 120 L838 120" marker-end="url(#ar2)"/>
    <path d="M1012 120 L1033 120" marker-end="url(#ar2)"/>
  </g>
</svg>"""


BRAND_CSS = """
:root { --lx-ink:#0a0a0b; --lx-paper:#fffefa; --lx-soft:#f6f0e8; --lx-accent:#e08a2c; --lx-accent-dark:#9a5416; --lx-muted:#726b62; --lx-line:rgba(10,10,11,0.12); }
body, .gradio-container { background: var(--lx-paper) !important; color: var(--lx-ink) !important; font-family: Aptos, "Avenir Next", "Segoe UI", Helvetica, Arial, sans-serif !important; }
.lx-shell { width: min(1280px, calc(100% - 48px)); margin: 0 auto; padding-bottom: 60px; }
.lx-hero { position: relative; padding: 56px 0 28px; border-bottom: 1px solid var(--lx-line); }
.lx-hero::before { content: ""; position: absolute; top: 0; right: 0; width: min(420px, 42vw); height: 3px; background: var(--lx-accent); }
.lx-eyebrow { color: var(--lx-accent-dark); font: 700 12px/1.3 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; letter-spacing: 0.18em; text-transform: uppercase; }
.lx-hero h1 { margin: 14px 0 12px; font-family: Georgia, Cambria, "Times New Roman", serif; font-size: clamp(40px, 6vw, 80px); line-height: 0.95; font-weight: 500; }
.lx-hero p.lead { color: var(--lx-muted); max-width: 820px; font-size: clamp(15px, 1.6vw, 19px); line-height: 1.55; }
.lx-tagline { font-family: Georgia, Cambria, serif; font-style: italic; color: var(--lx-accent-dark); margin-top: 8px; }
.lx-chips { margin-top: 22px; display: flex; flex-wrap: wrap; gap: 10px; }
.lx-chips span { border: 1px solid var(--lx-line); border-radius: 999px; padding: 8px 12px; background: #fff; color: var(--lx-muted); font: 700 11px/1 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; letter-spacing: 0.08em; text-transform: uppercase; }
.lx-explainer { background: var(--lx-soft); border: 1px solid var(--lx-line); border-left: 4px solid var(--lx-accent); border-radius: 10px; padding: 20px 24px; margin: 24px 0; }
.lx-explainer h3 { margin: 0 0 8px; font-family: Georgia, Cambria, serif; font-size: 22px; font-weight: 500; }
.lx-result-allow { background: #f0f7ec; border: 1px solid #4d6b44; border-left: 6px solid #4d6b44; padding: 20px; border-radius: 10px; }
.lx-result-deny { background: #fbeded; border: 1px solid #b03a3a; border-left: 6px solid #b03a3a; padding: 20px; border-radius: 10px; }
.gradio-container button.primary { background: var(--lx-ink) !important; border-color: var(--lx-ink) !important; color: #fff !important; border-radius: 999px !important; font-weight: 700 !important; }
.gradio-container button.primary:hover { background: var(--lx-accent-dark) !important; border-color: var(--lx-accent-dark) !important; }
.gradio-container button:not(.primary) { background: #fff !important; border-color: var(--lx-line) !important; color: var(--lx-ink) !important; border-radius: 999px !important; }
.gradio-container textarea, .gradio-container input, .gradio-container .code { background: #fff !important; color: var(--lx-ink) !important; border-color: var(--lx-line) !important; border-radius: 12px !important; }
.gradio-container label, .gradio-container .block-title, .gradio-container .block-label { color: var(--lx-accent-dark) !important; font: 700 11px/1.2 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace !important; letter-spacing: 0.12em !important; text-transform: uppercase !important; }
footer { display: none !important; }
"""


def run(req_text: str) -> tuple[str, str, str, str]:
    try:
        request = json.loads(req_text)
    except Exception as exc:
        err = f'<div class="lx-result-deny"><h3>Parse error</h3><pre>{type(exc).__name__}: {exc}</pre></div>'
        return err, "", "", ""
    decision = route(REGISTRY, request)
    if decision.selected:
        s = decision.selected
        rows = "".join(
            f"<tr><td><b>{k}</b></td><td><code>{v}</code></td></tr>" for k, v in [
                ("Repo", s["repo_id"]), ("Family", s.get("family", "—")),
                ("Runtime", s.get("runtime", "—")), ("Modalities", ", ".join(s.get("modalities", []))),
                ("Context", f"{s.get('context_tokens', '—')} tok"),
                ("Sovereignty tier", s.get("sovereignty_tier", "—")),
                ("Quality / cost rank", f"{s.get('quality_rank', '—')} / {s.get('cost_rank', '—')}"),
                ("Tools / JSON", f"{s.get('supports_tools')} / {s.get('supports_json')}"),
                ("Score", s.get("_score", "—")),
            ]
        )
        fb_rows = "".join(f'<li><code>{fb["repo_id"]}</code> · score <b>{fb["_score"]}</b></li>' for fb in decision.fallbacks) or "<li>—</li>"
        summary = (
            f'<div class="lx-result-allow">'
            f'<h3>✓ Selected — <code>{s["repo_id"]}</code></h3>'
            f'<table style="margin-top:8px"><tbody>{rows}</tbody></table>'
            f'<p style="margin-top:14px"><b>Fallbacks (next-best matches)</b></p><ol>{fb_rows}</ol>'
            f'</div>'
        )
        explainer = (
            "### Why this model won\n\n"
            f"The router scores each candidate on **quality** (lower rank = better, weighted 2&times;), **sovereignty tier** (weighted 1.5&times;), "
            f"and **cost-fit** (lower = lighter, weighted 0.5&times;). Matching the **task tag** (`{request.get('task_type', '—')}`) adds +3. "
            f"`requires_local` with a `llama_cpp` runtime adds +1. Frontier-size models (>50B active) lose 0.5.\n\n"
            f"**This request asked for:** `{request.get('task_type')}` · modalities `{request.get('modalities')}` · "
            f"jurisdiction `{request.get('jurisdiction')}` · sensitivity `{request.get('data_sensitivity')}` · "
            f"local `{request.get('requires_local')}` · context ≥ `{request.get('min_context_tokens')}`.\n\n"
            f"**Rejected candidates:** {len(decision.rejected)}. Top reasons are jurisdiction mismatch, missing modality, runtime not local, or sovereignty tier too low for sensitive data."
        )
    else:
        summary = (
            f'<div class="lx-result-deny"><h3>✗ No model satisfies the request</h3>'
            f'<p>{len(decision.rejected)} candidates were rejected. See "Rejected candidates" for the gate each one failed.</p></div>'
        )
        explainer = "### Nothing matched\n\nRelax one constraint and try again: drop `requires_local`, broaden `modalities`, lower `min_context_tokens`, or change `data_sensitivity`."

    selected_json = json.dumps(decision.selected, indent=2) if decision.selected else "{}"
    rejected_json = json.dumps(decision.rejected[:10] + ([{"note": f"... {len(decision.rejected) - 10} more"}] if len(decision.rejected) > 10 else []), indent=2)
    return summary, explainer, selected_json, rejected_json


with gr.Blocks(theme=gr.themes.Soft(primary_hue="orange", neutral_hue="stone"), css=BRAND_CSS, title="MaramaRoute Live") as demo:
    with gr.Column(elem_classes="lx-shell"):
        gr.HTML(
            f"""
            <section class="lx-hero">
              <div class="lx-eyebrow">AbteeX AI Labs · Aotearoa New Zealand · Routing across {MODEL_COUNT} LumynaX models</div>
              <h1>MaramaRoute <span style="color:#e08a2c">Live</span></h1>
              <p class="lead">A <b>sovereign model router</b> for the LumynaX release family. Paste a request &mdash; modality, jurisdiction, data sensitivity, runtime constraints &mdash; and see which model wins, with full fallback chain and rejection reasons for every other candidate.</p>
              <p class="lx-tagline">"Ko te mārama te tūāpapa." — the light is the foundation.</p>
              <div class="lx-chips">
                <span>{MODEL_COUNT} models</span><span>Six gates</span><span>Deterministic</span><span>Sovereignty-weighted</span><span>Aotearoa NZ kaupapa</span>
              </div>
            </section>
            """
        )

        gr.HTML(f'<div style="margin: 20px 0 8px"><div style="font: 700 11px/1.2 ui-monospace, Menlo, Consolas, monospace; letter-spacing: 0.18em; color:#9a5416; text-transform:uppercase">Architecture · Six gates</div>{HERO_SVG}</div>')

        gr.HTML(
            """
            <div class="lx-explainer">
              <h3>How the router decides</h3>
              <ol>
                <li><b>Capability gate</b> — model must support the request's modalities, context window, tool calling, and JSON mode.</li>
                <li><b>Sovereignty gate</b> — request's jurisdiction must be in the model's residency; sensitive data requires sovereignty tier ≥ 2.</li>
                <li><b>License gate</b> — optional license allowlist and model-card provenance.</li>
                <li><b>Runtime gate</b> — <code>requires_local</code> excludes hosted-only runtimes.</li>
                <li><b>Score</b> — candidates are scored on quality, cost-fit, sovereignty tier, and task-tag match.</li>
                <li><b>Audit</b> — decision, selected model, fallbacks, and rejection reasons are persisted.</li>
              </ol>
            </div>
            """
        )

        with gr.Row():
            with gr.Column():
                request_box = gr.Code(value=json.dumps(EXAMPLE_CODE, indent=2), language="json", label="Request (JSON)", lines=20)
                with gr.Row():
                    route_btn = gr.Button("Route", variant="primary")
                    ex_code = gr.Button("Restricted code")
                    ex_reason = gr.Button("Reasoning + tools")
                    ex_mm = gr.Button("Public multimodal")
                    ex_emb = gr.Button("Restricted embedding")
                    ex_tiny = gr.Button("Tiny / smoke")
            with gr.Column():
                summary = gr.HTML(value='<div style="color:#726b62; padding:18px"><em>Press <b>Route</b> to evaluate a request against the registry.</em></div>')
        explainer = gr.Markdown()
        with gr.Row():
            sel_json = gr.Code(language="json", label="Selected model (full record)", lines=18)
            rej_json = gr.Code(language="json", label="Rejected candidates (top 10)", lines=18)

        route_btn.click(run, inputs=request_box, outputs=[summary, explainer, sel_json, rej_json])
        ex_code.click(lambda: json.dumps(EXAMPLE_CODE, indent=2), outputs=request_box)
        ex_reason.click(lambda: json.dumps(EXAMPLE_REASON, indent=2), outputs=request_box)
        ex_mm.click(lambda: json.dumps(EXAMPLE_MULTIMODAL, indent=2), outputs=request_box)
        ex_emb.click(lambda: json.dumps(EXAMPLE_EMBEDDING, indent=2), outputs=request_box)
        ex_tiny.click(lambda: json.dumps(EXAMPLE_TINY, indent=2), outputs=request_box)

        gr.HTML(
            """
            <div style="margin-top:32px; padding-top:24px; border-top:1px solid rgba(10,10,11,0.12); text-align:center; color:#726b62; font-size:13px">
              <em>Local roots, global work. · Sovereignty is a design property, not a deployment option.</em><br/>
              <b><a href="https://huggingface.co/AbteeXAILab/marama-route" style="color:#9a5416">Model repo</a></b> ·
              <b><a href="https://huggingface.co/AbteeXAILab/sovereigncode" style="color:#9a5416">SovereignCode</a></b> ·
              <b><a href="https://huggingface.co/spaces/AbteeXAILab/lumynax-live-demo" style="color:#9a5416">Live demo</a></b> ·
              <b><a href="https://abteex.com" style="color:#9a5416">abteex.com</a></b> ·
              <b><a href="https://lumynax.com" style="color:#9a5416">lumynax.com</a></b>
            </div>
            """
        )


if __name__ == "__main__":
    demo.launch()
