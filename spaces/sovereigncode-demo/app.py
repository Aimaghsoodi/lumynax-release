"""SovereignCode Live — interactive Data Capsule policy evaluator (v2 polish)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List

import gradio as gr
import yaml


# ---------- Embedded policy engine ----------
@dataclass
class Decision:
    allowed: bool
    decision: str
    reasons: List[str] = field(default_factory=list)
    obligations: List[str] = field(default_factory=list)
    gate: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"allowed": self.allowed, "decision": self.decision, "gate": self.gate, "reasons": self.reasons, "obligations": self.obligations}


DEFAULT_POLICY_YAML = """policy_id: abx-sovereigncode-default-v0
default_jurisdiction: NZ
default_resident_regions: [NZ]
high_impact_sensitivity: [personal, restricted, health, iwi, taonga]
default_obligations:
  - write_immutable_audit_record
  - preserve_capsule_id_in_agent_trace
  - show_diff_before_write_or_commit
denied_without_human_approval:
  - delete_file
  - execute_shell
  - network_export
  - publish
  - commit
remote_model_rule:
  restricted_data_requires_local_or_lumynax: true
training_rule:
  requires_capsule_training_allowed: true
export_rule:
  requires_capsule_export_allowed: true
"""

EXAMPLE_CAPSULE = {
    "capsule_id": "cap-nz-code-001",
    "subject_id": "abx-workspace",
    "jurisdiction": "NZ",
    "sensitivity": "restricted",
    "allowed_purposes": ["coding_assistance", "inference", "test_generation"],
    "denied_purposes": ["ad_training", "third_party_resale"],
    "resident_regions": ["NZ"],
    "data_classes": ["source_code", "policy", "runtime_logs"],
    "retention_days": 14,
    "export_allowed": False,
    "training_allowed": False,
    "schema_context": "https://schema.org",
    "consent_record": "local-operator-policy-v0",
}

EXAMPLE_REQUEST_ALLOWED = {
    "actor": "developer", "purpose": "coding_assistance", "action": "read_context", "region": "NZ",
    "model_id": "AbteeXAILab/lumynax-infused-qwen3-8b-gguf", "data_classes": ["source_code"],
    "tool_name": "workspace_reader", "writes_files": False, "exports_data": False, "trains_model": False, "human_approved": False,
}
EXAMPLE_REQUEST_DENIED_TRAIN = {
    "actor": "developer", "purpose": "coding_assistance", "action": "train_adapter", "region": "NZ",
    "model_id": "local/lumynax", "data_classes": ["source_code"],
    "tool_name": "trainer", "writes_files": True, "exports_data": False, "trains_model": True, "human_approved": True,
}
EXAMPLE_REQUEST_DENIED_REGION = {
    "actor": "developer", "purpose": "inference", "action": "model_call", "region": "AU",
    "model_id": "AbteeXAILab/lumynax-infused-qwen3-8b-gguf", "data_classes": ["source_code"],
    "tool_name": "model_caller", "writes_files": False, "exports_data": False, "trains_model": False, "human_approved": False,
}
EXAMPLE_REQUEST_DENIED_REMOTE = {
    "actor": "developer", "purpose": "inference", "action": "model_call", "region": "NZ",
    "model_id": "openai/gpt-4o", "data_classes": ["source_code"],
    "tool_name": "model_caller", "writes_files": False, "exports_data": False, "trains_model": False, "human_approved": False,
}
EXAMPLE_REQUEST_DENIED_APPROVAL = {
    "actor": "developer", "purpose": "coding_assistance", "action": "execute_shell", "region": "NZ",
    "model_id": "local/lumynax", "data_classes": ["source_code"],
    "tool_name": "shell", "writes_files": False, "exports_data": False, "trains_model": False, "human_approved": False,
}


def evaluate(capsule: Dict[str, Any], request: Dict[str, Any], policy: Dict[str, Any]) -> Decision:
    obligations: List[str] = list(policy.get("default_obligations", []))
    purpose = request.get("purpose")
    if purpose in capsule.get("denied_purposes", []):
        return Decision(False, "deny", [f"purpose `{purpose}` is in capsule.denied_purposes"], obligations, "purpose")
    if capsule.get("allowed_purposes") and purpose not in capsule.get("allowed_purposes", []):
        return Decision(False, "deny", [f"purpose `{purpose}` not in capsule.allowed_purposes"], obligations, "purpose")
    region = request.get("region")
    resident = capsule.get("resident_regions", [])
    if region and resident and region not in resident:
        return Decision(False, "deny", [f"region `{region}` not in capsule.resident_regions `{resident}`"], obligations, "residency")
    sensitivity = str(capsule.get("sensitivity", "")).lower()
    is_high = sensitivity in set(map(str.lower, policy.get("high_impact_sensitivity", [])))
    if policy.get("remote_model_rule", {}).get("restricted_data_requires_local_or_lumynax") and is_high:
        mid = str(request.get("model_id", "")).lower()
        if not (mid.startswith("local/") or "lumynax" in mid):
            return Decision(False, "deny", [f"restricted data ({sensitivity}) requires local or LumynaX-governed model; got `{request.get('model_id')}`"], obligations, "remote-model")
    if request.get("trains_model"):
        if policy.get("training_rule", {}).get("requires_capsule_training_allowed") and not capsule.get("training_allowed", False):
            return Decision(False, "deny", ["training_rule requires capsule.training_allowed = true"], obligations, "training")
    if request.get("exports_data"):
        if policy.get("export_rule", {}).get("requires_capsule_export_allowed") and not capsule.get("export_allowed", False):
            return Decision(False, "deny", ["export_rule requires capsule.export_allowed = true"], obligations, "export")
    action = request.get("action")
    if action in set(policy.get("denied_without_human_approval", [])) and not request.get("human_approved", False):
        return Decision(False, "deny", [f"action `{action}` requires human approval (request.human_approved is false)"], obligations, "approval")
    if request.get("writes_files"):
        obligations.append("show_diff_before_write_or_commit")
    if is_high:
        obligations.append("route_to_local_or_lumynax_model")
    obligations = sorted(set(obligations))
    reasons = [f"capsule `{capsule.get('capsule_id')}` permits purpose `{purpose}` in region `{region}`"]
    return Decision(True, "allow_with_obligations" if obligations else "allow", reasons, obligations, "allow")


def request_hash(request: Dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(request, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


# ---------- Brand SVGs / CSS ----------
HERO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 200" role="img" aria-label="SovereignCode runtime flow">
  <defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="#e08a2c"/></marker></defs>
  <rect width="1280" height="200" fill="#fffefa"/>
  <rect x="0" y="0" width="1280" height="3" fill="#0a0a0b"/>
  <text x="64" y="32" font-family="ui-monospace,Menlo,Consolas,monospace" font-size="11" font-weight="700" letter-spacing="0.2em" fill="#9a5416">SOVEREIGNCODE · POLICY DECISION POINT</text>
  <g font-family="Georgia,Cambria,serif" font-size="18" font-weight="500" fill="#0a0a0b" text-anchor="middle">
    <g transform="translate(60,68)"><rect width="200" height="90" rx="12" ry="12" fill="#fffefa" stroke="#0a0a0b" stroke-width="1.4"/><text x="100" y="40">Request</text><text x="100" y="62" font-family="ui-monospace,Menlo,Consolas,monospace" font-size="10" letter-spacing="0.14em" fill="#9a5416">CLIENT INTENT</text></g>
    <g transform="translate(310,68)"><rect width="200" height="90" rx="12" ry="12" fill="#e08a2c" stroke="#9a5416" stroke-width="1.4"/><text x="100" y="40">Data Capsule</text><text x="100" y="62" font-family="ui-monospace,Menlo,Consolas,monospace" font-size="10" letter-spacing="0.14em" fill="#fff7ed">POLICY ENVELOPE</text></g>
    <g transform="translate(560,68)"><rect width="200" height="90" rx="12" ry="12" fill="#e08a2c" stroke="#9a5416" stroke-width="1.4"/><text x="100" y="40">PDP</text><text x="100" y="62" font-family="ui-monospace,Menlo,Consolas,monospace" font-size="10" letter-spacing="0.14em" fill="#fff7ed">DECISION ENGINE</text></g>
    <g transform="translate(810,68)"><rect width="200" height="90" rx="12" ry="12" fill="#fffefa" stroke="#0a0a0b" stroke-width="1.4"/><text x="100" y="40">Tool Broker</text><text x="100" y="62" font-family="ui-monospace,Menlo,Consolas,monospace" font-size="10" letter-spacing="0.14em" fill="#9a5416">ENFORCEMENT</text></g>
    <g transform="translate(1060,68)"><rect width="160" height="90" rx="12" ry="12" fill="#0a0a0b" stroke="#0a0a0b" stroke-width="1.4"/><text x="80" y="40" fill="#fffefa">Audit</text><text x="80" y="62" font-family="ui-monospace,Menlo,Consolas,monospace" font-size="10" letter-spacing="0.14em" fill="#e08a2c">HASH-CHAINED</text></g>
  </g>
  <g stroke="#e08a2c" stroke-width="2" fill="none">
    <path d="M262 113 L308 113" marker-end="url(#ar)"/>
    <path d="M512 113 L558 113" marker-end="url(#ar)"/>
    <path d="M762 113 L808 113" marker-end="url(#ar)"/>
    <path d="M1012 113 L1058 113" marker-end="url(#ar)"/>
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
.lx-explainer ol { margin: 8px 0 0 18px; color: var(--lx-ink); }
.lx-explainer li { margin: 4px 0; }
.lx-explainer code { background: #fff; padding: 1px 6px; border-radius: 4px; border: 1px solid var(--lx-line); font-size: 12px; }
.lx-result-allow { background: #f0f7ec; border: 1px solid #4d6b44; border-left: 6px solid #4d6b44; padding: 20px; border-radius: 10px; }
.lx-result-deny { background: #fbeded; border: 1px solid #b03a3a; border-left: 6px solid #b03a3a; padding: 20px; border-radius: 10px; }
.gradio-container button.primary { background: var(--lx-ink) !important; border-color: var(--lx-ink) !important; color: #fff !important; border-radius: 999px !important; font-weight: 700 !important; }
.gradio-container button.primary:hover { background: var(--lx-accent-dark) !important; border-color: var(--lx-accent-dark) !important; }
.gradio-container button:not(.primary) { background: #fff !important; border-color: var(--lx-line) !important; color: var(--lx-ink) !important; border-radius: 999px !important; }
.gradio-container textarea, .gradio-container input, .gradio-container .code { background: #fff !important; color: var(--lx-ink) !important; border-color: var(--lx-line) !important; border-radius: 12px !important; }
.gradio-container label, .gradio-container .block-title, .gradio-container .block-label { color: var(--lx-accent-dark) !important; font: 700 11px/1.2 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace !important; letter-spacing: 0.12em !important; text-transform: uppercase !important; }
footer { display: none !important; }
"""


GATE_EXPLAIN = {
    "purpose": "**Purpose gate.** The capsule explicitly allows / denies certain purposes (e.g. coding_assistance, inference). A request with a purpose outside the allowed set is denied.",
    "residency": "**Residency gate.** The capsule binds data to specific regions. A request from outside those regions is denied to prevent data egress.",
    "remote-model": "**Remote-model gate.** For high-sensitivity data (restricted, personal, health, iwi, taonga), only local or LumynaX-governed models may be used. Generic remote APIs are denied.",
    "training": "**Training gate.** The capsule's `training_allowed` flag is checked before any model adaptation. If false, training requests are denied even if every other gate passes.",
    "export": "**Export gate.** `export_allowed` must be true before any operation that ships data outside the operator's environment.",
    "approval": "**Human-approval gate.** High-impact actions (shell, delete, publish, commit, network export) require explicit human approval. Without it, the request is denied.",
    "allow": "**Allow with obligations.** Every gate passed. The decision attaches obligations (audit logging, diff display, local routing) that the tool broker must honour before executing the action.",
}


def run(capsule_text: str, request_text: str, policy_text: str) -> tuple[str, str, str, str]:
    try:
        capsule = json.loads(capsule_text)
        request = json.loads(request_text)
        policy = yaml.safe_load(policy_text)
    except Exception as exc:
        err = f'<div class="lx-result-deny"><h3>Parse error</h3><pre>{type(exc).__name__}: {exc}</pre></div>'
        return err, "", "", ""
    decision = evaluate(capsule, request, policy)
    audit = {
        "capsule_id": str(capsule.get("capsule_id", "")), "actor": str(request.get("actor", "")),
        "purpose": str(request.get("purpose", "")), "action": str(request.get("action", "")),
        "model_id": str(request.get("model_id", "")), "decision": decision.decision,
        "gate": decision.gate, "reasons": decision.reasons, "obligations": decision.obligations,
        "request_hash": request_hash(request), "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    klass = "lx-result-allow" if decision.allowed else "lx-result-deny"
    icon = "✓" if decision.allowed else "✗"
    badge = "ALLOWED" if decision.allowed else "DENIED"
    reasons_html = "".join(f"<li>{r}</li>" for r in decision.reasons)
    obligations_html = "".join(f"<li><code>{o}</code></li>" for o in decision.obligations)
    summary_html = (
        f'<div class="{klass}">'
        f'<h3>{icon} {badge} &mdash; <code>{decision.decision}</code></h3>'
        f'<p><b>Gate:</b> <code>{decision.gate}</code></p>'
        f'<p><b>Reasons</b></p><ul>{reasons_html}</ul>'
        + (f'<p><b>Obligations</b></p><ul>{obligations_html}</ul>' if decision.obligations else "")
        + '</div>'
    )
    explainer_md = "### How to read this\n\n" + GATE_EXPLAIN.get(decision.gate, "")
    return summary_html, explainer_md, json.dumps(decision.to_dict(), indent=2), json.dumps(audit, indent=2)


with gr.Blocks(theme=gr.themes.Soft(primary_hue="orange", neutral_hue="stone"), css=BRAND_CSS, title="SovereignCode Live") as demo:
    with gr.Column(elem_classes="lx-shell"):
        gr.HTML(
            """
            <section class="lx-hero">
              <div class="lx-eyebrow">AbteeX AI Labs · Aotearoa New Zealand</div>
              <h1>SovereignCode <span style="color:#e08a2c">Live</span></h1>
              <p class="lead">Interactive <b>Data Capsule policy evaluator</b>. Paste a capsule and a tool / model action; the policy decision point returns a deterministic decision, the gate that triggered it, an obligations list, and a hash-stable audit record. No code is executed.</p>
              <p class="lx-tagline">"Sovereign intelligence, held in the light." · Ko te mārama te tūāpapa.</p>
              <div class="lx-chips">
                <span>Local-first</span><span>Policy before tools</span><span>Hash-chained audit</span><span>Provenance visible</span><span>Aotearoa NZ kaupapa</span>
              </div>
            </section>
            """
        )

        gr.HTML(f'<div style="margin: 20px 0 8px"><div style="font: 700 11px/1.2 ui-monospace, Menlo, Consolas, monospace; letter-spacing: 0.18em; color:#9a5416; text-transform:uppercase">Architecture</div>{HERO_SVG}</div>')

        gr.HTML(
            """
            <div class="lx-explainer">
              <h3>How to use this demo</h3>
              <ol>
                <li>Edit the <b>Data Capsule</b> on the left (the policy envelope attached to your workspace / dataset / tenant).</li>
                <li>Edit the <b>Action Request</b> on the right (what an agent wants to do: read context, call a model, write a file, train, export).</li>
                <li>Press <b>Evaluate</b>. The PDP returns one of: <code>allow</code>, <code>allow_with_obligations</code>, or <code>deny</code> &mdash; with the <b>gate</b> that decided it.</li>
              </ol>
              <p style="margin-top:12px"><b>Gates evaluated, in order:</b> purpose → residency → remote-model → training → export → human-approval. The first failing gate stops the chain.</p>
            </div>
            """
        )

        with gr.Row():
            with gr.Column():
                capsule_box = gr.Code(value=json.dumps(EXAMPLE_CAPSULE, indent=2), language="json", label="Data Capsule (JSON)", lines=22)
            with gr.Column():
                request_box = gr.Code(value=json.dumps(EXAMPLE_REQUEST_ALLOWED, indent=2), language="json", label="Action Request (JSON)", lines=22)

        with gr.Row():
            evaluate_btn = gr.Button("Evaluate", variant="primary")
            ex_allow = gr.Button("Example · allowed")
            ex_train = gr.Button("Example · denied (training)")
            ex_region = gr.Button("Example · denied (region)")
            ex_remote = gr.Button("Example · denied (remote model)")
            ex_approval = gr.Button("Example · denied (approval missing)")

        with gr.Accordion("Policy (YAML, editable)", open=False):
            policy_box = gr.Code(value=DEFAULT_POLICY_YAML, language="yaml", label="Policy", lines=20)

        result_html = gr.HTML()
        explainer_md = gr.Markdown()
        with gr.Row():
            decision_json = gr.Code(language="json", label="Decision record", lines=14)
            audit_json = gr.Code(language="json", label="Audit record (hash-stable)", lines=14)

        evaluate_btn.click(run, inputs=[capsule_box, request_box, policy_box], outputs=[result_html, explainer_md, decision_json, audit_json])
        ex_allow.click(lambda: json.dumps(EXAMPLE_REQUEST_ALLOWED, indent=2), outputs=request_box)
        ex_train.click(lambda: json.dumps(EXAMPLE_REQUEST_DENIED_TRAIN, indent=2), outputs=request_box)
        ex_region.click(lambda: json.dumps(EXAMPLE_REQUEST_DENIED_REGION, indent=2), outputs=request_box)
        ex_remote.click(lambda: json.dumps(EXAMPLE_REQUEST_DENIED_REMOTE, indent=2), outputs=request_box)
        ex_approval.click(lambda: json.dumps(EXAMPLE_REQUEST_DENIED_APPROVAL, indent=2), outputs=request_box)

        gr.HTML(
            """
            <div style="margin-top:32px; padding-top:24px; border-top:1px solid rgba(10,10,11,0.12); text-align:center; color:#726b62; font-size:13px">
              <em>Local roots, global work. · Sovereignty is a design property, not a deployment option.</em><br/>
              <b><a href="https://huggingface.co/AbteeXAILab/sovereigncode" style="color:#9a5416">Model repo</a></b> ·
              <b><a href="https://huggingface.co/AbteeXAILab/marama-route" style="color:#9a5416">MaramaRoute</a></b> ·
              <b><a href="https://huggingface.co/spaces/AbteeXAILab/lumynax-live-demo" style="color:#9a5416">Live demo</a></b> ·
              <b><a href="https://abteex.com" style="color:#9a5416">abteex.com</a></b> ·
              <b><a href="https://lumynax.com" style="color:#9a5416">lumynax.com</a></b>
            </div>
            """
        )


if __name__ == "__main__":
    demo.launch()
