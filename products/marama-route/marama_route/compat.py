from __future__ import annotations

from collections import Counter
from typing import Any

from .registry import ModelEndpoint

COMPATIBILITY_TARGETS = ("llama_cpp", "vllm", "nvidia_nim", "nvidia_nemo")
_USABLE_STATUSES = {"supported", "candidate", "experimental"}
_PATHWAY_STATUSES = _USABLE_STATUSES | {"convert_required"}
_STATUS_GROUPS = {
    "usable": _USABLE_STATUSES,
    "compatible": _USABLE_STATUSES,
    "pathway": _PATHWAY_STATUSES,
    "deployment_path": _PATHWAY_STATUSES,
    "deployment-path": _PATHWAY_STATUSES,
}

_TASK_TAGS = {
    "asr",
    "classifier",
    "detection",
    "doc-ai",
    "document-vqa",
    "embedding",
    "embedding-companion",
    "guardrail",
    "layout",
    "moderation",
    "ocr",
    "reranker",
    "retrieval",
    "safety",
    "speech",
    "tables",
    "tts",
}
_NIM_LLM_FAMILY_HINTS = {
    "bart",
    "bloom",
    "chatglm",
    "deepseek",
    "gemma",
    "glm",
    "granite",
    "llama",
    "mistral",
    "mixtral",
    "olmo",
    "phi",
    "qwen",
    "starcoder",
}


def model_runtime_compatibility(model: ModelEndpoint) -> dict[str, Any]:
    """Return runtime compatibility metadata for production deployment planning.

    This is intentionally conservative. It records whether MaramaRoute can treat a
    model as directly supported, a candidate needing backend validation, or
    unsupported for a target runtime. It does not claim that every repository can
    run in every backend.
    """

    has_gguf = _is_gguf_model(model)
    text_only = _is_text_only(model)
    task_model = _is_task_model(model) or _is_smoke_seed(model)
    text_generation = text_only and not task_model
    single_file_gguf = has_gguf and _is_single_file_gguf(model)
    family = model.family.lower()

    return {
        "llama_cpp": _llama_cpp_compat(model, has_gguf=has_gguf, single_file_gguf=single_file_gguf),
        "vllm": _vllm_compat(
            model,
            has_gguf=has_gguf,
            single_file_gguf=single_file_gguf,
            text_generation=text_generation,
            task_model=task_model,
        ),
        "nvidia_nim": _nim_compat(
            model,
            has_gguf=has_gguf,
            single_file_gguf=single_file_gguf,
            text_generation=text_generation,
            task_model=task_model,
            family=family,
        ),
        "nvidia_nemo": _nemo_compat(
            model,
            has_gguf=has_gguf,
            text_generation=text_generation,
            task_model=task_model,
        ),
    }


def build_compatibility_matrix(
    models: tuple[ModelEndpoint, ...],
    *,
    target: str = "",
    status: str = "",
    limit: int = 0,
) -> dict[str, Any]:
    target = _normalize_target(target)
    wanted_status = status.strip().lower()
    rows: list[dict[str, Any]] = []
    summary: dict[str, Counter[str]] = {name: Counter() for name in COMPATIBILITY_TARGETS}

    for model in models:
        compatibility = model_runtime_compatibility(model)
        for name in COMPATIBILITY_TARGETS:
            summary[name][str(compatibility[name]["status"])] += 1
        if target:
            entry = compatibility[target]
            if wanted_status and not _status_matches(str(entry["status"]), wanted_status):
                continue
            rows.append(_compatibility_row(model, {target: entry}))
        else:
            if wanted_status and not any(
                _status_matches(str(entry["status"]), wanted_status) for entry in compatibility.values()
            ):
                continue
            rows.append(_compatibility_row(model, compatibility))

    if limit > 0:
        rows = rows[:limit]
    return {
        "ok": True,
        "model_count": len(models),
        "returned": len(rows),
        "target": target or "all",
        "status": wanted_status or "all",
        "summary": {name: dict(sorted(counts.items())) for name, counts in summary.items()},
        "models": rows,
    }


def render_compatibility_markdown(matrix: dict[str, Any]) -> str:
    lines = [
        "# MaramaRoute Runtime Compatibility Matrix",
        "",
        f"Model count: `{matrix['model_count']}`",
        "",
        "## Summary",
        "",
        "| Runtime | Status counts |",
        "| --- | --- |",
    ]
    for runtime, counts in matrix["summary"].items():
        count_text = ", ".join(f"{status}: {count}" for status, count in counts.items())
        lines.append(f"| `{runtime}` | {count_text} |")
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- `supported` means MaramaRoute can directly plan that runtime.",
            "- `candidate` means the format and task look compatible, but backend validation is still required.",
            "- `experimental` means the backend documents the path as experimental or backend-sensitive.",
            "- `convert_required` means the model needs a format conversion before that runtime path is valid.",
            "- `unsupported` means the model is a task/runtime mismatch for that target.",
            "",
            "## Models",
            "",
            "| Model | Runtime | vLLM | NVIDIA NIM | NVIDIA NeMo |",
            "| --- | --- | --- | --- | --- |",
        ],
    )
    for row in matrix["models"]:
        compatibility = row["compatibility"]
        lines.append(
            "| "
            f"`{row['model_id']}` | `{row['runtime']}` | "
            f"{_status_cell(compatibility.get('vllm'))} | "
            f"{_status_cell(compatibility.get('nvidia_nim'))} | "
            f"{_status_cell(compatibility.get('nvidia_nemo'))} |",
        )
    lines.append("")
    return "\n".join(lines)


def _compatibility_row(model: ModelEndpoint, compatibility: dict[str, Any]) -> dict[str, Any]:
    return {
        "model_id": model.model_id,
        "repo_id": model.repo_id,
        "family": model.family,
        "runtime": model.runtime,
        "modalities": list(model.modalities),
        "primary_artifact": model.primary_artifact,
        "tags": list(model.tags),
        "compatibility": compatibility,
    }


def _llama_cpp_compat(
    model: ModelEndpoint,
    *,
    has_gguf: bool,
    single_file_gguf: bool,
) -> dict[str, Any]:
    if has_gguf and single_file_gguf:
        return _entry(
            "supported",
            "single-file GGUF local runtime",
            commands=[f"MaramaRoute run {model.model_id}"],
        )
    if has_gguf:
        return _entry(
            "candidate",
            "GGUF runtime detected, but artifact layout should be inspected before serving",
        )
    return _entry("unsupported", "not a GGUF/llama.cpp model")


def _vllm_compat(
    model: ModelEndpoint,
    *,
    has_gguf: bool,
    single_file_gguf: bool,
    text_generation: bool,
    task_model: bool,
) -> dict[str, Any]:
    if task_model:
        return _entry("unsupported", "task model is not a vLLM text-generation serving target")
    if has_gguf and text_generation and single_file_gguf:
        return _entry(
            "experimental",
            "vLLM GGUF loading is experimental and requires tokenizer/config validation",
            commands=[f"vllm serve {model.repo_id}:<quant> --tokenizer <base-hf-tokenizer>"],
        )
    if text_generation and _is_transformers_runtime(model):
        return _entry(
            "candidate",
            "HF Transformers text-generation layout can be tried with vLLM when architecture is supported",
            commands=[f"vllm serve {model.repo_id}"],
        )
    if has_gguf:
        return _entry("unsupported", "multimodal or task GGUF is not a safe vLLM target")
    return _entry("unsupported", "model format is not a vLLM text-generation candidate")


def _nim_compat(
    model: ModelEndpoint,
    *,
    has_gguf: bool,
    single_file_gguf: bool,
    text_generation: bool,
    task_model: bool,
    family: str,
) -> dict[str, Any]:
    if task_model:
        return _entry("unsupported", "task model is outside NVIDIA NIM for LLM serving scope")
    if not text_generation:
        return _entry("unsupported", "not a text-only LLM serving target")
    if family not in _NIM_LLM_FAMILY_HINTS:
        return _entry(
            "candidate",
            "text LLM candidate; confirm NVIDIA NIM architecture support before production",
            commands=[f"hf://{model.repo_id}"],
        )
    if has_gguf and single_file_gguf:
        return _entry(
            "candidate",
            "NVIDIA NIM accepts GGUF when architecture, config, tokenizer, and folder layout are valid",
            commands=[f"hf://{model.repo_id}"],
        )
    if _is_transformers_runtime(model):
        return _entry(
            "candidate",
            "HF safetensors model candidate for NIM when architecture and tokenizer files are supported",
            commands=[f"hf://{model.repo_id}"],
        )
    return _entry("candidate", "text LLM candidate; backend validation required")


def _nemo_compat(
    model: ModelEndpoint,
    *,
    has_gguf: bool,
    text_generation: bool,
    task_model: bool,
) -> dict[str, Any]:
    if task_model:
        return _entry("unsupported", "task model needs its own task runtime or a NeMo-specific package")
    if has_gguf and text_generation:
        return _entry(
            "convert_required",
            "GGUF is not a direct NeMo checkpoint; use HF/base weights or convert to a NeMo-supported format",
        )
    if text_generation and _is_transformers_runtime(model):
        return _entry(
            "candidate",
            "HF text-generation model candidate for NeMo AutoModel or conversion workflow",
        )
    return _entry("unsupported", "model is not a NeMo LLM deployment target")


def _entry(status: str, reason: str, *, commands: list[str] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"status": status, "reason": reason}
    if commands:
        payload["commands"] = commands
    return payload


def _status_matches(actual: str, wanted: str) -> bool:
    actual_value = actual.strip().lower()
    wanted_value = wanted.strip().lower()
    status_group = _STATUS_GROUPS.get(wanted_value)
    if status_group is not None:
        return actual_value in status_group
    return actual_value == wanted_value


def _normalize_target(target: str) -> str:
    value = target.strip().lower().replace("-", "_")
    aliases = {
        "all": "",
        "llama": "llama_cpp",
        "llama.cpp": "llama_cpp",
        "llamacpp": "llama_cpp",
        "nim": "nvidia_nim",
        "nvidia_nim": "nvidia_nim",
        "nem": "nvidia_nemo",
        "nemo": "nvidia_nemo",
        "nvidia_nemo": "nvidia_nemo",
    }
    resolved = aliases.get(value, value)
    if resolved and resolved not in COMPATIBILITY_TARGETS:
        raise ValueError(f"Unknown compatibility target: {target}")
    return resolved


def _status_cell(entry: Any) -> str:
    if not isinstance(entry, dict):
        return ""
    return str(entry.get("status") or "")


def _is_gguf_model(model: ModelEndpoint) -> bool:
    value = f"{model.runtime} {model.primary_artifact} {' '.join(model.tags)}".lower()
    return "gguf" in value or "llama_cpp" in value


def _is_single_file_gguf(model: ModelEndpoint) -> bool:
    artifact = model.primary_artifact.strip().lower()
    return artifact.endswith(".gguf") and "-of-" not in artifact


def _is_transformers_runtime(model: ModelEndpoint) -> bool:
    return "transformers" in model.runtime.lower()


def _is_text_only(model: ModelEndpoint) -> bool:
    return {item.lower() for item in model.modalities} == {"text"}


def _is_task_model(model: ModelEndpoint) -> bool:
    return bool(set(model.tags) & _TASK_TAGS)


def _is_smoke_seed(model: ModelEndpoint) -> bool:
    if model.model_id == "lumynax-tiny":
        return True
    if "transformers" not in model.runtime.lower():
        return False
    weight = model.metadata.get("total_weight_size")
    try:
        total_weight_size = int(weight or 0)
    except (TypeError, ValueError):
        return False
    return 0 < total_weight_size < 50_000_000
