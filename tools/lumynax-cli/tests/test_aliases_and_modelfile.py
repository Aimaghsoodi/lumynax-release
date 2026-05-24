"""Tests for aliases + modelfile + config — the v0.5 additions."""
import os, sys, tempfile, json
from pathlib import Path

# Isolate ~/.lumynax for every test
TMP = tempfile.mkdtemp(prefix="lumynax-test-")
os.environ["LUMYNAX_HOME"] = TMP

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from lumynax import aliases, modelfile, config


# ---- aliases ----

def test_builtin_aliases_resolve():
    all_slugs = list(aliases.BUILTIN.values())
    slug, ambig = aliases.resolve("hermes3", all_slugs)
    assert slug == "lumynax-chat-hermes-3-llama31-8b-gguf" and not ambig

def test_alias_case_insensitive():
    all_slugs = list(aliases.BUILTIN.values())
    slug, _ = aliases.resolve("HERMES3", all_slugs)
    assert slug == "lumynax-chat-hermes-3-llama31-8b-gguf"

def test_exact_slug_wins_over_alias():
    all_slugs = ["lumynax-chat-hermes-3-llama31-8b-gguf", "fake-slug"]
    slug, _ = aliases.resolve("lumynax-chat-hermes-3-llama31-8b-gguf", all_slugs)
    assert slug == "lumynax-chat-hermes-3-llama31-8b-gguf"

def test_substring_resolution_unique():
    all_slugs = ["lumynax-chat-hermes-3-llama31-8b-gguf", "lumynax-other"]
    slug, ambig = aliases.resolve("hermes-3-llama31", all_slugs)
    assert slug == "lumynax-chat-hermes-3-llama31-8b-gguf" and not ambig

def test_substring_ambiguous():
    all_slugs = ["lumynax-coder-a", "lumynax-coder-b", "lumynax-chat-c"]
    slug, ambig = aliases.resolve("coder", all_slugs)
    assert slug is None and set(ambig) == {"lumynax-coder-a", "lumynax-coder-b"}

def test_user_alias_overrides_builtin():
    aliases.add_alias("hermes3", "lumynax-other-model")
    assert aliases.all_aliases()["hermes3"] == "lumynax-other-model"
    # restore for downstream tests
    aliases.add_alias("hermes3", "lumynax-chat-hermes-3-llama31-8b-gguf")


# ---- modelfile ----

def test_modelfile_parses_minimal():
    text = "FROM lumynax-chat-hermes-3-llama31-8b-gguf\n"
    mf = modelfile.parse(text)
    assert mf.base == "lumynax-chat-hermes-3-llama31-8b-gguf"
    assert mf.system is None and mf.parameters == {}

def test_modelfile_parses_full():
    text = '''FROM lumynax-chat-hermes-3-llama31-8b-gguf
SYSTEM """You are a NZ legal assistant. Cite Acts."""
PARAMETER temperature 0.2
PARAMETER num_ctx 16384
PARAMETER stop "</s>"
TEMPLATE """{{ .System }}\\n\\n{{ .Prompt }}"""
LICENSE """MIT"""
'''
    mf = modelfile.parse(text)
    assert mf.system.startswith("You are a NZ legal")
    assert mf.parameters["temperature"] == 0.2
    assert mf.parameters["num_ctx"] == 16384
    assert mf.parameters["stop"] == "</s>"
    assert mf.template.startswith("{{")
    assert mf.license == "MIT"

def test_modelfile_round_trip():
    text = '''FROM lumynax-chat-hermes-3-llama31-8b-gguf
SYSTEM """hello"""
PARAMETER temperature 0.5
'''
    mf = modelfile.parse(text)
    mf2 = modelfile.parse(mf.to_text())
    assert mf2.base == mf.base and mf2.system == mf.system and mf2.parameters == mf.parameters

def test_modelfile_rejects_no_from():
    import pytest
    with pytest.raises(ValueError, match="FROM"):
        modelfile.parse("SYSTEM \"\"\"hi\"\"\"")

def test_modelfile_save_and_list():
    mf = modelfile.Modelfile(base="lumynax-chat-hermes-3-llama31-8b-gguf",
                              system="Be concise.",
                              parameters={"temperature": 0.3})
    out = modelfile.save_derived("nz-legal-test", mf)
    assert out.exists()
    derived = modelfile.list_derived()
    names = [d["name"] for d in derived]
    assert "nz-legal-test" in names
    loaded = modelfile.load_derived("nz-legal-test")
    assert loaded.base == mf.base and loaded.system == mf.system

def test_modelfile_remove():
    mf = modelfile.Modelfile(base="x")
    modelfile.save_derived("to-remove-test", mf)
    assert modelfile.remove_derived("to-remove-test") is True
    assert modelfile.remove_derived("never-existed") is False

def test_modelfile_hash_stable():
    mf1 = modelfile.Modelfile(base="x", parameters={"temperature": 0.1})
    mf2 = modelfile.Modelfile(base="x", parameters={"temperature": 0.1})
    assert mf1.hash() == mf2.hash()


# ---- config ----

def test_config_default():
    c = config.load()
    assert c.gateway_url and c.default_strategy == "balanced"

def test_config_save_and_load():
    c = config.load()
    c.default_model = "hermes3"
    c.streaming = False
    config.save(c)
    c2 = config.load()
    assert c2.default_model == "hermes3"
    assert c2.streaming is False
