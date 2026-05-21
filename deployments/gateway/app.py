"""
LumynaX AI gateway — OpenAI-compatible facade in front of multiple model servers.

- One /v1/chat/completions endpoint, routes by `model` field in request body.
- Each registered model has its own backend (llama-server / vLLM / HF text-generation).
- Authenticated by per-tenant API keys (Bearer token).
- Every request runs through SovereignCode policy gates (residency, purpose, training, export).
- Tool-capable models get a `web_search` tool wired to self-hosted SearXNG.
- Hash-chained audit log to stdout (and optional file).

Run:  uvicorn app:app --host 0.0.0.0 --port 8080
Env:  GATEWAY_REGISTRY_PATH, GATEWAY_API_KEYS_PATH, GATEWAY_AUDIT_LOG, SEARXNG_URL,
      HF_TOKEN (for fetching registry from HF if path not set)
"""
from __future__ import annotations
import asyncio, hashlib, json, os, time, uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Optional

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

# ---------- config ----------
REGISTRY_PATH = os.environ.get("GATEWAY_REGISTRY_PATH", "/data/registry.json")
API_KEYS_PATH = os.environ.get("GATEWAY_API_KEYS_PATH", "/data/api-keys.json")
ROUTES_PATH   = os.environ.get("GATEWAY_ROUTES_PATH", "/data/routes.json")
AUDIT_LOG     = os.environ.get("GATEWAY_AUDIT_LOG", "/data/audit.log")
SEARXNG_URL   = os.environ.get("SEARXNG_URL", "http://searxng:8080")
BIND_HOST     = os.environ.get("GATEWAY_HOST", "0.0.0.0")
BIND_PORT     = int(os.environ.get("GATEWAY_PORT", "8080"))

# ---------- state ----------
state: dict[str, Any] = {"registry": {}, "api_keys": {}, "routes": {}, "audit_last_hash": "GENESIS"}
http: httpx.AsyncClient | None = None


def _load_json(path: str, default):
    p = Path(path)
    if not p.exists(): return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[gateway] WARN: failed to load {path}: {e}")
        return default


def _save_json(path: str, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global http
    http = httpx.AsyncClient(timeout=httpx.Timeout(connect=10, read=600, write=120, pool=10))
    state["registry"] = _load_json(REGISTRY_PATH, {"models": []})
    state["api_keys"] = _load_json(API_KEYS_PATH, {})
    state["routes"]   = _load_json(ROUTES_PATH,   {})
    print(f"[gateway] loaded {len(state['registry'].get('models', []))} models, "
          f"{len(state['api_keys'])} api keys, {len(state['routes'])} routes")
    yield
    await http.aclose()


app = FastAPI(title="LumynaX Gateway", version="0.2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
auth = HTTPBearer(auto_error=True)

# ---------- audit ----------
def audit(event: dict) -> None:
    """Append a hash-chained audit record."""
    canon = json.dumps(event, sort_keys=True, separators=(",", ":"))
    chain_in = state["audit_last_hash"] + canon
    h = hashlib.sha256(chain_in.encode()).hexdigest()
    record = {"ts": time.time(), "prev": state["audit_last_hash"], "hash": h, **event}
    state["audit_last_hash"] = h
    line = json.dumps(record, separators=(",", ":"))
    print(f"[audit] {line}")
    try:
        with open(AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception: pass


# ---------- auth ----------
def authn(creds: HTTPAuthorizationCredentials = Depends(auth)) -> dict[str, Any]:
    token = creds.credentials
    info = state["api_keys"].get(token)
    if not info:
        # graceful single-tenant default for dev: anonymous if token == "lumynax-local"
        if token == "lumynax-local":
            return {"tenant": "local", "policies": ["allow-all"], "rate_limit": 0}
        raise HTTPException(401, "invalid api key")
    return {"tenant": info.get("tenant","unknown"), **info}


# ---------- policy ----------
def policy_check(req_body: dict, tenant: dict, model: dict) -> Optional[str]:
    """Run SovereignCode-style policy gates. Returns None if allowed, str reason if denied."""
    # Tenant-scoped capsule from api-keys.json["policies"][...]
    pols = tenant.get("policies", [])
    if "allow-all" in pols: return None
    # Jurisdiction check
    jur = tenant.get("jurisdiction", "NZ")
    if jur not in (model.get("residency") or []):
        return f"model residency {model.get('residency')} excludes tenant jurisdiction {jur}"
    # Sovereignty tier
    min_tier = tenant.get("min_sovereignty_tier")
    if min_tier and (model.get("sovereignty_tier") or 0) < min_tier:
        return f"model sovereignty_tier={model.get('sovereignty_tier')} below tenant minimum {min_tier}"
    # Required tools / json
    if req_body.get("tools") and not model.get("supports_tools"):
        return f"request uses tools but model {model['model_id']} doesn't support tools"
    # Training-data flag (custom extension)
    if req_body.get("metadata", {}).get("for_training") and "allow-training" not in pols:
        return "training-flagged request not allowed by tenant policy"
    return None


# ---------- routing ----------
def find_model(model_id: str) -> Optional[dict]:
    """Look up by repo slug, full repo_id, or model_id field."""
    if not model_id: return None
    target = model_id.replace("AbteeXAILab/", "").lower()
    for m in state["registry"].get("models", []):
        slug = m["repo_id"].split("/")[-1].lower()
        if slug == target or m.get("model_id","").lower() == target or m["repo_id"].lower() == model_id.lower():
            return m
    return None


def backend_url_for(model: dict) -> Optional[str]:
    """Find configured backend URL for this model from routes.json."""
    slug = model["repo_id"].split("/")[-1]
    return state["routes"].get(slug) or state["routes"].get(model["repo_id"])


# ---------- tools: web search ----------
WEB_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": ("Search the web via self-hosted SearXNG. Returns the top matching "
                        "pages with title, URL, and snippet. Use sparingly; the model is "
                        "expected to cite results."),
        "parameters": {
            "type": "object",
            "properties": {
                "query":    {"type": "string", "description": "Search query."},
                "max_results": {"type": "integer", "description": "How many results to return (1-10).", "default": 5},
                "lang":     {"type": "string",  "description": "ISO-639 language code, e.g. 'en'.", "default": "en"},
            },
            "required": ["query"],
        },
    },
}


async def run_web_search(query: str, max_results: int = 5, lang: str = "en") -> list[dict]:
    """Hit local SearXNG; return structured results."""
    params = {"q": query, "format": "json", "language": lang, "safesearch": 1}
    r = await http.get(f"{SEARXNG_URL}/search", params=params)
    r.raise_for_status()
    data = r.json()
    out = []
    for item in (data.get("results") or [])[:max_results]:
        out.append({
            "title":   item.get("title"),
            "url":     item.get("url"),
            "snippet": item.get("content") or item.get("snippet"),
            "engine":  item.get("engine"),
        })
    return out


# ---------- OpenAI shapes ----------
class ChatMessage(BaseModel):
    role: str
    content: Any = None
    name: Optional[str] = None
    tool_calls: Optional[list[dict]] = None
    tool_call_id: Optional[str] = None


class ChatRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    stream: bool = False
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    tools: Optional[list[dict]] = None
    tool_choice: Optional[Any] = None
    response_format: Optional[dict] = None
    user: Optional[str] = None
    metadata: Optional[dict] = None
    enable_web_search: Optional[bool] = Field(
        None, description="If true and the model supports tools, inject the web_search tool definition."
    )


# ---------- endpoints ----------
@app.get("/health")
async def health():
    return {"ok": True, "models": len(state["registry"].get("models", [])),
            "routes": len(state["routes"])}


@app.get("/v1/models")
async def list_models(tenant: dict = Depends(authn)):
    jur = tenant.get("jurisdiction", "NZ")
    out = []
    for m in state["registry"].get("models", []):
        if jur not in (m.get("residency") or []) and "allow-all" not in tenant.get("policies", []):
            continue
        out.append({
            "id": m["repo_id"].split("/")[-1],
            "object": "model",
            "created": int(time.time()),
            "owned_by": "AbteeX AI Labs",
            "lumynax": {
                "context_window": m.get("context_tokens"),
                "supports_tools": m.get("supports_tools"),
                "supports_json": m.get("supports_json"),
                "modalities": m.get("modalities"),
                "sovereignty_tier": m.get("sovereignty_tier"),
                "residency": m.get("residency"),
                "license": m.get("license_id"),
            },
        })
    return {"object": "list", "data": out}


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatRequest, raw: Request, tenant: dict = Depends(authn)):
    request_id = f"chatcmpl-lumynax-{uuid.uuid4().hex[:16]}"
    model = find_model(req.model)
    if not model:
        audit({"request_id": request_id, "tenant": tenant["tenant"], "event": "model_not_found", "asked": req.model})
        raise HTTPException(404, f"model not found: {req.model}")
    backend = backend_url_for(model)
    if not backend:
        audit({"request_id": request_id, "tenant": tenant["tenant"], "event": "no_backend", "model": model["repo_id"]})
        raise HTTPException(503, f"no backend configured for model {model['repo_id']}")
    # policy
    body = req.model_dump(exclude_none=True)
    deny_reason = policy_check(body, tenant, model)
    if deny_reason:
        audit({"request_id": request_id, "tenant": tenant["tenant"], "event": "policy_deny", "model": model["repo_id"], "reason": deny_reason})
        raise HTTPException(403, f"policy denied: {deny_reason}")
    # inject web_search tool if requested
    inject_web = bool(req.enable_web_search) and bool(model.get("supports_tools"))
    if inject_web:
        body.setdefault("tools", [])
        if not any(t.get("function", {}).get("name") == "web_search" for t in body["tools"]):
            body["tools"].append(WEB_SEARCH_TOOL)
    # strip our extensions from the body before forwarding upstream
    body.pop("enable_web_search", None)
    body.pop("metadata", None)
    audit({"request_id": request_id, "tenant": tenant["tenant"], "event": "request",
           "model": model["repo_id"], "backend": backend,
           "messages_n": len(req.messages), "stream": req.stream, "web_search": inject_web})
    # outer agentic loop: if the model emits a web_search tool call, we execute and feed it back, then re-call upstream
    return await _agentic_chat(model, backend, body, request_id, tenant, inject_web)


async def _agentic_chat(model, backend, body, request_id, tenant, web_enabled):
    """Loop: post → check for tool calls we own → execute → re-post. Max 4 hops."""
    messages = list(body["messages"])
    for hop in range(4):
        body["messages"] = messages
        if body.get("stream"):
            # For streaming, we only execute web_search non-streaming; on tool call we'd need to buffer.
            # Simple approach: don't agentic-loop on streaming responses; pass through.
            return StreamingResponse(_stream(backend, body, request_id, tenant), media_type="text/event-stream")
        upstream = await http.post(f"{backend.rstrip('/')}/chat/completions", json=body)
        if upstream.status_code >= 400:
            audit({"request_id": request_id, "tenant": tenant["tenant"], "event": "backend_error",
                   "status": upstream.status_code, "body": upstream.text[:500]})
            return JSONResponse(status_code=upstream.status_code, content={"error": upstream.text[:1000]})
        resp = upstream.json()
        choice = (resp.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        tcs = msg.get("tool_calls") or []
        if web_enabled and tcs and any(tc.get("function", {}).get("name") == "web_search" for tc in tcs):
            messages.append(msg)
            for tc in tcs:
                if tc.get("function", {}).get("name") != "web_search":
                    continue
                try:
                    args = json.loads(tc["function"].get("arguments") or "{}")
                except Exception: args = {}
                try:
                    results = await run_web_search(
                        args.get("query", ""),
                        int(args.get("max_results") or 5),
                        args.get("lang", "en"),
                    )
                except Exception as e:
                    results = [{"error": f"search failed: {e}"}]
                audit({"request_id": request_id, "tenant": tenant["tenant"], "event": "tool_web_search",
                       "query": args.get("query"), "n_results": len(results)})
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id"),
                    "name": "web_search",
                    "content": json.dumps(results),
                })
            continue  # re-call upstream with tool results appended
        # No web_search tool call (or none we handle) → return upstream answer as-is
        resp["id"] = resp.get("id") or request_id
        audit({"request_id": request_id, "tenant": tenant["tenant"], "event": "response",
               "finish_reason": choice.get("finish_reason"), "hops": hop + 1})
        return JSONResponse(content=resp)
    audit({"request_id": request_id, "tenant": tenant["tenant"], "event": "agentic_max_hops"})
    return JSONResponse(status_code=500, content={"error": "agentic loop exceeded 4 hops"})


async def _stream(backend, body, request_id, tenant) -> AsyncIterator[bytes]:
    async with http.stream("POST", f"{backend.rstrip('/')}/chat/completions", json=body) as r:
        async for line in r.aiter_lines():
            if line: yield (line + "\n").encode()
    audit({"request_id": request_id, "tenant": tenant["tenant"], "event": "response_stream_done"})


@app.post("/v1/embeddings")
async def embeddings(payload: dict, tenant: dict = Depends(authn)):
    """Proxy embeddings to whichever backend serves the requested model."""
    model = find_model(payload.get("model", ""))
    if not model:
        raise HTTPException(404, f"model not found: {payload.get('model')}")
    backend = backend_url_for(model)
    if not backend:
        raise HTTPException(503, "no backend configured")
    upstream = await http.post(f"{backend.rstrip('/')}/embeddings", json=payload)
    audit({"tenant": tenant["tenant"], "event": "embeddings", "model": model["repo_id"]})
    return JSONResponse(status_code=upstream.status_code, content=upstream.json())


@app.get("/v1/route")
async def route(prompt: str = "", requires_local: bool = False, requires_tools: bool = False,
                requires_json: bool = False, jurisdiction: str = "NZ",
                modalities: str = "text", tenant: dict = Depends(authn)):
    """MaramaRoute-style endpoint: returns the best model for a request."""
    mods = [m.strip() for m in modalities.split(",") if m.strip()]
    candidates = []
    for m in state["registry"].get("models", []):
        if any(mod not in (m.get("modalities") or []) for mod in mods): continue
        if requires_local and (m.get("sovereignty_tier") or 0) < 3: continue
        if requires_tools and not m.get("supports_tools"): continue
        if requires_json and not m.get("supports_json"): continue
        if jurisdiction not in (m.get("residency") or []): continue
        q = int(m.get("quality_rank") or 5); s = int(m.get("sovereignty_tier") or 3); c = int(m.get("cost_rank") or 5)
        score = (6 - q) * 2 + s * 1.5 + (6 - c) * 0.5
        candidates.append((score, m))
    candidates.sort(key=lambda x: -x[0])
    if not candidates: raise HTTPException(404, "no candidate matches")
    score, pick = candidates[0]
    return {
        "model": pick["repo_id"].split("/")[-1],
        "repo_id": pick["repo_id"],
        "score": score,
        "alternatives": [{"model": m["repo_id"].split("/")[-1], "score": s} for s, m in candidates[1:5]],
    }


@app.post("/v1/tools/web_search")
async def manual_web_search(payload: dict, tenant: dict = Depends(authn)):
    """Direct web search endpoint — useful for clients that want search without going through a model."""
    results = await run_web_search(payload.get("query", ""), int(payload.get("max_results", 5)),
                                    payload.get("lang", "en"))
    audit({"tenant": tenant["tenant"], "event": "direct_web_search", "query": payload.get("query"),
           "n_results": len(results)})
    return {"results": results}


@app.get("/")
async def root():
    return {
        "service": "LumynaX Gateway",
        "version": "0.2.0",
        "endpoints": ["/v1/chat/completions", "/v1/models", "/v1/embeddings", "/v1/route", "/v1/tools/web_search", "/health"],
        "models": len(state["registry"].get("models", [])),
        "configured_backends": len(state["routes"]),
    }
