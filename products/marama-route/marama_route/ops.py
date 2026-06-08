from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from .download import (
    artifact_files,
    default_cache_root,
    list_pulled_models,
    local_model_files,
    model_cache_dir,
)
from .registry import ModelEndpoint


def default_state_root() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
        return base / "AbteeXAI" / "MaramaRoute"
    base = Path(os.environ.get("XDG_STATE_HOME") or (Path.home() / ".local" / "state"))
    return base / "abteex-ai" / "marama-route"


def cache_report(models: tuple[ModelEndpoint, ...], cache_root: Path | None = None) -> dict[str, Any]:
    root = cache_root or default_cache_root()
    pulled = list_pulled_models(root)
    rows = []
    for item in pulled["models"]:
        model_id = str(item.get("model_id") or "")
        cache_dir = Path(str(item.get("cache_dir") or ""))
        files = [Path(str(path)) for path in item.get("files") or []]
        existing = [path for path in files if path.exists()]
        size_bytes = sum(path.stat().st_size for path in existing if path.is_file())
        rows.append(
            {
                "model_id": model_id,
                "runtime": item.get("runtime", ""),
                "cache_dir": str(cache_dir),
                "file_count": len(existing),
                "size_bytes": size_bytes,
                "size": _format_bytes(size_bytes),
                "valid": bool(existing),
            },
        )
    total = sum(row["size_bytes"] for row in rows)
    return {
        "ok": True,
        "cache_root": str(root),
        "registry_count": len(models),
        "pulled_count": len(rows),
        "total_size_bytes": total,
        "total_size": _format_bytes(total),
        "models": rows,
    }


def verify_cache(
    models: tuple[ModelEndpoint, ...],
    cache_root: Path | None = None,
    *,
    deep: bool = False,
    write_hashes: bool = False,
) -> dict[str, Any]:
    root = cache_root or default_cache_root()
    model_index = {model.model_id: model for model in models}
    rows = []
    for item in list_pulled_models(root)["models"]:
        model_id = str(item.get("model_id") or "")
        model = model_index.get(model_id)
        if item.get("cache_dir"):
            cache_dir = Path(str(item["cache_dir"]))
        elif model is not None:
            cache_dir = model_cache_dir(model, root)
        else:
            cache_dir = root / "unknown" / model_id
        expected = tuple(cache_dir / name for name in artifact_files(model)) if model else ()
        existing = local_model_files(cache_dir)
        missing = [str(path) for path in expected if not path.exists()]
        file_rows = []
        if deep:
            for path in existing:
                size = path.stat().st_size
                file_rows.append(
                    {
                        "path": str(path),
                        "size_bytes": size,
                        "size": _format_bytes(size),
                        "sha256": sha256_file(path),
                    },
                )
        hash_manifest_path = ""
        if write_hashes and deep and file_rows:
            hash_manifest_path = str(write_hash_manifest(model_id, cache_dir, file_rows))
        rows.append(
            {
                "model_id": model_id,
                "known_registry_model": model is not None,
                "cache_dir": str(cache_dir),
                "expected_files": [str(path) for path in expected],
                "local_files": [str(path) for path in existing],
                "missing_files": missing,
                "hash_manifest_path": hash_manifest_path,
                "file_hashes": file_rows,
                "ok": model is not None and bool(existing) and not missing,
            },
        )
    return {
        "ok": all(row["ok"] for row in rows),
        "cache_root": str(root),
        "deep": deep,
        "hash_manifests_written": write_hashes,
        "models": rows,
    }


def remove_cached_model(
    models: tuple[ModelEndpoint, ...],
    model_ref: str,
    *,
    cache_root: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    model = _resolve_model_loose(models, model_ref)
    cache_dir = model_cache_dir(model, cache_root)
    size = _dir_size(cache_dir)
    if cache_dir.exists() and not dry_run:
        shutil.rmtree(cache_dir)
    return {
        "ok": True,
        "model_id": model.model_id,
        "cache_dir": str(cache_dir),
        "removed": cache_dir.exists() is False and not dry_run,
        "dry_run": dry_run,
        "size_bytes": size,
        "size": _format_bytes(size),
    }


def prune_cache(
    models: tuple[ModelEndpoint, ...],
    *,
    cache_root: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    root = cache_root or default_cache_root()
    known_dirs = {model_cache_dir(model, root).resolve() for model in models}
    removed = []
    if root.exists():
        for candidate in root.glob("*/*"):
            if not candidate.is_dir() or candidate.resolve() in known_dirs:
                continue
            size = _dir_size(candidate)
            if not dry_run:
                shutil.rmtree(candidate)
            removed.append({"path": str(candidate), "size_bytes": size, "size": _format_bytes(size)})
    return {"ok": True, "cache_root": str(root), "dry_run": dry_run, "removed": removed, "count": len(removed)}


def inspect_hardware(cache_root: Path | None = None) -> dict[str, Any]:
    memory = _total_memory_bytes()
    disk_path = cache_root or default_cache_root().parent
    while not disk_path.exists() and disk_path.parent != disk_path:
        disk_path = disk_path.parent
    disk = shutil.disk_usage(disk_path)
    gpu = _nvidia_smi()
    return {
        "ok": True,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "cpu_count": os.cpu_count() or 1,
        "memory_bytes": memory,
        "memory": _format_bytes(memory),
        "disk_free_bytes": disk.free,
        "disk_free": _format_bytes(disk.free),
        "gpu": gpu,
    }


def hardware_recommendations(
    models: tuple[ModelEndpoint, ...],
    hardware: dict[str, Any],
    *,
    limit: int = 8,
) -> dict[str, Any]:
    memory_gb = max(float(hardware.get("memory_bytes") or 0) / (1024**3), 1.0)
    rows = []
    for model in models:
        required = _estimated_memory_gb(model)
        if required <= memory_gb * 0.8:
            row = model.to_dict()
            row["estimated_memory_gb"] = required
            rows.append(row)
    rows.sort(key=lambda item: (item["sovereignty_tier"], item["context_tokens"], -item["estimated_memory_gb"]), reverse=True)
    return {"ok": True, "hardware_memory_gb": round(memory_gb, 2), "models": rows[:limit], "count": len(rows)}


def alias_store_path(state_root: Path | None = None) -> Path:
    return (state_root or default_state_root()) / "aliases.json"


def load_aliases(state_root: Path | None = None) -> dict[str, Any]:
    path = alias_store_path(state_root)
    if not path.exists():
        return {"aliases": {}, "favorites": []}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        return {"aliases": {}, "favorites": []}
    return {"aliases": dict(payload.get("aliases") or {}), "favorites": list(payload.get("favorites") or [])}


def save_aliases(payload: dict[str, Any], state_root: Path | None = None) -> Path:
    path = alias_store_path(state_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def set_alias(name: str, model_id: str, state_root: Path | None = None) -> dict[str, Any]:
    payload = load_aliases(state_root)
    payload["aliases"][name] = model_id
    path = save_aliases(payload, state_root)
    return {"ok": True, "alias": name, "model_id": model_id, "path": str(path)}


def delete_alias(name: str, state_root: Path | None = None) -> dict[str, Any]:
    payload = load_aliases(state_root)
    removed = payload["aliases"].pop(name, None)
    path = save_aliases(payload, state_root)
    return {"ok": True, "alias": name, "removed_model_id": removed, "path": str(path)}


def set_favorite(model_id: str, state_root: Path | None = None) -> dict[str, Any]:
    payload = load_aliases(state_root)
    favorites = [item for item in payload["favorites"] if item != model_id]
    favorites.insert(0, model_id)
    payload["favorites"] = favorites[:20]
    path = save_aliases(payload, state_root)
    return {"ok": True, "model_id": model_id, "favorites": payload["favorites"], "path": str(path)}


def resolve_alias(model_ref: str, state_root: Path | None = None) -> str:
    return str(load_aliases(state_root)["aliases"].get(model_ref, model_ref))


def session_path(name: str, state_root: Path | None = None) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in name.strip()) or "default"
    return (state_root or default_state_root()) / "sessions" / f"{safe}.json"


def save_session(name: str, model_id: str, history: list[tuple[str, str]], state_root: Path | None = None) -> Path:
    path = session_path(name, state_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "model_id": model_id,
                "saved_at": int(time.time()),
                "history": [{"user": user, "assistant": assistant} for user, assistant in history],
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return path


def load_session(name: str, state_root: Path | None = None) -> dict[str, Any]:
    path = session_path(name, state_root)
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected session object in {path}")
    payload["path"] = str(path)
    return payload


def export_session_markdown(name: str, output: Path, state_root: Path | None = None) -> Path:
    payload = load_session(name, state_root)
    lines = [f"# MaramaRoute Session: {name}", "", f"Model: `{payload.get('model_id', '')}`", ""]
    for item in payload.get("history") or []:
        if not isinstance(item, dict):
            continue
        lines.extend(["## User", str(item.get("user") or ""), "", "## LumynaX", str(item.get("assistant") or ""), ""])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def write_audit_receipt(receipt: dict[str, Any], state_root: Path | None = None) -> Path:
    audit_dir = (state_root or default_state_root()) / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    receipt_id = str(receipt.get("receipt_id") or _hash_payload(receipt)[:16])
    path = audit_dir / f"{receipt_id}.json"
    payload = dict(receipt)
    payload["written_at"] = int(time.time())
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def list_audit_receipts(state_root: Path | None = None) -> dict[str, Any]:
    audit_dir = (state_root or default_state_root()) / "audit"
    rows = []
    for path in sorted(audit_dir.glob("*.json")) if audit_dir.exists() else []:
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            continue
        rows.append(
            {
                "receipt_id": payload.get("receipt_id") or path.stem,
                "selected_model": payload.get("selected_model"),
                "written_at": payload.get("written_at"),
                "path": str(path),
            },
        )
    return {"ok": True, "count": len(rows), "receipts": rows}


def show_audit_receipt(receipt_id: str, state_root: Path | None = None) -> dict[str, Any]:
    audit_dir = (state_root or default_state_root()) / "audit"
    path = audit_dir / f"{receipt_id}.json"
    if not path.exists():
        matches = sorted(audit_dir.glob(f"{receipt_id}*.json")) if audit_dir.exists() else []
        if not matches:
            raise FileNotFoundError(f"No audit receipt found for {receipt_id}")
        path = matches[0]
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    payload["path"] = str(path)
    return payload


def export_audit_receipts(output: Path, state_root: Path | None = None) -> Path:
    rows = [show_audit_receipt(item["receipt_id"], state_root) for item in list_audit_receipts(state_root)["receipts"]]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"ok": True, "count": len(rows), "receipts": rows}, indent=2, sort_keys=True), encoding="utf-8")
    return output


def estimate_model_download(
    model: ModelEndpoint,
    cache_root: Path | None = None,
    *,
    remote: bool = False,
    all_files: bool = False,
) -> dict[str, Any]:
    files = artifact_files(model)
    cache_dir = model_cache_dir(model, cache_root)
    result = {
        "ok": True,
        "model_id": model.model_id,
        "repo_id": model.repo_id,
        "cache_dir": str(cache_dir),
        "file_count": len(files),
        "files": list(files),
        "estimated_memory_gb": _estimated_memory_gb(model),
        "note": "Exact remote sizes require Hugging Face metadata; this is a runtime memory estimate.",
    }
    if remote:
        metadata = remote_artifact_metadata(model, all_files=all_files)
        result["remote"] = metadata
        if metadata.get("ok"):
            result["remote_total_size_bytes"] = metadata["total_size_bytes"]
            result["remote_total_size"] = metadata["total_size"]
            result["remote_exact_size"] = metadata["exact_size"]
    return result


def remote_artifact_metadata(model: ModelEndpoint, *, all_files: bool = False) -> dict[str, Any]:
    try:
        from huggingface_hub import HfApi  # type: ignore[import-not-found]
    except ImportError:
        return {
            "ok": False,
            "repo_id": model.repo_id,
            "error": "huggingface-hub is not installed",
            "install": "python -m pip install -U huggingface-hub",
        }
    try:
        info = HfApi().model_info(model.repo_id, files_metadata=True)
    except Exception as exc:
        return {"ok": False, "repo_id": model.repo_id, "error": str(exc)}

    selected = set(artifact_files(model))
    rows = []
    total = 0
    exact = True
    for sibling in getattr(info, "siblings", []) or []:
        name = str(getattr(sibling, "rfilename", "") or "")
        if not name:
            continue
        if selected and not all_files and name not in selected:
            continue
        size = getattr(sibling, "size", None)
        lfs = getattr(sibling, "lfs", None)
        if size is None and isinstance(lfs, dict):
            size = lfs.get("size")
        digest = ""
        if isinstance(lfs, dict):
            digest = str(lfs.get("sha256") or lfs.get("oid") or "")
        size_int = int(size) if isinstance(size, int | float) else None
        if size_int is None:
            exact = False
            formatted = ""
        else:
            total += size_int
            formatted = _format_bytes(size_int)
        rows.append(
            {
                "path": name,
                "size_bytes": size_int,
                "size": formatted,
                "sha256": digest,
            },
        )
    missing = sorted(selected - {row["path"] for row in rows}) if selected and not all_files else []
    return {
        "ok": True,
        "repo_id": model.repo_id,
        "all_files": all_files,
        "file_count": len(rows),
        "total_size_bytes": total,
        "total_size": _format_bytes(total),
        "exact_size": exact and not missing,
        "missing_expected_files": missing,
        "files": rows,
    }


def diff_model_registry(
    local_models: tuple[ModelEndpoint, ...],
    remote_payload: dict[str, Any] | list[Any],
) -> dict[str, Any]:
    raw_models = remote_payload.get("models") if isinstance(remote_payload, dict) else remote_payload
    if not isinstance(raw_models, list):
        raise ValueError("Remote registry payload does not contain a model list.")
    remote_models = tuple(ModelEndpoint.from_payload(item) for item in raw_models if isinstance(item, dict))
    local_index = {model.model_id: model for model in local_models}
    remote_index = {model.model_id: model for model in remote_models}
    added = sorted(model_id for model_id in remote_index if model_id not in local_index)
    removed = sorted(model_id for model_id in local_index if model_id not in remote_index)
    changed = sorted(
        model_id
        for model_id in (set(local_index) & set(remote_index))
        if local_index[model_id].to_dict() != remote_index[model_id].to_dict()
    )
    return {
        "ok": True,
        "local_count": len(local_models),
        "remote_count": len(remote_models),
        "added_count": len(added),
        "removed_count": len(removed),
        "changed_count": len(changed),
        "added": added,
        "removed": removed,
        "changed": changed,
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_hash_manifest(model_id: str, cache_dir: Path, file_rows: list[dict[str, Any]]) -> Path:
    path = cache_dir / ".marama-route-sha256.json"
    payload = {
        "model_id": model_id,
        "cache_dir": str(cache_dir),
        "written_at": int(time.time()),
        "files": file_rows,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _resolve_model_loose(models: tuple[ModelEndpoint, ...], model_ref: str) -> ModelEndpoint:
    lowered = model_ref.lower()
    exact = [model for model in models if model_ref in {model.model_id, model.repo_id}]
    if exact:
        return exact[0]
    matches = [model for model in models if lowered in model.model_id.lower() or lowered in model.repo_id.lower()]
    if len(matches) == 1:
        return matches[0]
    if matches:
        raise ValueError("Model reference is ambiguous: " + ", ".join(model.model_id for model in matches[:8]))
    raise ValueError(f"Unknown LumynaX model: {model_ref}")


def _estimated_memory_gb(model: ModelEndpoint) -> float:
    text = f"{model.model_id} {model.primary_artifact}".lower()
    if "480b" in text:
        return 260.0
    if "70b" in text:
        return 48.0
    if "33b" in text or "32b" in text or "30b" in text:
        return 24.0
    if "16b" in text or "15b" in text or "14b" in text:
        return 12.0
    if "9b" in text or "8b" in text or "7b" in text:
        return 8.0
    if "3b" in text:
        return 4.0
    if "1.5b" in text or "15b" in text:
        return 2.5
    if "0.5b" in text or "05b" in text:
        return 1.5
    if model.active_params_b is not None:
        return round(max(1.0, model.active_params_b * 0.9), 2)
    return 6.0


def _total_memory_bytes() -> int:
    if os.name == "nt":
        try:
            import ctypes

            class MemoryStatus(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MemoryStatus()
            status.dwLength = ctypes.sizeof(status)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
            return int(status.ullTotalPhys)
        except Exception:
            return 0
    if hasattr(os, "sysconf"):
        try:
            return int(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES"))
        except (OSError, ValueError):
            return 0
    return 0


def _nvidia_smi() -> list[dict[str, Any]]:
    if shutil.which("nvidia-smi") is None:
        return []
    result = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=name,memory.total",
            "--format=csv,noheader,nounits",
        ],
        text=True,
        capture_output=True,
        timeout=5,
        check=False,
    )
    if result.returncode != 0:
        return []
    rows = []
    for line in result.stdout.splitlines():
        name, _, memory = line.partition(",")
        rows.append({"name": name.strip(), "memory_mb": int(memory.strip() or 0)})
    return rows


def _dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _format_bytes(value: int) -> str:
    size = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{value} B"


def _hash_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
