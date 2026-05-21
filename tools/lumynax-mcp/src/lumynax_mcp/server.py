"""
LumynaX MCP server — exposes the 98-model LumynaX family as MCP tools.

Attach to Claude Desktop / Cursor / Zed / any MCP client by adding to its config:

  {
    "mcpServers": {
      "lumynax": {
        "command": "lumynax-mcp",
        "env": {
          "LUMYNAX_GATEWAY_URL": "http://localhost:8080/v1",
          "LUMYNAX_GATEWAY_KEY": "lumynax-local-dev"
        }
      }
    }
  }

Then the client sees every LumynaX model as a callable tool with full metadata
(modalities, context, sovereignty tier, residency, license).

Tools exposed:
  lumynax_route(prompt, ...)              MaramaRoute scoring; returns best model id
  lumynax_chat(model, messages, ...)      forwards to the gateway
  lumynax_list(filter)                    lists matching models
  lumynax_info(model)                     full metadata for one model
  lumynax_web_search(query)               direct web search via gateway/SearXNG
"""
from __future__ import annotations
import asyncio, json, os
from typing import Any

import httpx
from huggingface_hub import hf_hub_download
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
import mcp.types as t


GATEWAY_URL = os.environ.get("LUMYNAX_GATEWAY_URL", "http://localhost:8080/v1").rstrip("/")
GATEWAY_KEY = os.environ.get("LUMYNAX_GATEWAY_KEY", "lumynax-local-dev")
REGISTRY_REPO = "AbteeXAILab/marama-route"
REGISTRY_PATH = "configs/lumynax_model_registry.json"


def _load_registry() -> dict[str, Any]:
    try:
        p = hf_hub_download(repo_id=REGISTRY_REPO, filename=REGISTRY_PATH,
                            repo_type="model", token=os.environ.get("HF_TOKEN"))
        return json.loads(open(p, encoding="utf-8").read())
    except Exception:
        return {"models": []}


REGISTRY = _load_registry()
HEADERS = {"Authorization": f"Bearer {GATEWAY_KEY}"}

server = Server("lumynax")


@server.list_tools()
async def list_tools() -> list[t.Tool]:
    return [
        t.Tool(
            name="lumynax_route",
            description=(
                f"Pick the best LumynaX model for a request via MaramaRoute scoring. "
                f"There are {len(REGISTRY.get('models', []))} models in the family, gated on "
                f"residency, sovereignty tier, modality, tools, and JSON-mode support. "
                f"Returns the top match plus 4 runners-up."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt":          {"type": "string"},
                    "modalities":      {"type": "array", "items": {"type": "string"}, "default": ["text"]},
                    "requires_local":  {"type": "boolean", "default": False},
                    "requires_tools":  {"type": "boolean", "default": False},
                    "requires_json":   {"type": "boolean", "default": False},
                    "jurisdiction":    {"type": "string",  "default": "NZ"},
                },
                "required": ["prompt"],
            },
        ),
        t.Tool(
            name="lumynax_chat",
            description=(
                "Run a chat completion against a specific LumynaX model via the gateway. "
                "Returns the assistant's reply. Supports optional self-hosted web search "
                "if enable_web_search=true and the model supports tools."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "model":            {"type": "string", "description": "LumynaX model slug, e.g. lumynax-chat-hermes-3-llama31-8b-gguf"},
                    "messages":         {"type": "array", "items": {"type": "object"}},
                    "temperature":      {"type": "number", "default": 0.4},
                    "max_tokens":       {"type": "integer", "default": 1024},
                    "enable_web_search": {"type": "boolean", "default": False},
                },
                "required": ["model", "messages"],
            },
        ),
        t.Tool(
            name="lumynax_list",
            description="List LumynaX models with optional filters (tier, modality, max params, etc).",
            inputSchema={
                "type": "object",
                "properties": {
                    "tier":      {"type": "string"},
                    "modality":  {"type": "string"},
                    "max_params_b": {"type": "number"},
                },
            },
        ),
        t.Tool(
            name="lumynax_info",
            description="Full metadata for one LumynaX model (params, context, runtime, residency, sovereignty, license).",
            inputSchema={
                "type": "object",
                "properties": {"model": {"type": "string"}},
                "required": ["model"],
            },
        ),
        t.Tool(
            name="lumynax_web_search",
            description="Direct web search via the LumynaX gateway's self-hosted SearXNG (no external SDK).",
            inputSchema={
                "type": "object",
                "properties": {
                    "query":       {"type": "string"},
                    "max_results": {"type": "integer", "default": 5},
                    "lang":        {"type": "string",  "default": "en"},
                },
                "required": ["query"],
            },
        ),
    ]


def _find_model(model_id: str):
    target = model_id.replace("AbteeXAILab/", "").lower()
    for m in REGISTRY.get("models", []):
        if m["repo_id"].split("/")[-1].lower() == target or m.get("model_id", "").lower() == target:
            return m
    return None


@server.call_tool()
async def call_tool(name: str, args: dict) -> list[t.TextContent]:
    async with httpx.AsyncClient(timeout=300, headers=HEADERS) as c:
        if name == "lumynax_route":
            params = {
                "modalities": ",".join(args.get("modalities", ["text"])),
                "requires_local": str(args.get("requires_local", False)).lower(),
                "requires_tools": str(args.get("requires_tools", False)).lower(),
                "requires_json": str(args.get("requires_json", False)).lower(),
                "jurisdiction": args.get("jurisdiction", "NZ"),
            }
            try:
                r = await c.get(f"{GATEWAY_URL}/route", params=params)
                r.raise_for_status()
                return [t.TextContent(type="text", text=json.dumps(r.json(), indent=2))]
            except Exception:
                # Fallback: route locally
                return [t.TextContent(type="text", text=json.dumps(_route_local(args), indent=2))]

        if name == "lumynax_chat":
            body = {
                "model": args["model"],
                "messages": args["messages"],
                "temperature": args.get("temperature", 0.4),
                "max_tokens": args.get("max_tokens", 1024),
            }
            if args.get("enable_web_search"):
                body["enable_web_search"] = True
            r = await c.post(f"{GATEWAY_URL}/chat/completions", json=body)
            if r.status_code >= 400:
                return [t.TextContent(type="text", text=f"gateway error {r.status_code}: {r.text[:500]}")]
            data = r.json()
            content = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
            return [t.TextContent(type="text", text=content)]

        if name == "lumynax_list":
            rows = []
            for m in REGISTRY.get("models", []):
                if args.get("tier") and args["tier"] not in m["model_id"]: continue
                if args.get("modality") and args["modality"] not in (m.get("modalities") or []): continue
                if args.get("max_params_b") and (m.get("total_params_b") or 0) > args["max_params_b"]: continue
                rows.append({
                    "slug": m["repo_id"].split("/")[-1],
                    "params_b": m.get("total_params_b"),
                    "modalities": m.get("modalities"),
                    "sovereignty_tier": m.get("sovereignty_tier"),
                    "license": m.get("license_id"),
                })
            return [t.TextContent(type="text", text=json.dumps(rows, indent=2))]

        if name == "lumynax_info":
            m = _find_model(args["model"])
            if not m:
                return [t.TextContent(type="text", text=f"not found: {args['model']}")]
            return [t.TextContent(type="text", text=json.dumps(m, indent=2))]

        if name == "lumynax_web_search":
            r = await c.post(f"{GATEWAY_URL}/tools/web_search",
                              json={"query": args["query"],
                                    "max_results": args.get("max_results", 5),
                                    "lang": args.get("lang", "en")})
            if r.status_code >= 400:
                return [t.TextContent(type="text", text=f"gateway error {r.status_code}: {r.text[:500]}")]
            return [t.TextContent(type="text", text=json.dumps(r.json(), indent=2))]

        return [t.TextContent(type="text", text=f"unknown tool: {name}")]


def _route_local(args):
    """Fallback router when the gateway isn't reachable."""
    mods = args.get("modalities", ["text"])
    cands = []
    for m in REGISTRY.get("models", []):
        if any(mod not in (m.get("modalities") or []) for mod in mods): continue
        if args.get("requires_local") and (m.get("sovereignty_tier") or 0) < 3: continue
        if args.get("requires_tools") and not m.get("supports_tools"): continue
        if args.get("jurisdiction", "NZ") not in (m.get("residency") or []): continue
        q = int(m.get("quality_rank") or 5); s = int(m.get("sovereignty_tier") or 3); c = int(m.get("cost_rank") or 5)
        score = (6 - q) * 2 + s * 1.5 + (6 - c) * 0.5
        cands.append((score, m))
    cands.sort(key=lambda x: -x[0])
    if not cands: return {"error": "no candidate"}
    score, pick = cands[0]
    return {"model": pick["repo_id"].split("/")[-1], "score": score, "note": "local fallback routing"}


async def _run():
    async with stdio_server() as (read, write):
        await server.run(read, write, InitializationOptions(
            server_name="lumynax",
            server_version="0.1.0",
            capabilities=server.get_capabilities(notification_options=NotificationOptions(), experimental_capabilities={}),
        ))


def main():
    asyncio.run(_run())


if __name__ == "__main__":
    main()
