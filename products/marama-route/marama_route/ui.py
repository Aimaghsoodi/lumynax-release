from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ._ui_server import serve_dashboard

from .platform import (
    build_models_api,
    build_opencode_provider_config,
    build_registry_analytics,
    catalog_models,
    compare_models,
    route_or_chat_payload,
    route_scenario_matrix,
    scenario_presets,
)
from .registry import load_model_registry

PRODUCT_NAME = "LumynaX MaramaRoute"
PACKAGE_ROOT = Path(__file__).resolve().parent
PACKAGE_PARENT = PACKAGE_ROOT.parent


def default_registry_path() -> Path:
    candidates = [
        Path.cwd() / "products" / "lumynax-marama-route" / "configs" / "lumynax_model_registry.json",
        Path.cwd() / "configs" / "lumynax_model_registry.json",
        PACKAGE_ROOT / "configs" / "lumynax_model_registry.json",
        PACKAGE_PARENT / "configs" / "lumynax_model_registry.json",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def default_chat_request_path() -> Path:
    candidates = [
        Path.cwd() / "products" / "lumynax-marama-route" / "examples" / "request.chat-code.json",
        Path.cwd() / "examples" / "request.chat-code.json",
        PACKAGE_ROOT / "examples" / "request.chat-code.json",
        PACKAGE_PARENT / "examples" / "request.chat-code.json",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def load_json_mapping(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


def route_dashboard_payload(payload: dict[str, Any], registry_path: Path) -> dict[str, Any]:
    return route_or_chat_payload(payload, load_model_registry(registry_path))


def build_dashboard_state(registry_path: Path) -> dict[str, Any]:
    models = load_model_registry(registry_path)
    example = (
        load_json_mapping(default_chat_request_path())
        if default_chat_request_path().exists()
        else _fallback_chat_example()
    )
    analytics = build_registry_analytics(models)
    return {
        "registry_path": str(registry_path),
        "model_count": len(models),
        "resident_nz": analytics["resident_nz"],
        "runtimes": sorted(analytics["runtimes"]),
        "example": example,
        "models": build_models_api(models),
        "analytics": analytics,
        "catalog": catalog_models(models, {"limit": 14})["models"],
        "scenarios": scenario_presets(),
        "matrix": route_scenario_matrix(models),
        "opencode_config": build_opencode_provider_config(models),
    }


def handle_api_request(
    method: str,
    path: str,
    payload: dict[str, Any] | None,
    registry_path: Path,
) -> tuple[int, dict[str, Any]]:
    if method == "GET" and path == "/api/health":
        state = build_dashboard_state(registry_path)
        return 200, {"ok": True, "product": PRODUCT_NAME, "model_count": state["model_count"]}
    if method == "GET" and path == "/api/models":
        return 200, build_models_api(load_model_registry(registry_path))
    if method == "GET" and path == "/api/analytics":
        return 200, {"ok": True, **build_registry_analytics(load_model_registry(registry_path))}
    if method == "GET" and path == "/api/state":
        return 200, {"ok": True, **build_dashboard_state(registry_path)}
    if method == "POST" and path == "/api/route" and payload is not None:
        status = 200
        result = route_dashboard_payload(payload, registry_path)
        if not result["ok"]:
            status = 422
        return status, result
    if method == "POST" and path == "/api/catalog" and payload is not None:
        return 200, catalog_models(load_model_registry(registry_path), payload)
    if method == "POST" and path == "/api/compare" and payload is not None:
        model_ids = payload.get("model_ids") or payload.get("models") or []
        if isinstance(model_ids, str):
            model_ids = [item.strip() for item in model_ids.split(",") if item.strip()]
        request_payload = payload.get("request") if isinstance(payload.get("request"), dict) else None
        result = compare_models(load_model_registry(registry_path), list(model_ids), request_payload)
        return (200 if result["ok"] else 422), result
    if method == "POST" and path == "/api/matrix" and payload is not None:
        scenarios = payload.get("scenarios") if isinstance(payload.get("scenarios"), list) else None
        return 200, route_scenario_matrix(load_model_registry(registry_path), scenarios)
    if method == "POST" and path == "/api/opencode-config" and payload is not None:
        return 200, {
            "ok": True,
            "config": build_opencode_provider_config(
                load_model_registry(registry_path),
                base_url=str(payload.get("base_url") or "http://127.0.0.1:8787/v1"),
            ),
        }
    return 404, {"ok": False, "error": "not_found"}


def smoke_ui(registry_path: Path | None = None) -> dict[str, Any]:
    resolved_registry = registry_path or default_registry_path()
    state = build_dashboard_state(resolved_registry)
    routed = route_dashboard_payload(state["example"], resolved_registry)
    if not routed["ok"]:
        raise RuntimeError("MaramaRoute UI smoke route did not select a model")
    catalog = catalog_models(load_model_registry(resolved_registry), {"task_type": "code", "limit": 3})
    matrix = route_scenario_matrix(load_model_registry(resolved_registry))
    if not catalog["models"] or not matrix["ok"]:
        raise RuntimeError("MaramaRoute expanded UI smoke checks failed")
    return {
        "ok": True,
        "product": PRODUCT_NAME,
        "model_count": state["model_count"],
        "selected_model": routed["route_decision"]["selected_model"]["model_id"],
        "catalog_count": catalog["count"],
        "scenario_count": len(matrix["scenarios"]),
    }


def run_ui(
    *,
    registry_path: Path | None = None,
    host: str = "127.0.0.1",
    port: int = 8787,
    open_browser: bool = False,
    smoke: bool = False,
) -> int:
    resolved_registry = registry_path or default_registry_path()
    if smoke:
        print(json.dumps(smoke_ui(resolved_registry), indent=2, sort_keys=True))
        return 0
    html = build_expanded_dashboard_html(build_dashboard_state(resolved_registry))
    return serve_dashboard(
        product_name=PRODUCT_NAME,
        html=html,
        api_handler=lambda method, path, payload: handle_api_request(
            method,
            path,
            payload,
            resolved_registry,
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
  <title>LumynaX MaramaRoute Console</title>
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
        linear-gradient(90deg, rgba(10,10,11,.035) 1px, transparent 1px) 0 0 / 44px 44px,
        linear-gradient(0deg, rgba(10,10,11,.025) 1px, transparent 1px) 0 0 / 44px 44px,
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
    .subtitle, label, button, input, select, .metric, .pill, th, td {
      font-family: var(--mono);
      font-size: 12px;
      letter-spacing: 0;
    }
    .subtitle { margin-top: 10px; color: var(--muted); }
    .metrics { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px; }
    .metric { border-left: 2px solid var(--amber); min-height: 60px; padding: 7px 8px; background: rgba(247,241,231,.72); }
    .metric strong { display: block; font: 700 22px/1 var(--serif); color: var(--ink); overflow-wrap: anywhere; }
    main { display: grid; grid-template-columns: minmax(340px, 440px) 1fr; min-height: calc(100vh - 118px); }
    aside { border-right: 1px solid var(--rule); background: rgba(255,250,242,.95); padding: 18px; }
    section { min-width: 0; }
    .stack { display: grid; gap: 12px; }
    .grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
    .wide { grid-column: 1 / -1; }
    .panel, textarea, input, select, pre, table { border: 1px solid var(--rule); border-radius: 6px; background: var(--paper); color: var(--ink); }
    .panel { padding: 14px; }
    .panel h2 { margin: 0 0 10px; font-size: 18px; line-height: 1.1; }
    textarea {
      width: 100%;
      min-height: 270px;
      resize: vertical;
      padding: 12px;
      font: 12px/1.45 var(--mono);
    }
    input, select { width: 100%; min-height: 34px; padding: 0 10px; }
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
    .content { padding: 18px; display: grid; gap: 12px; align-content: start; }
    .status { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
    .status .panel { min-height: 92px; }
    .k { font: 12px/1.25 var(--mono); color: var(--muted); display: block; }
    .v { display: block; margin-top: 8px; font-size: 18px; line-height: 1.12; overflow-wrap: anywhere; }
    .ok { color: var(--green); }
    .bad { color: var(--red); }
    pre { margin: 0; padding: 14px; max-height: 520px; overflow: auto; font: 12px/1.45 var(--mono); }
    table { width: 100%; border-collapse: collapse; overflow: hidden; }
    th, td { padding: 9px 10px; text-align: left; border-bottom: 1px solid var(--rule); vertical-align: top; }
    th { color: var(--muted); background: var(--panel); }
    tr:last-child td { border-bottom: 0; }
    .pills { display: flex; flex-wrap: wrap; gap: 6px; }
    .pill { display: inline-flex; border: 1px solid var(--rule); border-radius: 999px; min-height: 24px; align-items: center; padding: 0 9px; background: var(--chalk); }
    .split { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 12px; }
    @media (max-width: 1120px) {
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
      <h1>LumynaX<br />MaramaRoute</h1>
      <div class="subtitle">Sovereign router control surface for LumynaX model selection.</div>
    </div>
    <div class="metrics">
      <div class="metric"><strong id="metricModels">0</strong>models</div>
      <div class="metric"><strong id="metricNz">0</strong>NZ resident</div>
      <div class="metric"><strong id="metricLocal">0</strong>local runtime</div>
      <div class="metric"><strong id="metricJson">0</strong>JSON ready</div>
      <div class="metric"><strong id="metricContext">0</strong>max ctx</div>
    </div>
  </header>
  <main>
    <aside class="stack">
      <div class="toolbar">
        <button id="routeBtn">Route</button>
        <button class="secondary" id="matrixBtn">Matrix</button>
        <button class="secondary" id="providerBtn">Provider</button>
      </div>
      <div>
        <label for="preset">PRESET</label>
        <select id="preset"></select>
      </div>
      <div>
        <label for="request">REQUEST JSON</label>
        <textarea id="request" spellcheck="false"></textarea>
      </div>
      <div class="panel stack">
        <h2>Catalog</h2>
        <div class="grid">
          <div>
            <label for="search">SEARCH</label>
            <input id="search" value="qwen" />
          </div>
          <div>
            <label for="task">TASK</label>
            <select id="task">
              <option value="">any</option>
              <option value="code">code</option>
              <option value="reasoning">reasoning</option>
              <option value="multimodal">multimodal</option>
              <option value="general">general</option>
            </select>
          </div>
          <div>
            <label for="runtime">RUNTIME</label>
            <select id="runtime"></select>
          </div>
          <div>
            <label for="context">MIN CONTEXT</label>
            <input id="context" type="number" min="0" value="4096" />
          </div>
        </div>
        <div class="toolbar">
          <button class="secondary" id="catalogBtn">Filter</button>
          <button class="secondary" id="compareBtn">Compare Top</button>
        </div>
      </div>
    </aside>
    <section class="content">
      <div class="status">
        <div class="panel"><span class="k">SELECTED</span><span class="v" id="selected">pending</span></div>
        <div class="panel"><span class="k">MODE</span><span class="v" id="mode">ready</span></div>
        <div class="panel"><span class="k">FALLBACKS</span><span class="v" id="fallbacks">0</span></div>
        <div class="panel"><span class="k">RECEIPT</span><span class="v" id="receipt">none</span></div>
      </div>
      <div class="split">
        <div class="panel">
          <h2>Route Result</h2>
          <pre id="output"></pre>
        </div>
        <div class="panel">
          <h2>Scenario Matrix</h2>
          <table>
            <thead><tr><th>Scenario</th><th>Model</th><th>Rejected</th></tr></thead>
            <tbody id="matrixRows"></tbody>
          </table>
        </div>
      </div>
      <div class="panel">
        <h2>Model Catalog</h2>
        <table>
          <thead><tr><th>Model</th><th>Runtime</th><th>Fit</th><th>Caps</th></tr></thead>
          <tbody id="catalogRows"></tbody>
        </table>
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
    const request = document.getElementById('request');
    const preset = document.getElementById('preset');
    const output = document.getElementById('output');
    const provider = document.getElementById('provider');
    const selected = document.getElementById('selected');
    const mode = document.getElementById('mode');
    const fallbacks = document.getElementById('fallbacks');
    const receipt = document.getElementById('receipt');
    const catalogRows = document.getElementById('catalogRows');
    const matrixRows = document.getElementById('matrixRows');
    const runtime = document.getElementById('runtime');

    function writeJson(node, value) {
      node.textContent = JSON.stringify(value, null, 2);
    }
    function safeJson(text) {
      try { return [JSON.parse(text), null]; }
      catch (error) { return [null, error.message]; }
    }
    function setMetric(id, value) { document.getElementById(id).textContent = value; }
    setMetric('metricModels', state.analytics.model_count);
    setMetric('metricNz', state.analytics.resident_nz);
    setMetric('metricLocal', state.analytics.local_runtimes);
    setMetric('metricJson', state.analytics.json_ready);
    setMetric('metricContext', state.analytics.max_context_tokens);

    runtime.innerHTML = '<option value="">any</option>' + Object.keys(state.analytics.runtimes).map(item => `<option value="${item}">${item}</option>`).join('');
    preset.innerHTML = state.scenarios.map((item, index) => `<option value="${index}">${item.name}</option>`).join('');
    preset.addEventListener('change', () => {
      request.value = JSON.stringify(state.scenarios[Number(preset.value)], null, 2);
    });
    request.value = JSON.stringify(state.example, null, 2);
    writeJson(output, {status: 'ready', registry: state.registry_path});
    writeJson(provider, state.opencode_config);

    function renderCatalog(rows) {
      catalogRows.innerHTML = rows.map(row => {
        const caps = [
          row.residency.includes('NZ') ? 'NZ' : '',
          row.supports_json ? 'JSON' : '',
          row.supports_tools ? 'TOOLS' : '',
          `${row.context_tokens} ctx`
        ].filter(Boolean).map(item => `<span class="pill">${item}</span>`).join(' ');
        return `<tr><td>${row.model_id}<br><span class="k">${row.repo_id}</span></td><td>${row.runtime}</td><td>${row.operator_score}</td><td><div class="pills">${caps}</div></td></tr>`;
      }).join('');
    }
    function renderMatrix(rows) {
      matrixRows.innerHTML = rows.map(row => `<tr><td>${row.name}<br><span class="k">${row.sensitivity}</span></td><td class="${row.ok ? 'ok' : 'bad'}">${row.selected_model || 'none'}</td><td>${row.rejected_count}</td></tr>`).join('');
    }
    function setResult(data) {
      writeJson(output, data);
      const decision = data.route_decision || {};
      const model = decision.selected_model || {};
      selected.textContent = model.model_id || 'none';
      selected.className = model.model_id ? 'v ok' : 'v bad';
      mode.textContent = data.mode || 'result';
      fallbacks.textContent = decision.fallback_models ? decision.fallback_models.length : 0;
      receipt.textContent = data.receipt ? data.receipt.receipt_id : 'none';
    }
    async function postJson(path, payload) {
      const response = await fetch(path, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      });
      return response.json();
    }
    async function route() {
      const [payload, error] = safeJson(request.value);
      if (error) { setResult({ok: false, error}); return; }
      setResult(await postJson('/api/route', payload));
    }
    async function loadCatalog() {
      const filters = {
        search: document.getElementById('search').value,
        task_type: document.getElementById('task').value,
        runtime: runtime.value,
        min_context_tokens: Number(document.getElementById('context').value || 0),
        jurisdiction: 'NZ',
        limit: 18
      };
      const data = await postJson('/api/catalog', filters);
      renderCatalog(data.models);
      writeJson(output, data);
    }
    async function compareTop() {
      const ids = Array.from(catalogRows.querySelectorAll('tr')).slice(0, 4).map(row => row.cells[0].childNodes[0].textContent);
      const data = await postJson('/api/compare', {model_ids: ids});
      writeJson(output, data);
      if (data.winner) {
        selected.textContent = data.winner.model_id;
        selected.className = 'v ok';
        mode.textContent = 'compare';
      }
    }
    async function matrix() {
      const data = await postJson('/api/matrix', {scenarios: state.scenarios});
      renderMatrix(data.scenarios);
      writeJson(output, data);
    }
    async function providerConfig() {
      const data = await postJson('/api/opencode-config', {base_url: 'http://127.0.0.1:8787/v1'});
      writeJson(provider, data.config);
      writeJson(output, data);
    }
    document.getElementById('routeBtn').addEventListener('click', route);
    document.getElementById('catalogBtn').addEventListener('click', loadCatalog);
    document.getElementById('compareBtn').addEventListener('click', compareTop);
    document.getElementById('matrixBtn').addEventListener('click', matrix);
    document.getElementById('providerBtn').addEventListener('click', providerConfig);
    renderCatalog(state.catalog);
    renderMatrix(state.matrix.scenarios);
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
  <title>LumynaX MaramaRoute</title>
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
      font-size: clamp(28px, 4vw, 48px);
      line-height: .95;
      margin: 0;
      letter-spacing: 0;
      font-weight: 700;
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
      grid-template-columns: minmax(330px, 42vw) 1fr;
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
    textarea, pre, .card {{
      border: 1px solid var(--rule);
      background: var(--paper);
      color: var(--ink);
      border-radius: 6px;
    }}
    textarea {{
      width: 100%;
      min-height: 560px;
      resize: vertical;
      padding: 14px;
      font-family: var(--mono);
      font-size: 12px;
      line-height: 1.45;
    }}
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
      min-height: 520px;
      max-height: 68vh;
      overflow: auto;
      font-family: var(--mono);
      font-size: 12px;
      line-height: 1.45;
    }}
    .ok {{ color: var(--green); }}
    .bad {{ color: var(--red); }}
    @media (max-width: 920px) {{
      header, main {{ grid-template-columns: 1fr; }}
      .meta {{ min-width: 0; grid-template-columns: repeat(3, 1fr); }}
      .left {{ border-right: 0; border-bottom: 1px solid var(--rule); }}
      textarea {{ min-height: 360px; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <div>
        <h1>LumynaX<br />MaramaRoute</h1>
        <div class="subtitle">Sovereign model router for AbteeXAILab Hugging Face releases</div>
      </div>
      <div class="meta">
        <div class="metric"><strong id="modelCount">0</strong>models</div>
        <div class="metric"><strong id="residentCount">0</strong>NZ resident</div>
        <div class="metric"><strong id="runtimeCount">0</strong>runtimes</div>
      </div>
    </header>
    <main>
      <section class="left">
        <div class="toolbar">
          <button id="routeBtn">Route</button>
          <button class="secondary" id="exampleBtn">Example</button>
          <button class="secondary" id="modelsBtn">Models</button>
        </div>
        <label for="request">REQUEST JSON</label>
        <textarea id="request" spellcheck="false"></textarea>
      </section>
      <section class="right">
        <div class="status">
          <div class="card"><b>SELECTED</b><span id="selected">pending</span></div>
          <div class="card"><b>MODE</b><span id="mode">pending</span></div>
          <div class="card"><b>REJECTED</b><span id="rejected">0</span></div>
        </div>
        <pre id="output"></pre>
      </section>
    </main>
  </div>
  <script type="application/json" id="initial-state">{initial}</script>
  <script>
    const state = JSON.parse(document.getElementById('initial-state').textContent);
    const request = document.getElementById('request');
    const output = document.getElementById('output');
    const selected = document.getElementById('selected');
    const mode = document.getElementById('mode');
    const rejected = document.getElementById('rejected');
    document.getElementById('modelCount').textContent = state.model_count;
    document.getElementById('residentCount').textContent = state.resident_nz;
    document.getElementById('runtimeCount').textContent = state.runtimes.length;
    request.value = JSON.stringify(state.example, null, 2);
    output.textContent = JSON.stringify({{status: 'ready', registry: state.registry_path}}, null, 2);

    function setResult(data) {{
      output.textContent = JSON.stringify(data, null, 2);
      const decision = data.route_decision || {{}};
      const model = decision.selected_model || (data.marama_route || {{}}).selected_model;
      selected.textContent = model ? model.model_id : 'none';
      selected.className = model ? 'ok' : 'bad';
      mode.textContent = data.mode || 'models';
      rejected.textContent = decision.rejected ? decision.rejected.length : 0;
    }}

    async function postRoute() {{
      let payload;
      try {{
        payload = JSON.parse(request.value);
      }} catch (error) {{
        setResult({{ok: false, error: error.message}});
        return;
      }}
      const response = await fetch('/api/route', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify(payload)
      }});
      setResult(await response.json());
    }}

    async function getModels() {{
      const response = await fetch('/api/models');
      setResult(await response.json());
    }}

    document.getElementById('routeBtn').addEventListener('click', postRoute);
    document.getElementById('exampleBtn').addEventListener('click', () => {{
      request.value = JSON.stringify(state.example, null, 2);
    }});
    document.getElementById('modelsBtn').addEventListener('click', getModels);
  </script>
</body>
</html>"""


def _fallback_chat_example() -> dict[str, Any]:
    return {
        "model": "lumynax/code",
        "messages": [
            {
                "role": "user",
                "content": "Refactor this private Python service and return a JSON diff plan.",
            },
        ],
        "response_format": {"type": "json_object"},
        "route": {
            "jurisdiction": "NZ",
            "data_sensitivity": "restricted",
            "task_type": "code",
            "requires_local": True,
            "requires_json": True,
            "max_fallbacks": 3,
        },
    }
