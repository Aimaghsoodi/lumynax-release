"""Generate per-runtime configuration: OpenCode, LM Studio, vLLM, llama.cpp, Ollama, Continue."""
from __future__ import annotations
import json
from typing import Any


LUMYNAX_SYS = (
    "You are LumynaX, the AbteeX AI Labs assistant from Aotearoa New Zealand. "
    "Ko te marama te tuapapa. Answer with care, cite uncertainty, "
    "prefer local-first reasoning, and refuse unsafe or sovereignty-violating requests."
)


def opencode(m: dict, base_url: str = "http://localhost:8080/v1", api_key: str = "lumynax-local") -> dict:
    """Emit an OpenCode (sst/opencode) provider JSON for a LumynaX model."""
    slug = m["repo_id"].split("/")[-1]
    return {
        "id": f"lumynax-{slug.replace('lumynax-','')}",
        "name": m.get("title") or slug,
        "type": "openai-compatible",
        "base_url": base_url,
        "api_key": api_key,
        "models": [{
            "id": slug,
            "name": m.get("title") or slug,
            "context_window": m.get("context_tokens") or 16384,
            "max_output_tokens": 4096,
            "supports_tools": bool(m.get("supports_tools")),
            "supports_json": bool(m.get("supports_json")),
            "supports_vision": "vision" in (m.get("modalities") or []),
        }],
        "system_prompt": LUMYNAX_SYS,
        "metadata": {
            "lumynax_repo": m["repo_id"],
            "sovereignty_tier": m.get("sovereignty_tier"),
            "jurisdiction": m.get("jurisdiction"),
            "residency": m.get("residency"),
            "license_id": m.get("license_id"),
        },
    }


def continue_dev(m: dict, base_url: str = "http://localhost:8080/v1") -> dict:
    """Emit a Continue.dev (~/.continue/config.json) model entry."""
    slug = m["repo_id"].split("/")[-1]
    return {
        "title": f"LumynaX · {m.get('title') or slug}",
        "model": slug,
        "apiBase": base_url,
        "apiKey": "lumynax-local",
        "provider": "openai",
        "contextLength": m.get("context_tokens") or 16384,
        "systemMessage": LUMYNAX_SYS,
        "completionOptions": {"temperature": 0.4, "maxTokens": 4096},
    }


def lm_studio(m: dict) -> str:
    """Emit an LM Studio discovery URL or instruction string."""
    repo = m["repo_id"]
    if "gguf" in repo.lower() or (m.get("runtime") or "").startswith("llama_cpp"):
        return (
            f"LM Studio: Open Discover, search for `{repo}` (or `{repo.split('/')[-1]}`), "
            f"select the Q4_K_M shard, click Download. LM Studio's local server lives at "
            f"http://localhost:1234/v1 after you Start Server."
        )
    return (
        f"LM Studio does not load this safetensors repo directly. "
        f"Use `lumynax serve {repo.split('/')[-1]} --backend vllm` instead, "
        f"then point your client at http://localhost:8080/v1."
    )


def ollama(m: dict) -> str:
    """Emit Ollama setup commands."""
    slug = m["repo_id"].split("/")[-1]
    if "gguf" in slug.lower():
        return (
            f"hf download {m['repo_id']} --local-dir {slug}\n"
            f"cd {slug}\n"
            f"ollama create lumynax-{slug.replace('lumynax-','')} -f ollama/Modelfile\n"
            f"ollama run lumynax-{slug.replace('lumynax-','')}"
        )
    return (
        f"# Ollama doesn't natively run safetensors. Use:\n"
        f"# lumynax serve {slug} --backend vllm   (vLLM)\n"
        f"# or convert weights to GGUF first via llama.cpp tools."
    )


def vllm_cmd(m: dict, port: int = 8000) -> str:
    """Emit vLLM serve command."""
    repo = m["repo_id"]
    ctx = min(int(m.get("context_tokens") or 16384), 32768)
    flags = [
        f"vllm serve {repo}",
        f"--port {port}",
        f"--max-model-len {ctx}",
        "--dtype auto",
    ]
    if "moe" in (m.get("model_id") or "").lower():
        flags.append("--enable-expert-parallel")
    if "vision" in (m.get("modalities") or []) or "multimodal" in m.get("model_id",""):
        flags.append("--trust-remote-code")
    return " \\\n  ".join(flags)


def llama_server(m: dict, port: int = 8080) -> str:
    """Emit llama-server (llama.cpp) command."""
    slug = m["repo_id"].split("/")[-1]
    primary = m.get("primary_artifact") or "model.gguf"
    ctx = min(int(m.get("context_tokens") or 16384), 32768)
    return (
        f"hf download {m['repo_id']} --local-dir {slug}\n"
        f"llama-server -m {slug}/{primary} --host 0.0.0.0 --port {port} -c {ctx} -ngl -1"
    )


def all_for(m: dict) -> dict[str, Any]:
    """Return every integration as a dict."""
    return {
        "opencode": opencode(m),
        "continue_dev": continue_dev(m),
        "lm_studio": lm_studio(m),
        "ollama": ollama(m),
        "vllm": vllm_cmd(m),
        "llama_server": llama_server(m),
    }
