from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .registry import ModelEndpoint

SHARD_RE = re.compile(r"^(?P<prefix>.*-)(?P<index>\d{5})-of-(?P<total>\d{5})(?P<suffix>\.[^.\\/]+)$")


@dataclass(frozen=True, slots=True)
class PulledModel:
    model: ModelEndpoint
    cache_dir: Path
    files: tuple[Path, ...]
    manifest_path: Path
    downloaded: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": True,
            "model_id": self.model.model_id,
            "repo_id": self.model.repo_id,
            "runtime": self.model.runtime,
            "primary_artifact": self.model.primary_artifact,
            "cache_dir": str(self.cache_dir),
            "files": [str(path) for path in self.files],
            "manifest_path": str(self.manifest_path),
            "downloaded": self.downloaded,
            "next_commands": {
                "chat": f"MaramaRoute chat {self.model.model_id}",
                "run": f'MaramaRoute run {self.model.model_id} "Say kia ora."',
                "serve": "MaramaRoute serve --live-local --port 8787",
                "agent_config": f"MaramaRoute agent-config --target claude-code --model {self.model.model_id}",
            },
        }


class LlamaChatSession:
    def __init__(
        self,
        *,
        model: ModelEndpoint,
        model_path: Path,
        context_tokens: int,
        threads: int | None,
        max_tokens: int,
        temperature: float,
    ) -> None:
        try:
            from llama_cpp import Llama  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                "llama-cpp-python is required for local chat. "
                "Install it with `python -m pip install llama-cpp-python`.",
            ) from exc

        kwargs: dict[str, Any] = {
            "model_path": str(model_path),
            "n_ctx": context_tokens,
            "verbose": False,
        }
        if threads is not None:
            kwargs["n_threads"] = threads
        self.model = model
        self.model_path = model_path
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.history: list[tuple[str, str]] = []
        self._llama = Llama(**kwargs)

    def send(self, prompt: str) -> str:
        rendered = _format_prompt(prompt, history=tuple(self.history))
        response = self._llama.create_completion(
            prompt=rendered,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            stop=["<|im_end|>", "<|endoftext|>"],
        )
        choices = response.get("choices", [])
        text = str(choices[0].get("text", "")).strip() if choices else ""
        self.history.append((prompt, text))
        return text

    def send_stream(self, prompt: str) -> Any:
        rendered = _format_prompt(prompt, history=tuple(self.history))
        chunks = self._llama.create_completion(
            prompt=rendered,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            stop=["<|im_end|>", "<|endoftext|>"],
            stream=True,
        )
        collected: list[str] = []
        for chunk in chunks:
            choices = chunk.get("choices", []) if isinstance(chunk, dict) else []
            text = str(choices[0].get("text", "")) if choices else ""
            if text:
                collected.append(text)
                yield text
        self.history.append((prompt, "".join(collected).strip()))


class TransformersChatSession:
    def __init__(
        self,
        *,
        model: ModelEndpoint,
        cache_dir: Path,
        local_files: tuple[Path, ...],
        max_tokens: int,
        temperature: float,
    ) -> None:
        try:
            from transformers import (  # type: ignore[import-not-found]
                AutoModelForCausalLM,
                AutoModelForSeq2SeqLM,
                AutoTokenizer,
            )
        except ImportError as exc:
            raise RuntimeError(
                "transformers and torch are required for this offline LumynaX model. "
                "Install them with `python -m pip install transformers torch`.",
            ) from exc

        self.model = model
        self.model_path = _transformers_model_dir(model, cache_dir, local_files)
        self.cache_dir = cache_dir
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.history: list[tuple[str, str]] = []
        self._seq2seq = False
        self._tokenizer = _load_transformers_tokenizer(
            AutoTokenizer,
            self.model_path,
            model.model_id,
        )
        try:
            self._model = AutoModelForCausalLM.from_pretrained(
                str(self.model_path),
                local_files_only=True,
                trust_remote_code=True,
            )
        except Exception as causal_exc:
            try:
                self._model = AutoModelForSeq2SeqLM.from_pretrained(
                    str(self.model_path),
                    local_files_only=True,
                    trust_remote_code=True,
                )
                self._seq2seq = True
            except Exception as seq_exc:
                raise RuntimeError(
                    f"{model.model_id} is pulled, but it did not load as a local text-generation model. "
                    "This model may be a task model such as OCR, reranking, speech, moderation, or embeddings. "
                    f"Causal loader error: {causal_exc}. Seq2Seq loader error: {seq_exc}",
                ) from seq_exc
        self.context_limit = _transformers_context_limit(
            self._model,
            self._tokenizer,
            model.context_tokens,
        )

    def send(self, prompt: str) -> str:
        rendered = self._render(prompt)
        inputs = self._tokenizer(rendered, return_tensors="pt")
        inputs, input_length, max_new_tokens = _fit_transformers_inputs(
            inputs,
            context_limit=self.context_limit,
            max_tokens=self.max_tokens,
        )
        generate_kwargs: dict[str, Any] = {
            **inputs,
            "max_new_tokens": max_new_tokens,
            "do_sample": self.temperature > 0,
            "temperature": max(self.temperature, 0.01),
        }
        pad_token_id = getattr(self._tokenizer, "pad_token_id", None)
        eos_token_id = getattr(self._tokenizer, "eos_token_id", None)
        if pad_token_id is None and eos_token_id is not None:
            generate_kwargs["pad_token_id"] = eos_token_id
        try:
            output = self._model.generate(**generate_kwargs)
        except Exception as exc:
            raise RuntimeError(
                f"{self.model.model_id} failed during local generation after loading. "
                f"Input tokens: {input_length}. Context limit: {self.context_limit}. "
                "Try a shorter prompt, lower --max-tokens, or choose a GGUF chat model. "
                f"Backend error: {exc}",
            ) from exc
        if self._seq2seq:
            text = self._tokenizer.decode(output[0], skip_special_tokens=True).strip()
        else:
            text = self._tokenizer.decode(output[0][input_length:], skip_special_tokens=True).strip()
        self.history.append((prompt, text))
        return text

    def send_stream(self, prompt: str) -> Any:
        yield self.send(prompt)

    def _render(self, prompt: str) -> str:
        messages = [{"role": "system", "content": "You are LumynaX, a local AbteeX AI Labs assistant."}]
        for user, assistant in self.history[-8:]:
            messages.append({"role": "user", "content": user})
            messages.append({"role": "assistant", "content": assistant})
        messages.append({"role": "user", "content": prompt})
        template = getattr(self._tokenizer, "apply_chat_template", None)
        if callable(template):
            try:
                return str(template(messages, tokenize=False, add_generation_prompt=True))
            except Exception:
                pass
        return _format_prompt(prompt, history=tuple(self.history))


class OfflineTaskSession:
    def __init__(self, *, model: ModelEndpoint, cache_dir: Path, local_files: tuple[Path, ...]) -> None:
        self.model = model
        self.model_path = cache_dir
        self.cache_dir = cache_dir
        self.local_files = local_files
        self.history: list[tuple[str, str]] = []

    def send(self, prompt: str) -> str:
        files = "\n".join(f"- {path}" for path in self.local_files)
        note = _offline_task_note(self.model)
        text = (
            f"LumynaX offline task model selected: {self.model.model_id}\n"
            f"Runtime: {self.model.runtime}\n"
            "Mode: offline_task_model\n\n"
            "Your prompt was received locally:\n"
            f"{prompt}\n\n"
            f"{note}\n\n"
            f"Local files:\n{files}"
        )
        self.history.append((prompt, text))
        return text

    def send_stream(self, prompt: str) -> Any:
        yield self.send(prompt)


def default_cache_root() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
        return base / "AbteeXAI" / "MaramaRoute" / "models"
    base = Path(os.environ.get("XDG_CACHE_HOME") or (Path.home() / ".cache"))
    return base / "abteex-ai" / "marama-route" / "models"


def resolve_model(models: tuple[ModelEndpoint, ...], model_ref: str) -> ModelEndpoint:
    query = model_ref.strip()
    lowered = query.lower()
    for model in models:
        if query in {model.model_id, model.repo_id}:
            return model
    matches = [
        model
        for model in models
        if lowered in model.model_id.lower() or lowered in model.repo_id.lower()
    ]
    if len(matches) == 1:
        return matches[0]
    if matches:
        candidates = ", ".join(model.model_id for model in matches[:8])
        raise ValueError(f"Model reference is ambiguous: {model_ref}. Matches: {candidates}")
    raise ValueError(f"Unknown LumynaX model: {model_ref}")


def artifact_files(model: ModelEndpoint) -> tuple[str, ...]:
    artifact = model.primary_artifact.strip()
    if not artifact:
        return ()
    match = SHARD_RE.match(artifact.replace("\\", "/"))
    if match is None:
        return (artifact,)
    total = int(match.group("total"))
    width = len(match.group("index"))
    prefix = match.group("prefix")
    suffix = match.group("suffix")
    return tuple(f"{prefix}{index:0{width}d}-of-{total:0{width}d}{suffix}" for index in range(1, total + 1))


def model_cache_dir(model: ModelEndpoint, cache_root: Path | None = None) -> Path:
    root = cache_root or default_cache_root()
    owner, _, name = model.repo_id.partition("/")
    if not name:
        owner = "AbteeXAILab"
        name = model.model_id
    return root / owner / name


def pull_model(
    models: tuple[ModelEndpoint, ...],
    model_ref: str,
    *,
    cache_root: Path | None = None,
    all_files: bool = False,
    force: bool = False,
    dry_run: bool = False,
) -> PulledModel:
    model = resolve_model(models, model_ref)
    cache_dir = model_cache_dir(model, cache_root)
    manifest_path = cache_dir / ".marama-route-pull.json"
    selected_files = artifact_files(model)
    snapshot = _requires_snapshot_download(model)

    if dry_run:
        planned = (
            (cache_dir / "<full-huggingface-snapshot>",)
            if snapshot
            else tuple(cache_dir / item for item in selected_files)
        )
        return PulledModel(model, cache_dir, planned, manifest_path, downloaded=False)

    cache_dir.mkdir(parents=True, exist_ok=True)
    files = _download_from_hugging_face(
        model,
        cache_dir=cache_dir,
        selected_files=selected_files,
        all_files=all_files or snapshot,
        force=force,
    )
    manifest = {
        "model_id": model.model_id,
        "repo_id": model.repo_id,
        "runtime": model.runtime,
        "primary_artifact": model.primary_artifact,
        "cache_dir": str(cache_dir),
        "files": [str(path) for path in files],
        "downloaded_at": int(time.time()),
        "source": "huggingface",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return PulledModel(model, cache_dir, tuple(files), manifest_path, downloaded=True)


def list_pulled_models(cache_root: Path | None = None) -> dict[str, Any]:
    root = cache_root or default_cache_root()
    manifests = sorted(root.glob("*/*/.marama-route-pull.json")) if root.exists() else []
    models: list[dict[str, Any]] = []
    for manifest in manifests:
        try:
            payload = json.loads(manifest.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            payload["manifest_path"] = str(manifest)
            models.append(payload)
    return {"ok": True, "cache_root": str(root), "count": len(models), "models": models}


def run_pulled_model(
    models: tuple[ModelEndpoint, ...],
    model_ref: str,
    *,
    prompt: str,
    cache_root: Path | None = None,
    pull: bool = False,
    max_tokens: int = 192,
    temperature: float = 0.2,
    context_tokens: int | None = None,
    threads: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    model = resolve_model(models, model_ref)
    cache_dir = model_cache_dir(model, cache_root)
    local_files = local_model_files(cache_dir)
    if pull or not local_files:
        result = pull_model(models, model.model_id, cache_root=cache_root, dry_run=dry_run)
        local_files = tuple(result.files)

    if dry_run:
        return {
            "ok": True,
            "mode": "dry_run",
            "model_id": model.model_id,
            "repo_id": model.repo_id,
            "cache_dir": str(cache_dir),
            "files": [str(path) for path in local_files],
            "prompt": prompt,
        }

    if not local_files:
        raise FileNotFoundError(
            f"No local model files found for {model.model_id}. Run `MaramaRoute pull {model.model_id}` first.",
        )
    session = load_chat_session(
        models,
        model.model_id,
        cache_root=cache_root,
        pull=False,
        max_tokens=max_tokens,
        temperature=temperature,
        context_tokens=context_tokens,
        threads=threads,
    )
    text = session.send(prompt)
    return {
        "ok": True,
        "model_id": model.model_id,
        "repo_id": model.repo_id,
        "model_path": str(session.model_path),
        "prompt": prompt,
        "response": text,
    }


def load_chat_session(
    models: tuple[ModelEndpoint, ...],
    model_ref: str,
    *,
    cache_root: Path | None = None,
    pull: bool = False,
    max_tokens: int = 192,
    temperature: float = 0.2,
    context_tokens: int | None = None,
    threads: int | None = None,
) -> Any:
    model = resolve_model(models, model_ref)
    cache_dir = model_cache_dir(model, cache_root)
    local_files = local_model_files(cache_dir)
    if pull or not local_files:
        result = pull_model(models, model.model_id, cache_root=cache_root)
        local_files = tuple(result.files)
    if not local_files:
        raise FileNotFoundError(
            f"No local model files found for {model.model_id}. Run `MaramaRoute pull {model.model_id}` first.",
        )
    if _is_llama_runtime(model):
        return LlamaChatSession(
            model=model,
            model_path=local_files[0],
            context_tokens=context_tokens or min(model.context_tokens, 32768),
            threads=threads,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    if _is_transformers_text_generation(model):
        return TransformersChatSession(
            model=model,
            cache_dir=cache_dir,
            local_files=local_files,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    return OfflineTaskSession(model=model, cache_dir=cache_dir, local_files=local_files)


def _download_from_hugging_face(
    model: ModelEndpoint,
    *,
    cache_dir: Path,
    selected_files: tuple[str, ...],
    all_files: bool,
    force: bool,
) -> tuple[Path, ...]:
    try:
        from huggingface_hub import (  # type: ignore[import-not-found]
            hf_hub_download,
            snapshot_download,
        )
    except ImportError as exc:
        raise RuntimeError(
            "huggingface-hub is required for `MaramaRoute pull`. "
            "Install or upgrade with `python -m pip install -U lumynax-marama-route huggingface-hub`.",
        ) from exc

    if all_files or not selected_files:
        snapshot_download(repo_id=model.repo_id, local_dir=str(cache_dir), force_download=force)
        return local_model_files(cache_dir)

    downloaded: list[Path] = []
    for filename in selected_files:
        path = hf_hub_download(
            repo_id=model.repo_id,
            filename=filename,
            local_dir=str(cache_dir),
            force_download=force,
        )
        downloaded.append(Path(path).resolve())
    return tuple(downloaded)


def local_model_files(cache_dir: Path) -> tuple[Path, ...]:
    if not cache_dir.exists():
        return ()
    patterns = ("*.gguf", "*.safetensors", "*.bin", "*.pt", "*.pth", "*.onnx")
    files: list[Path] = []
    for pattern in patterns:
        files.extend(path.resolve() for path in cache_dir.rglob(pattern) if path.is_file())
    return tuple(sorted(files))


def _is_llama_runtime(model: ModelEndpoint) -> bool:
    value = f"{model.runtime} {model.primary_artifact}".lower()
    return "llama" in value or "gguf" in value


def _is_transformers_text_generation(model: ModelEndpoint) -> bool:
    runtime = model.runtime.lower()
    if "transformers" not in runtime or "multimodal" in runtime:
        return False
    if _is_transformers_smoke_test(model):
        return False
    modalities = {item.lower() for item in model.modalities}
    if modalities - {"text"}:
        return False
    task_tags = {
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
    return not (set(model.tags) & task_tags)


def _is_transformers_smoke_test(model: ModelEndpoint) -> bool:
    runtime = model.runtime.lower()
    if "transformers" not in runtime:
        return False
    modalities = {item.lower() for item in model.modalities}
    if modalities - {"text"}:
        return False
    weight = model.metadata.get("total_weight_size")
    try:
        total_weight_size = int(weight or 0)
    except (TypeError, ValueError):
        total_weight_size = 0
    return model.model_id == "lumynax-tiny" or (0 < total_weight_size < 50_000_000)


def _offline_task_note(model: ModelEndpoint) -> str:
    if _is_transformers_smoke_test(model):
        return (
            "This LumynaX entry is a tiny smoke-test seed, not a conversational generator. "
            "Use `lumynax-tiny-qwen25-05b-gguf` for tiny local chat."
        )
    return (
        "This registry entry is pulled and available offline, but it is task-specific rather "
        "than a free-form chat generator. Use the matching local task runtime for its model "
        "family, or use /switch to choose a direct chat model."
    )


def _transformers_model_dir(
    model: ModelEndpoint,
    cache_dir: Path,
    local_files: tuple[Path, ...],
) -> Path:
    artifact = model.primary_artifact.strip().replace("\\", "/")
    if " (" in artifact:
        artifact = artifact.split(" (", 1)[0].strip()
    candidates: list[Path] = []
    if artifact:
        primary = cache_dir / artifact
        if primary.is_file() or primary.parent.exists():
            candidates.append(primary.parent)
    merged = cache_dir / "merged_model"
    if merged.exists():
        candidates.append(merged)
    candidates.extend(path.parent for path in local_files)
    candidates.append(cache_dir)

    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if any((resolved / marker).exists() for marker in ("config.json", "tokenizer.json", "tokenizer_config.json")):
            return resolved
    return cache_dir


def _load_transformers_tokenizer(auto_tokenizer: Any, model_path: Path, model_id: str) -> Any:
    errors: list[str] = []
    for use_fast in (True, False):
        try:
            return auto_tokenizer.from_pretrained(
                str(model_path),
                local_files_only=True,
                trust_remote_code=True,
                use_fast=use_fast,
            )
        except Exception as exc:
            errors.append(f"use_fast={use_fast}: {exc}")
    detail = " | ".join(errors)
    raise RuntimeError(
        f"{model_id} is pulled, but its tokenizer did not load from {model_path}. "
        "Install tokenizer support with `python -m pip install -U sentencepiece tiktoken tokenizers`, "
        f"then retry. Tokenizer errors: {detail}",
    )


def _transformers_context_limit(model: Any, tokenizer: Any, fallback: int) -> int:
    values: list[int] = []
    for source in (getattr(model, "config", None), tokenizer):
        if source is None:
            continue
        for name in ("max_position_embeddings", "n_positions", "max_sequence_length", "model_max_length"):
            value = getattr(source, name, None)
            if isinstance(value, int) and 0 < value < 1_000_000:
                values.append(value)
    if fallback > 0 and fallback < 1_000_000:
        values.append(fallback)
    return min(values) if values else 4096


def _fit_transformers_inputs(
    inputs: dict[str, Any],
    *,
    context_limit: int,
    max_tokens: int,
) -> tuple[dict[str, Any], int, int]:
    input_ids = inputs.get("input_ids")
    input_length = int(input_ids.shape[-1])
    desired_new_tokens = max(1, int(max_tokens))
    reserve = min(desired_new_tokens, max(1, min(256, context_limit // 4)))
    allowed_input = max(1, context_limit - reserve)
    if input_length > allowed_input:
        for key, value in list(inputs.items()):
            shape = getattr(value, "shape", None)
            if shape is not None and len(shape) >= 2 and int(shape[-1]) == input_length:
                inputs[key] = value[..., -allowed_input:]
        input_length = int(inputs["input_ids"].shape[-1])
    available = max(1, context_limit - input_length)
    return inputs, input_length, min(desired_new_tokens, available)


def _requires_snapshot_download(model: ModelEndpoint) -> bool:
    return not _is_llama_runtime(model)


def _format_prompt(prompt: str, *, history: tuple[tuple[str, str], ...] = ()) -> str:
    parts = [
        "<|im_start|>system\n"
        "You are LumynaX, a local-first AbteeX AI Labs assistant for Aotearoa New Zealand."
        "<|im_end|>\n",
    ]
    for user, assistant in history[-8:]:
        parts.append(f"<|im_start|>user\n{user}<|im_end|>\n")
        parts.append(f"<|im_start|>assistant\n{assistant}<|im_end|>\n")
    parts.append(f"<|im_start|>user\n{prompt}<|im_end|>\n")
    parts.append("<|im_start|>assistant\n")
    return "".join(parts)
