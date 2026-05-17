from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ._ui_server import serve_dashboard

try:
    from tinyluminax.products.marama_route import RoutingRequest, load_model_registry
except ModuleNotFoundError:  # standalone HF package
    from marama_route import (  # type: ignore[no-redef]
        RoutingRequest,
        load_model_registry,
    )

from .audit import build_audit_record
from .planner import plan_coding_turn
from .platform import (
    build_capsule_summary,
    build_opencode_workspace_config,
    build_policy_matrix,
    build_turn_brief,
    check_tool_request,
    tool_scenarios,
)
from .policy import DataCapsule, SovereignRequest, SovereigntyPolicyEngine

PRODUCT_NAME = "AbteeX SovereignCode"
PACKAGE_ROOT = Path(__file__).resolve().parent
PACKAGE_PARENT = PACKAGE_ROOT.parent


def default_capsule_path() -> Path:
    return _first_existing(
        [
            Path.cwd() / "products" / "abx-sovereigncode" / "examples" / "capsule.restricted-nz-code.json",
            Path.cwd() / "examples" / "capsule.restricted-nz-code.json",
            PACKAGE_ROOT / "examples" / "capsule.restricted-nz-code.json",
            PACKAGE_PARENT / "examples" / "capsule.restricted-nz-code.json",
        ],
    )


def default_request_path() -> Path:
    return _first_existing(
        [
            Path.cwd() / "products" / "abx-sovereigncode" / "examples" / "request.allowed-local-edit.json",
            Path.cwd() / "examples" / "request.allowed-local-edit.json",
            PACKAGE_ROOT / "examples" / "request.allowed-local-edit.json",
            PACKAGE_PARENT / "examples" / "request.allowed-local-edit.json",
        ],
    )


def default_personal_capsule_path() -> Path:
    return _first_existing(
        [
            Path.cwd()
            / "products"
            / "abx-sovereigncode"
            / "examples"
            / "capsule.personal-sovereignty-profile.json",
            Path.cwd() / "examples" / "capsule.personal-sovereignty-profile.json",
            PACKAGE_ROOT / "examples" / "capsule.personal-sovereignty-profile.json",
            PACKAGE_PARENT / "examples" / "capsule.personal-sovereignty-profile.json",
        ],
    )


def default_personal_request_path() -> Path:
    return _first_existing(
        [
            Path.cwd() / "products" / "abx-sovereigncode" / "examples" / "request.personal-memory-read.json",
            Path.cwd() / "examples" / "request.personal-memory-read.json",
            PACKAGE_ROOT / "examples" / "request.personal-memory-read.json",
            PACKAGE_PARENT / "examples" / "request.personal-memory-read.json",
        ],
    )


def default_route_request_path() -> Path:
    return _first_existing(
        [
            Path.cwd() / "products" / "lumynax-marama-route" / "examples" / "request.code-restricted.json",
            Path.cwd() / "examples" / "request.code-restricted.json",
            PACKAGE_ROOT / "examples" / "request.code-restricted.json",
            PACKAGE_PARENT / "examples" / "request.code-restricted.json",
        ],
    )


def default_registry_path() -> Path:
    return _first_existing(
        [
            Path.cwd() / "products" / "lumynax-marama-route" / "configs" / "lumynax_model_registry.json",
            Path.cwd() / "configs" / "lumynax_model_registry.json",
            PACKAGE_ROOT / "configs" / "lumynax_model_registry.json",
            PACKAGE_PARENT / "configs" / "lumynax_model_registry.json",
        ],
    )


def _first_existing(candidates: list[Path]) -> Path:
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def load_json_mapping(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


def evaluate_dashboard_payload(
    payload: dict[str, Any],
    registry_path: Path,
) -> dict[str, Any]:
    capsule_payload = _mapping(payload.get("capsule"))
    request_payload = _mapping(payload.get("request"))
    if not capsule_payload or not request_payload:
        raise ValueError("Payload must include `capsule` and `request` objects")

    capsule = DataCapsule.from_payload(capsule_payload)
    request = SovereignRequest.from_payload(request_payload)
    decision = SovereigntyPolicyEngine().evaluate(capsule, request)
    audit = build_audit_record(capsule, request, decision)
    result: dict[str, Any] = {
        "ok": decision.allowed,
        "decision": decision.to_dict(),
        "audit_record": audit.to_dict(),
    }

    route_payload = _mapping(payload.get("route_request"))
    if route_payload:
        models = load_model_registry(registry_path)
        route_request = RoutingRequest.from_payload(route_payload)
        plan = plan_coding_turn(capsule, request, route_request, models)
        result["ok"] = plan.allowed
        result["plan"] = plan.to_dict()
    return result


def build_dashboard_state(
    capsule_path: Path,
    request_path: Path,
    route_request_path: Path,
    registry_path: Path,
) -> dict[str, Any]:
    personal_capsule = (
        load_json_mapping(default_personal_capsule_path())
        if default_personal_capsule_path().exists()
        else _fallback_personal_capsule()
    )
    personal_request = (
        load_json_mapping(default_personal_request_path())
        if default_personal_request_path().exists()
        else _fallback_personal_request()
    )
    models = load_model_registry(registry_path)
    capsule = load_json_mapping(capsule_path)
    request = load_json_mapping(request_path)
    route_request = load_json_mapping(route_request_path)
    return {
        "capsule": capsule,
        "request": request,
        "route_request": route_request,
        "personal_capsule": personal_capsule,
        "personal_request": personal_request,
        "capsule_summary": build_capsule_summary(capsule),
        "personal_capsule_summary": build_capsule_summary(personal_capsule),
        "policy_matrix": build_policy_matrix(capsule, request),
        "tool_scenarios": tool_scenarios(),
        "opencode_config": build_opencode_workspace_config(),
        "registry_path": str(registry_path),
        "model_count": len(models),
    }


def handle_api_request(
    method: str,
    path: str,
    payload: dict[str, Any] | None,
    registry_path: Path,
    state: dict[str, Any],
) -> tuple[int, dict[str, Any]]:
    if method == "GET" and path == "/api/health":
        return 200, {
            "ok": True,
            "product": PRODUCT_NAME,
            "model_count": state["model_count"],
        }
    if method == "GET" and path == "/api/state":
        return 200, {"ok": True, **state}
    if method == "POST" and path in {"/api/evaluate", "/api/plan"} and payload is not None:
        result = evaluate_dashboard_payload(payload, registry_path)
        if "plan" in result:
            result["turn_brief"] = build_turn_brief(result["plan"])
        return (200 if result["ok"] else 422), result
    if method == "POST" and path == "/api/policy-matrix" and payload is not None:
        capsule = _mapping(payload.get("capsule")) or state["capsule"]
        request = _mapping(payload.get("request")) or state["request"]
        return 200, build_policy_matrix(capsule, request)
    if method == "POST" and path == "/api/tool-check" and payload is not None:
        capsule = _mapping(payload.get("capsule")) or state["capsule"]
        request = _mapping(payload.get("request")) or state["request"]
        tool = _mapping(payload.get("tool"))
        result = check_tool_request(capsule, request, tool)
        return (200 if result["ok"] else 422), result
    if method == "POST" and path == "/api/opencode-config" and payload is not None:
        return 200, {
            "ok": True,
            "config": build_opencode_workspace_config(
                base_url=str(payload.get("base_url") or "http://127.0.0.1:8787/v1"),
                model=str(payload.get("model") or "lumynax-infused-qwen3-coder-30b-a3b-gguf"),
            ),
        }
    return 404, {"ok": False, "error": "not_found"}


def smoke_ui(
    *,
    capsule_path: Path | None = None,
    request_path: Path | None = None,
    route_request_path: Path | None = None,
    registry_path: Path | None = None,
) -> dict[str, Any]:
    resolved_capsule = capsule_path or default_capsule_path()
    resolved_request = request_path or default_request_path()
    resolved_route = route_request_path or default_route_request_path()
    resolved_registry = registry_path or default_registry_path()
    state = build_dashboard_state(
        resolved_capsule,
        resolved_request,
        resolved_route,
        resolved_registry,
    )
    result = evaluate_dashboard_payload(
        {
            "capsule": state["capsule"],
            "request": state["request"],
            "route_request": state["route_request"],
        },
        resolved_registry,
    )
    if not result["ok"]:
        raise RuntimeError("SovereignCode UI smoke plan was blocked")
    selected = result["plan"]["route_decision"]["selected_model"]["model_id"]
    matrix = build_policy_matrix(state["capsule"], state["request"])
    tool = check_tool_request(state["capsule"], state["request"], tool_scenarios()[0])
    if matrix["blocked_count"] < 1 or not tool["ok"]:
        raise RuntimeError("SovereignCode expanded UI smoke checks failed")
    return {
        "ok": True,
        "product": PRODUCT_NAME,
        "model_count": state["model_count"],
        "selected_model": selected,
        "matrix_rows": len(matrix["rows"]),
        "tool_check": tool["ok"],
    }


def run_ui(
    *,
    capsule_path: Path | None = None,
    request_path: Path | None = None,
    route_request_path: Path | None = None,
    registry_path: Path | None = None,
    host: str = "127.0.0.1",
    port: int = 8788,
    open_browser: bool = False,
    smoke: bool = False,
) -> int:
    resolved_capsule = capsule_path or default_capsule_path()
    resolved_request = request_path or default_request_path()
    resolved_route = route_request_path or default_route_request_path()
    resolved_registry = registry_path or default_registry_path()
    if smoke:
        print(
            json.dumps(
                smoke_ui(
                    capsule_path=resolved_capsule,
                    request_path=resolved_request,
                    route_request_path=resolved_route,
                    registry_path=resolved_registry,
                ),
                indent=2,
                sort_keys=True,
            ),
        )
        return 0

    state = build_dashboard_state(
        resolved_capsule,
        resolved_request,
        resolved_route,
        resolved_registry,
    )
    html = build_expanded_dashboard_html(state)
    return serve_dashboard(
        product_name=PRODUCT_NAME,
        html=html,
        api_handler=lambda method, path, payload: handle_api_request(
            method,
            path,
            payload,
            resolved_registry,
            state,
        ),
        host=host,
        port=port,
        open_browser=open_browser,
    )


def build_expanded_dashboard_html(state: dict[str, Any]) -> str:
    initial = json.dumps(state, sort_keys=True).replace("</", "<\\/")
    html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AbteeX SovereignCode Console</title>
  <style>
    :root {
      --paper: #fffefa;
      --ink: #0a0a0b;
      --muted: #726b62;
      --rule: #ded6c8;
      --amber: #e08a2c;
      --amber-dark: #9a5416;
      --green: #275f45;
      --red: #8f2e24;
      --panel: #f7f1e7;
      --chalk: #fff7e8;
      --mono: "Cascadia Code", "SFMono-Regular", Menlo, Consolas, monospace;
      --serif: Georgia, "Iowan Old Style", "Palatino Linotype", serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background:
        linear-gradient(90deg, rgba(10,10,11,.035) 1px, transparent 1px) 0 0 / 42px 42px,
        linear-gradient(0deg, rgba(10,10,11,.025) 1px, transparent 1px) 0 0 / 42px 42px,
        var(--paper);
      color: var(--ink);
      font-family: var(--serif);
    }
    header {
      display: grid;
      grid-template-columns: minmax(260px, 1fr) minmax(320px, 48vw);
      gap: 24px;
      align-items: end;
      padding: 22px 28px 16px;
      border-bottom: 1px solid var(--rule);
      background: rgba(255,254,250,.92);
    }
    h1 {
      margin: 0;
      font-size: clamp(34px, 5vw, 68px);
      line-height: .88;
      letter-spacing: 0;
    }
    .subtitle, label, button, select, .metric, .k, th, td {
      font-family: var(--mono);
      font-size: 12px;
      letter-spacing: 0;
    }
    .subtitle { margin-top: 10px; color: var(--muted); }
    .metrics { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px; }
    .metric { border-left: 2px solid var(--amber); min-height: 60px; padding: 7px 8px; background: rgba(247,241,231,.72); }
    .metric strong { display: block; font: 700 22px/1 var(--serif); color: var(--ink); overflow-wrap: anywhere; }
    main { display: grid; grid-template-columns: minmax(360px, 480px) 1fr; min-height: calc(100vh - 118px); }
    aside { border-right: 1px solid var(--rule); background: rgba(255,250,242,.95); padding: 18px; }
    .content { padding: 18px; display: grid; gap: 12px; align-content: start; min-width: 0; }
    .stack { display: grid; gap: 12px; }
    .grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
    .split { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 12px; }
    .panel, textarea, pre, table, select { border: 1px solid var(--rule); border-radius: 6px; background: var(--paper); color: var(--ink); }
    .panel { padding: 14px; min-width: 0; }
    .panel h2 { margin: 0 0 10px; font-size: 18px; line-height: 1.1; }
    textarea {
      width: 100%;
      min-height: 150px;
      resize: vertical;
      padding: 12px;
      font: 12px/1.45 var(--mono);
    }
    #routeRequest { min-height: 118px; }
    select { width: 100%; min-height: 34px; padding: 0 10px; }
    button {
      appearance: none;
      border: 1px solid var(--ink);
      background: var(--ink);
      color: var(--paper);
      border-radius: 4px;
      min-height: 34px;
      padding: 0 12px;
      cursor: pointer;
      white-space: nowrap;
    }
    button.secondary { background: transparent; color: var(--ink); border-color: var(--rule); }
    .toolbar { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
    .status { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10px; }
    .status .panel { min-height: 92px; }
    .k { color: var(--muted); display: block; line-height: 1.25; }
    .v { display: block; margin-top: 8px; font-size: 18px; line-height: 1.12; overflow-wrap: anywhere; }
    .ok { color: var(--green); }
    .bad { color: var(--red); }
    pre { margin: 0; padding: 14px; max-height: 520px; overflow: auto; font: 12px/1.45 var(--mono); }
    table { width: 100%; border-collapse: collapse; overflow: hidden; }
    th, td { padding: 9px 10px; text-align: left; border-bottom: 1px solid var(--rule); vertical-align: top; }
    th { color: var(--muted); background: var(--panel); }
    tr:last-child td { border-bottom: 0; }
    .pill { display: inline-flex; border: 1px solid var(--rule); border-radius: 999px; min-height: 24px; align-items: center; padding: 0 9px; margin: 0 5px 5px 0; background: var(--chalk); font: 12px/1 var(--mono); }
    @media (max-width: 1180px) {
      header, main, .split { grid-template-columns: 1fr; }
      aside { border-right: 0; border-bottom: 1px solid var(--rule); }
      .metrics, .status { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    @media (max-width: 680px) {
      header, aside, .content { padding: 14px; }
      .grid, .metrics, .status { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>AbteeX<br />SovereignCode</h1>
      <div class="subtitle">Policy decision point, route plan, tool gates, audit receipt.</div>
    </div>
    <div class="metrics">
      <div class="metric"><strong id="metricModels">0</strong>models</div>
      <div class="metric"><strong id="metricRegion">NZ</strong>region</div>
      <div class="metric"><strong id="metricSensitivity">-</strong>sensitivity</div>
      <div class="metric"><strong id="metricRetention">0</strong>retention</div>
      <div class="metric"><strong id="metricBlocked">0</strong>blocked tools</div>
    </div>
  </header>
  <main>
    <aside class="stack">
      <div class="toolbar">
        <button id="planBtn">Plan Turn</button>
        <button class="secondary" id="evaluateBtn">Evaluate</button>
        <button class="secondary" id="matrixBtn">Matrix</button>
        <button class="secondary" id="providerBtn">Provider</button>
      </div>
      <div class="toolbar">
        <button class="secondary" id="restrictedBtn">Restricted</button>
        <button class="secondary" id="personalBtn">Personal</button>
      </div>
      <div>
        <label for="toolScenario">TOOL GATE</label>
        <select id="toolScenario"></select>
      </div>
      <div>
        <label for="capsule">DATA CAPSULE</label>
        <textarea id="capsule" spellcheck="false"></textarea>
      </div>
      <div>
        <label for="request">SOVEREIGN REQUEST</label>
        <textarea id="request" spellcheck="false"></textarea>
      </div>
      <div>
        <label for="routeRequest">ROUTE REQUEST</label>
        <textarea id="routeRequest" spellcheck="false"></textarea>
      </div>
    </aside>
    <section class="content">
      <div class="status">
        <div class="panel"><span class="k">DECISION</span><span class="v" id="decision">pending</span></div>
        <div class="panel"><span class="k">MODEL</span><span class="v" id="selected">pending</span></div>
        <div class="panel"><span class="k">GRANTS</span><span class="v" id="grants">0</span></div>
        <div class="panel"><span class="k">OBLIGATIONS</span><span class="v" id="obligations">0</span></div>
        <div class="panel"><span class="k">NEXT GATE</span><span class="v" id="nextGate">ready</span></div>
      </div>
      <div class="split">
        <div class="panel">
          <h2>Turn Result</h2>
          <pre id="output"></pre>
        </div>
        <div class="panel">
          <h2>Operator Checklist</h2>
          <table>
            <thead><tr><th>Gate</th><th>Status</th><th>Detail</th></tr></thead>
            <tbody id="checkRows"></tbody>
          </table>
        </div>
      </div>
      <div class="split">
        <div class="panel">
          <h2>Policy Matrix</h2>
          <table>
            <thead><tr><th>Tool</th><th>Decision</th><th>Reasons</th></tr></thead>
            <tbody id="matrixRows"></tbody>
          </table>
        </div>
        <div class="panel">
          <h2>Capsule Summary</h2>
          <div id="capsuleSummary"></div>
        </div>
      </div>
      <div class="panel">
        <h2>Provider Config</h2>
        <pre id="provider"></pre>
      </div>
    </section>
  </main>
  <script type="application/json" id="initial-state">__INITIAL__</script>
  <script>
    const state = JSON.parse(document.getElementById('initial-state').textContent);
    const capsule = document.getElementById('capsule');
    const request = document.getElementById('request');
    const routeRequest = document.getElementById('routeRequest');
    const output = document.getElementById('output');
    const provider = document.getElementById('provider');
    const decision = document.getElementById('decision');
    const selected = document.getElementById('selected');
    const grants = document.getElementById('grants');
    const obligations = document.getElementById('obligations');
    const nextGate = document.getElementById('nextGate');
    const matrixRows = document.getElementById('matrixRows');
    const checkRows = document.getElementById('checkRows');
    const capsuleSummary = document.getElementById('capsuleSummary');
    const toolScenario = document.getElementById('toolScenario');

    function writeJson(node, value) { node.textContent = JSON.stringify(value, null, 2); }
    function safeJson(text) {
      try { return [JSON.parse(text), null]; }
      catch (error) { return [null, error.message]; }
    }
    function setMetric(id, value) { document.getElementById(id).textContent = value; }
    setMetric('metricModels', state.model_count);
    setMetric('metricRegion', state.capsule_summary.jurisdiction);
    setMetric('metricSensitivity', state.capsule_summary.sensitivity);
    setMetric('metricRetention', state.capsule_summary.retention_days);
    setMetric('metricBlocked', state.policy_matrix.blocked_count);
    toolScenario.innerHTML = state.tool_scenarios.map((item, index) => `<option value="${index}">${item.name}</option>`).join('');

    function loadRestricted() {
      capsule.value = JSON.stringify(state.capsule, null, 2);
      request.value = JSON.stringify(state.request, null, 2);
      routeRequest.value = JSON.stringify(state.route_request, null, 2);
      renderCapsuleSummary(state.capsule_summary);
    }
    function loadPersonal() {
      capsule.value = JSON.stringify(state.personal_capsule, null, 2);
      request.value = JSON.stringify(state.personal_request, null, 2);
      routeRequest.value = JSON.stringify(state.route_request, null, 2);
      renderCapsuleSummary(state.personal_capsule_summary);
    }
    function readPayload(includeRoute) {
      const payload = {capsule: JSON.parse(capsule.value), request: JSON.parse(request.value)};
      if (includeRoute) payload.route_request = JSON.parse(routeRequest.value);
      return payload;
    }
    function renderMatrix(matrix) {
      matrixRows.innerHTML = matrix.rows.map(row => `<tr><td>${row.name}<br><span class="k">${row.tool_name}</span></td><td class="${row.allowed ? 'ok' : 'bad'}">${row.allowed ? 'allow' : 'block'}</td><td>${row.reason_count}</td></tr>`).join('');
      setMetric('metricBlocked', matrix.blocked_count);
    }
    function renderChecklist(rows) {
      checkRows.innerHTML = rows.map(row => `<tr><td>${row.item}</td><td>${row.status}</td><td>${row.detail}</td></tr>`).join('');
    }
    function renderCapsuleSummary(summary) {
      capsuleSummary.innerHTML = `
        <div class="pill">${summary.capsule_id}</div>
        <div class="pill">${summary.jurisdiction}</div>
        <div class="pill">${summary.sensitivity}</div>
        <div class="pill">${summary.retention_days} days</div>
        ${(summary.risk_flags || []).map(item => `<div class="pill">${item}</div>`).join('')}
      `;
    }
    function setResult(data) {
      writeJson(output, data);
      const plan = data.plan || {};
      const brief = data.turn_brief || {};
      const route = plan.route_decision || {};
      const model = route.selected_model || {};
      const allowed = data.ok === true;
      decision.textContent = allowed ? 'allowed' : 'blocked';
      decision.className = allowed ? 'v ok' : 'v bad';
      selected.textContent = model.model_id || brief.selected_model || 'none';
      selected.className = selected.textContent !== 'none' ? 'v ok' : 'v bad';
      grants.textContent = plan.tool_grants ? plan.tool_grants.length : (brief.tool_grants || 0);
      obligations.textContent = plan.obligations ? plan.obligations.length : (brief.obligation_count || 0);
      if (brief.operator_checklist) renderChecklist(brief.operator_checklist);
      nextGate.textContent = data.operator_gate ? data.operator_gate.next_gate : (allowed ? 'execute_with_audit' : 'revise_request');
    }
    async function postJson(path, payload) {
      const response = await fetch(path, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      });
      return response.json();
    }
    async function submit(includeRoute) {
      let payload;
      try {
        payload = readPayload(includeRoute);
      } catch (error) {
        setResult({ok: false, error: error.message});
        return;
      }
      setResult(await postJson(includeRoute ? '/api/plan' : '/api/evaluate', payload));
    }
    async function matrix() {
      const [cap, capErr] = safeJson(capsule.value);
      const [req, reqErr] = safeJson(request.value);
      if (capErr || reqErr) { setResult({ok: false, error: capErr || reqErr}); return; }
      const data = await postJson('/api/policy-matrix', {capsule: cap, request: req});
      renderMatrix(data);
      writeJson(output, data);
    }
    async function toolCheck() {
      const [cap, capErr] = safeJson(capsule.value);
      const [req, reqErr] = safeJson(request.value);
      if (capErr || reqErr) { setResult({ok: false, error: capErr || reqErr}); return; }
      const tool = state.tool_scenarios[Number(toolScenario.value)];
      setResult(await postJson('/api/tool-check', {capsule: cap, request: req, tool}));
    }
    async function providerConfig() {
      const data = await postJson('/api/opencode-config', {base_url: 'http://127.0.0.1:8787/v1'});
      writeJson(provider, data.config);
      writeJson(output, data);
    }
    document.getElementById('planBtn').addEventListener('click', () => submit(true));
    document.getElementById('evaluateBtn').addEventListener('click', () => submit(false));
    document.getElementById('matrixBtn').addEventListener('click', matrix);
    document.getElementById('providerBtn').addEventListener('click', providerConfig);
    document.getElementById('restrictedBtn').addEventListener('click', loadRestricted);
    document.getElementById('personalBtn').addEventListener('click', loadPersonal);
    toolScenario.addEventListener('change', toolCheck);
    loadRestricted();
    renderMatrix(state.policy_matrix);
    writeJson(provider, state.opencode_config);
    writeJson(output, {status: 'ready', registry: state.registry_path});
  </script>
</body>
</html>"""
    return html.replace("__INITIAL__", initial)


def build_dashboard_html(state: dict[str, Any]) -> str:
    initial = json.dumps(state, sort_keys=True).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AbteeX SovereignCode</title>
  <style>
    :root {{
      --paper: #fffefa;
      --ink: #0a0a0b;
      --muted: #726b62;
      --rule: #ded6c8;
      --amber: #e08a2c;
      --amber-dark: #9a5416;
      --green: #275f45;
      --red: #8f2e24;
      --panel: #f7f1e7;
      --mono: "Cascadia Code", "SFMono-Regular", Menlo, Consolas, monospace;
      --serif: Georgia, "Iowan Old Style", "Palatino Linotype", serif;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font-family: var(--serif);
    }}
    .shell {{
      min-height: 100vh;
      display: grid;
      grid-template-rows: auto 1fr;
    }}
    header {{
      border-bottom: 1px solid var(--rule);
      padding: 18px 28px 14px;
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 20px;
      align-items: end;
    }}
    h1 {{
      font-size: clamp(28px, 4vw, 50px);
      line-height: .95;
      margin: 0;
      letter-spacing: 0;
    }}
    .subtitle, .meta, label, button, select {{
      font-family: var(--mono);
      font-size: 12px;
      letter-spacing: 0;
    }}
    .subtitle {{ color: var(--muted); margin-top: 8px; }}
    .meta {{
      display: grid;
      grid-template-columns: repeat(3, minmax(110px, 1fr));
      gap: 8px;
      min-width: min(430px, 44vw);
    }}
    .metric {{
      border-left: 2px solid var(--amber);
      padding: 4px 0 4px 10px;
    }}
    .metric strong {{
      display: block;
      font-size: 20px;
      font-family: var(--serif);
    }}
    main {{
      display: grid;
      grid-template-columns: minmax(380px, 45vw) 1fr;
      min-height: 0;
    }}
    .left, .right {{ padding: 22px; min-width: 0; }}
    .left {{ border-right: 1px solid var(--rule); background: #fffaf2; }}
    .toolbar {{
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
      margin-bottom: 12px;
    }}
    .editor-grid {{
      display: grid;
      gap: 12px;
    }}
    textarea, pre, .card {{
      border: 1px solid var(--rule);
      background: var(--paper);
      color: var(--ink);
      border-radius: 6px;
    }}
    textarea {{
      width: 100%;
      min-height: 170px;
      resize: vertical;
      padding: 12px;
      font-family: var(--mono);
      font-size: 12px;
      line-height: 1.45;
    }}
    #routeRequest {{ min-height: 138px; }}
    button {{
      appearance: none;
      border: 1px solid var(--ink);
      background: var(--ink);
      color: var(--paper);
      border-radius: 4px;
      min-height: 34px;
      padding: 0 12px;
      cursor: pointer;
    }}
    button.secondary {{ background: transparent; color: var(--ink); border-color: var(--rule); }}
    .status {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 14px;
    }}
    .card {{ padding: 14px; min-height: 86px; }}
    .card b {{ display: block; font-size: 12px; font-family: var(--mono); color: var(--muted); }}
    .card span {{ display: block; margin-top: 8px; font-size: 18px; overflow-wrap: anywhere; }}
    pre {{
      margin: 0;
      padding: 16px;
      min-height: 590px;
      max-height: 72vh;
      overflow: auto;
      font-family: var(--mono);
      font-size: 12px;
      line-height: 1.45;
    }}
    .ok {{ color: var(--green); }}
    .bad {{ color: var(--red); }}
    @media (max-width: 980px) {{
      header, main {{ grid-template-columns: 1fr; }}
      .meta {{ min-width: 0; grid-template-columns: repeat(3, 1fr); }}
      .left {{ border-right: 0; border-bottom: 1px solid var(--rule); }}
      pre {{ min-height: 360px; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <div>
        <h1>AbteeX<br />SovereignCode</h1>
        <div class="subtitle">Data Capsule policy, model route, tool grants, audit trace</div>
      </div>
      <div class="meta">
        <div class="metric"><strong id="modelCount">0</strong>models</div>
        <div class="metric"><strong>NZ</strong>resident default</div>
        <div class="metric"><strong>0</strong>export default</div>
      </div>
    </header>
    <main>
      <section class="left">
        <div class="toolbar">
          <button id="planBtn">Plan Turn</button>
          <button class="secondary" id="evaluateBtn">Evaluate</button>
          <button class="secondary" id="restrictedBtn">Restricted</button>
          <button class="secondary" id="personalBtn">Personal</button>
        </div>
        <div class="editor-grid">
          <div>
            <label for="capsule">DATA CAPSULE</label>
            <textarea id="capsule" spellcheck="false"></textarea>
          </div>
          <div>
            <label for="request">SOVEREIGN REQUEST</label>
            <textarea id="request" spellcheck="false"></textarea>
          </div>
          <div>
            <label for="routeRequest">ROUTE REQUEST</label>
            <textarea id="routeRequest" spellcheck="false"></textarea>
          </div>
        </div>
      </section>
      <section class="right">
        <div class="status">
          <div class="card"><b>DECISION</b><span id="decision">pending</span></div>
          <div class="card"><b>MODEL</b><span id="selected">pending</span></div>
          <div class="card"><b>TOOL GRANTS</b><span id="grants">0</span></div>
        </div>
        <pre id="output"></pre>
      </section>
    </main>
  </div>
  <script type="application/json" id="initial-state">{initial}</script>
  <script>
    const state = JSON.parse(document.getElementById('initial-state').textContent);
    const capsule = document.getElementById('capsule');
    const request = document.getElementById('request');
    const routeRequest = document.getElementById('routeRequest');
    const output = document.getElementById('output');
    const decision = document.getElementById('decision');
    const selected = document.getElementById('selected');
    const grants = document.getElementById('grants');
    document.getElementById('modelCount').textContent = state.model_count;

    function loadRestricted() {{
      capsule.value = JSON.stringify(state.capsule, null, 2);
      request.value = JSON.stringify(state.request, null, 2);
      routeRequest.value = JSON.stringify(state.route_request, null, 2);
    }}
    function loadPersonal() {{
      capsule.value = JSON.stringify(state.personal_capsule, null, 2);
      request.value = JSON.stringify(state.personal_request, null, 2);
      routeRequest.value = JSON.stringify(state.route_request, null, 2);
    }}
    loadRestricted();
    output.textContent = JSON.stringify({{status: 'ready', registry: state.registry_path}}, null, 2);

    function readPayload(includeRoute) {{
      const payload = {{
        capsule: JSON.parse(capsule.value),
        request: JSON.parse(request.value)
      }};
      if (includeRoute) payload.route_request = JSON.parse(routeRequest.value);
      return payload;
    }}
    function setResult(data) {{
      output.textContent = JSON.stringify(data, null, 2);
      const allowed = data.ok === true;
      decision.textContent = allowed ? 'allowed' : 'blocked';
      decision.className = allowed ? 'ok' : 'bad';
      const plan = data.plan || {{}};
      const route = plan.route_decision || {{}};
      const model = route.selected_model;
      selected.textContent = model ? model.model_id : 'none';
      selected.className = model ? 'ok' : 'bad';
      grants.textContent = plan.tool_grants ? plan.tool_grants.length : 0;
    }}
    async function submit(includeRoute) {{
      let payload;
      try {{
        payload = readPayload(includeRoute);
      }} catch (error) {{
        setResult({{ok: false, error: error.message}});
        return;
      }}
      const response = await fetch(includeRoute ? '/api/plan' : '/api/evaluate', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify(payload)
      }});
      setResult(await response.json());
    }}
    document.getElementById('planBtn').addEventListener('click', () => submit(true));
    document.getElementById('evaluateBtn').addEventListener('click', () => submit(false));
    document.getElementById('restrictedBtn').addEventListener('click', loadRestricted);
    document.getElementById('personalBtn').addEventListener('click', loadPersonal);
  </script>
</body>
</html>"""


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _fallback_personal_capsule() -> dict[str, Any]:
    return {
        "capsule_id": "cap-personal-profile-001",
        "subject_id": "operator-local-profile",
        "jurisdiction": "NZ",
        "sensitivity": "personal",
        "allowed_purposes": ["personal_memory", "coding_assistance"],
        "resident_regions": ["NZ"],
        "data_classes": ["personal", "preferences", "source_code"],
        "retention_days": 7,
        "export_allowed": False,
        "training_allowed": False,
        "personal_detail_level": "pseudonymous",
        "consent_scopes": ["personal_memory", "coding_assistance"],
    }


def _fallback_personal_request() -> dict[str, Any]:
    return {
        "actor": "developer",
        "purpose": "personal_memory",
        "action": "read_context",
        "region": "NZ",
        "model_id": "local/lumynax",
        "data_classes": ["personal", "preferences"],
        "personal_detail_level": "pseudonymous",
        "consent_scope": "personal_memory",
    }
