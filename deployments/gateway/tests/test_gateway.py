"""pytest for the LumynaX gateway. Mocks backend + SearXNG; tests routing, policy, audit."""
import json
import pytest
from fastapi.testclient import TestClient
import respx
from httpx import Response

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Set up minimal config before importing the app
import tempfile
TMP = tempfile.mkdtemp()
os.environ["GATEWAY_REGISTRY_PATH"] = f"{TMP}/registry.json"
os.environ["GATEWAY_API_KEYS_PATH"] = f"{TMP}/keys.json"
os.environ["GATEWAY_ROUTES_PATH"]   = f"{TMP}/routes.json"
os.environ["GATEWAY_AUDIT_LOG"]     = f"{TMP}/audit.log"
os.environ["SEARXNG_URL"]           = "http://searxng-fake:8080"

REGISTRY = {"models": [
    {"model_id": "lumynax-chat-test-8b-gguf", "repo_id": "AbteeXAILab/lumynax-chat-test-8b-gguf",
     "title": "Test 8B", "modalities": ["text"], "context_tokens": 8192,
     "supports_tools": True, "supports_json": True,
     "quality_rank": 2, "cost_rank": 2, "sovereignty_tier": 3,
     "residency": ["NZ"], "license_id": "apache-2.0", "jurisdiction": "NZ"},
    {"model_id": "lumynax-frontier-test-70b", "repo_id": "AbteeXAILab/lumynax-frontier-test-70b",
     "title": "Test 70B", "modalities": ["text"], "context_tokens": 32768,
     "supports_tools": True, "supports_json": True,
     "quality_rank": 1, "cost_rank": 4, "sovereignty_tier": 2,
     "residency": ["global"], "license_id": "other", "jurisdiction": "global"},
]}
KEYS = {
    "valid-nz-key": {"tenant": "nz-eng", "jurisdiction": "NZ", "policies": [], "min_sovereignty_tier": 3},
    "valid-global-key": {"tenant": "research", "jurisdiction": "global", "policies": ["allow-all"], "min_sovereignty_tier": 1},
}
ROUTES = {
    "lumynax-chat-test-8b-gguf": "http://backend-8b:8000/v1",
    "lumynax-frontier-test-70b": "http://backend-70b:8000/v1",
}
open(os.environ["GATEWAY_REGISTRY_PATH"], "w").write(json.dumps(REGISTRY))
open(os.environ["GATEWAY_API_KEYS_PATH"], "w").write(json.dumps(KEYS))
open(os.environ["GATEWAY_ROUTES_PATH"], "w").write(json.dumps(ROUTES))

from app import app
client = TestClient(app)


def auth(key="valid-nz-key"):
    return {"Authorization": f"Bearer {key}"}


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert r.json()["models"] == 2


def test_models_requires_auth():
    assert client.get("/v1/models").status_code == 401


def test_models_lists_for_tenant():
    r = client.get("/v1/models", headers=auth("valid-nz-key"))
    assert r.status_code == 200
    ids = [m["id"] for m in r.json()["data"]]
    assert "lumynax-chat-test-8b-gguf" in ids
    # 70B is global-only — NZ tenant should not see it
    assert "lumynax-frontier-test-70b" not in ids


def test_models_global_tenant_sees_all():
    r = client.get("/v1/models", headers=auth("valid-global-key"))
    ids = [m["id"] for m in r.json()["data"]]
    assert "lumynax-chat-test-8b-gguf" in ids
    assert "lumynax-frontier-test-70b" in ids


def test_route_picks_local_for_nz():
    r = client.get("/v1/route?requires_local=true&jurisdiction=NZ", headers=auth())
    assert r.status_code == 200
    assert r.json()["model"] == "lumynax-chat-test-8b-gguf"


def test_policy_denies_jurisdiction_mismatch():
    r = client.post("/v1/chat/completions", headers=auth("valid-nz-key"),
                    json={"model": "lumynax-frontier-test-70b",
                          "messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 403
    assert "policy denied" in r.text


def test_model_not_found():
    r = client.post("/v1/chat/completions", headers=auth(),
                    json={"model": "nonexistent", "messages": []})
    assert r.status_code == 404


@respx.mock
def test_chat_forwards_to_backend():
    respx.post("http://backend-8b:8000/v1/chat/completions").mock(
        return_value=Response(200, json={
            "id": "chatcmpl-x", "choices": [{"message": {"role": "assistant", "content": "hi back"}, "finish_reason": "stop"}],
        })
    )
    r = client.post("/v1/chat/completions", headers=auth(),
                    json={"model": "lumynax-chat-test-8b-gguf",
                          "messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 200
    assert r.json()["choices"][0]["message"]["content"] == "hi back"


@respx.mock
def test_web_search_tool_loop():
    # First upstream call returns a tool_call requesting web_search
    respx.post("http://backend-8b:8000/v1/chat/completions").mock(side_effect=[
        Response(200, json={"choices": [{"message": {
            "role": "assistant", "tool_calls": [
                {"id": "call_1", "type": "function",
                 "function": {"name": "web_search", "arguments": '{"query": "test"}'}}
            ]}}]}),
        Response(200, json={"choices": [{"message": {
            "role": "assistant", "content": "found 3 results"}, "finish_reason": "stop"}]}),
    ])
    respx.get("http://searxng-fake:8080/search").mock(
        return_value=Response(200, json={"results": [
            {"title": "T1", "url": "u1", "content": "snip1", "engine": "ddg"},
        ]})
    )
    r = client.post("/v1/chat/completions", headers=auth(),
                    json={"model": "lumynax-chat-test-8b-gguf",
                          "messages": [{"role": "user", "content": "search the web"}],
                          "enable_web_search": True})
    assert r.status_code == 200
    assert "found 3 results" in r.json()["choices"][0]["message"]["content"]


def test_audit_log_appended(tmp_path, monkeypatch):
    # Just check the audit hash chain advances on a request
    from app import state, audit
    h0 = state["audit_last_hash"]
    audit({"event": "test"})
    h1 = state["audit_last_hash"]
    assert h0 != h1
    assert len(h1) == 64  # sha256 hex
