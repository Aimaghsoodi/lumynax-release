"""Unit tests for the LumynaX Router — analyzer + scorer + gates + renderers."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lumynax.router import analyze, Router, Strategy
from lumynax.router import explain as render

# --------- Fixtures: a mini 6-model registry covering the matrix --------------

REG = [
    # 0: small NZ-resident chat, GGUF
    {"model_id":"lumynax-chat-hermes-3-llama31-8b-gguf","repo_id":"AbteeXAILab/lumynax-chat-hermes-3-llama31-8b-gguf",
     "title":"Hermes 3 8B","family":"llama","runtime":"llama_cpp","modalities":["text"],"context_tokens":16384,
     "supports_tools":True,"supports_json":True,"quality_rank":2,"cost_rank":2,"sovereignty_tier":3,
     "residency":["NZ"],"license_id":"llama3.1","tags":["chat","hermes","gguf"],"total_params_b":8},
    # 1: frontier MoE, global
    {"model_id":"lumynax-frontier-qwen3-235b-a22b-instruct","repo_id":"AbteeXAILab/lumynax-frontier-qwen3-235b-a22b-instruct",
     "title":"Qwen3 235B","family":"qwen","runtime":"transformers","modalities":["text"],"context_tokens":262144,
     "supports_tools":True,"supports_json":True,"quality_rank":1,"cost_rank":5,"sovereignty_tier":2,
     "residency":["NZ","AU","global"],"license_id":"apache-2.0","tags":["frontier","moe","reasoning"],"total_params_b":235,"active_params_b":22},
    # 2: coder mid
    {"model_id":"lumynax-coder-deepseek-v2-lite-16b-gguf","repo_id":"AbteeXAILab/lumynax-coder-deepseek-v2-lite-16b-gguf",
     "title":"DeepSeek-Coder V2 Lite","family":"deepseek","runtime":"llama_cpp","modalities":["text"],"context_tokens":163840,
     "supports_tools":True,"supports_json":True,"quality_rank":2,"cost_rank":2,"sovereignty_tier":3,
     "residency":["NZ"],"license_id":"other","tags":["coder","moe","gguf"],"total_params_b":16,"active_params_b":2.4},
    # 3: multimodal
    {"model_id":"lumynax-multimodal-qwen25-vl-72b-instruct-gguf","repo_id":"AbteeXAILab/lumynax-multimodal-qwen25-vl-72b-instruct-gguf",
     "title":"Qwen2.5 VL 72B","family":"qwen","runtime":"llama_cpp_multimodal","modalities":["text","vision"],"context_tokens":131072,
     "supports_tools":True,"supports_json":True,"quality_rank":2,"cost_rank":4,"sovereignty_tier":3,
     "residency":["NZ"],"license_id":"other","tags":["multimodal","vision","qwen","gguf"],"total_params_b":72},
    # 4: translator
    {"model_id":"lumynax-translate-nllb-200-3b","repo_id":"AbteeXAILab/lumynax-translate-nllb-200-3b",
     "title":"NLLB-200 3.3B","family":"nllb","runtime":"transformers","modalities":["text"],"context_tokens":1024,
     "supports_tools":False,"supports_json":False,"quality_rank":2,"cost_rank":3,"sovereignty_tier":3,
     "residency":["NZ","AU","global"],"license_id":"cc-by-nc-4.0","tags":["translation","te-reo","nllb"],"total_params_b":3.3},
    # 5: long context 1M
    {"model_id":"lumynax-longctx-glm4-9b-chat-1m-gguf","repo_id":"AbteeXAILab/lumynax-longctx-glm4-9b-chat-1m-gguf",
     "title":"GLM-4 1M","family":"glm","runtime":"llama_cpp","modalities":["text"],"context_tokens":1048576,
     "supports_tools":True,"supports_json":True,"quality_rank":2,"cost_rank":2,"sovereignty_tier":3,
     "residency":["NZ"],"license_id":"apache-2.0","tags":["long-context","1m","glm","gguf"],"total_params_b":9},
]

# --------------------------- Analyzer ----------------------------------------

def test_analyze_empty():
    a = analyze("")
    assert not a.is_code and not a.is_math and a.confidence == 0.0

def test_analyze_code_detection():
    a = analyze("```python\ndef foo(x):\n    return x + 1\n```\nfix this please")
    assert a.is_code and "python" in a.code_langs

def test_analyze_vision_detection():
    a = analyze("describe this image: photo.jpg")
    assert a.needs_vision

def test_analyze_audio_detection():
    a = analyze("transcribe this audio recording")
    assert a.needs_audio

def test_analyze_math_detection():
    a = analyze("prove that the sum of two even numbers is even")
    assert a.is_math and a.is_reasoning

def test_analyze_translation_detection():
    a = analyze("Translate to Māori: hello world")
    assert a.is_translation and a.translate_target in {"maori","māori"}
    assert a.contains_te_reo

def test_analyze_te_reo_detection():
    a = analyze("Kia ora, ko Tangata my name. What does this say in English?")
    assert a.contains_te_reo

def test_analyze_long_context():
    a = analyze("x" * 140000)  # ~35k tokens
    assert a.is_long_context

def test_analyze_tools_intent():
    a = analyze("call the get_weather function for Wellington")
    assert a.needs_tools

def test_analyze_json_intent():
    a = analyze("Return as valid JSON with keys foo, bar")
    assert a.needs_json

# --------------------------- Routing -----------------------------------------

def test_route_picks_chat_for_plain_prompt():
    r = Router(models=REG)
    d = r.route("Tell me a poem", jurisdiction="NZ")
    assert d.pick is not None
    # Should NOT be the translator (no translation signal) or vision (no image)
    assert "translate" not in d.pick["model_id"]
    assert "multimodal" not in d.pick["model_id"]

def test_route_picks_coder_for_code_prompt():
    r = Router(models=REG)
    d = r.route("```python\ndef bug():\n  return\n```\nfix this please", jurisdiction="NZ", strategy=Strategy.CODER)
    assert d.pick is not None
    assert "coder" in d.pick["model_id"]

def test_route_picks_vision_for_image_prompt():
    r = Router(models=REG)
    d = r.route("describe this image: photo.jpg", modalities=["text","vision"], jurisdiction="NZ")
    assert d.pick is not None and "vision" in (d.pick.get("modalities") or [])

def test_route_picks_translator_for_translation():
    r = Router(models=REG)
    d = r.route("Translate to Maori: hello", strategy=Strategy.TE_REO, jurisdiction="NZ")
    assert d.pick is not None
    assert "translate" in d.pick["model_id"] or "longctx" in d.pick["model_id"]

def test_route_long_context_auto_bumps_ctx():
    r = Router(models=REG)
    big = "Document text. " * 20000   # well over 32k tokens
    d = r.route(big, jurisdiction="NZ")
    assert d.pick is not None
    assert d.pick.get("context_tokens", 0) >= 32_000

def test_route_local_strategy_drops_global_only():
    r = Router(models=REG)
    d = r.route("Hi", strategy=Strategy.LOCAL, jurisdiction="NZ")
    assert d.pick is not None
    assert d.pick.get("sovereignty_tier", 0) >= 3

def test_route_cheap_penalises_large_models():
    r = Router(models=REG)
    d = r.route("hello", strategy=Strategy.CHEAP, jurisdiction="NZ")
    # Either a small one is picked, or 235B is heavily penalised
    assert d.pick is not None
    assert (d.pick.get("total_params_b") or 0) <= 20 or d.score < 5

def test_route_forbid_excludes():
    r = Router(models=REG)
    d = r.route("hi", forbid_slugs=["lumynax-chat-hermes-3-llama31-8b-gguf"], jurisdiction="NZ")
    assert d.pick is None or d.pick["repo_id"].split("/")[-1] != "lumynax-chat-hermes-3-llama31-8b-gguf"

def test_route_no_candidates_when_filters_too_tight():
    r = Router(models=REG)
    d = r.route("hi", jurisdiction="MARS")  # nothing has Mars residency
    assert d.pick is None
    assert d.n_candidates >= 1
    assert len(d.rejected) >= 1

def test_route_rejection_records_gate_and_reason():
    r = Router(models=REG)
    d = r.route("hi", jurisdiction="MARS")
    gates = {x.gate for x in d.rejected}
    assert "residency" in gates

# --------------------------- Renderers ---------------------------------------

def test_renderer_json_round_trip():
    r = Router(models=REG)
    d = r.route("describe this image", modalities=["text","vision"])
    out = render.as_json(d)
    parsed = json.loads(out)
    assert parsed["pick"] is not None and parsed["score"] > 0
    assert "is_code" in parsed["analysis"]

def test_renderer_slug_only():
    r = Router(models=REG)
    d = r.route("hi")
    assert render.slug_only(d).startswith("lumynax-")

def test_renderer_openai_stub_contains_curl():
    r = Router(models=REG)
    d = r.route("hi")
    s = render.openai_stub(d)
    assert "curl" in s and "chat/completions" in s and d.slug in s

def test_renderer_why_not_explains_rejection():
    r = Router(models=REG)
    d = r.route("hi", forbid_slugs=["lumynax-chat-hermes-3-llama31-8b-gguf"])
    s = render.why_not(d, "lumynax-chat-hermes-3-llama31-8b-gguf")
    assert "forbid" in s.lower() or "rejected" in s.lower()
