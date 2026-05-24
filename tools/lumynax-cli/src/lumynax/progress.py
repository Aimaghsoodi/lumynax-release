"""Progress bar for `lumynax pull` — wraps huggingface_hub.snapshot_download with a Rich progress."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, TransferSpeedColumn, DownloadColumn


def pull_with_progress(repo_id: str, local_dir: Path,
                       include_weights: bool = True,
                       token: Optional[str] = None) -> Path:
    """Snapshot-download with a live progress bar showing total bytes + per-file ETA."""
    from huggingface_hub import HfApi, snapshot_download

    api = HfApi(token=token)
    info = api.repo_info(repo_id, files_metadata=True)
    weight_exts = (".gguf", ".safetensors", ".bin", ".pt", ".pth")
    if include_weights:
        files = [(s.rfilename, s.size or 0) for s in info.siblings]
    else:
        files = [(s.rfilename, s.size or 0) for s in info.siblings
                 if not s.rfilename.lower().endswith(weight_exts)]
    total = sum(sz for _, sz in files)

    cols = [
        TextColumn("[bold cyan]{task.fields[filename]}"),
        BarColumn(bar_width=30),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
    ]
    with Progress(*cols, transient=False) as prog:
        # Single aggregate task — HF's snapshot_download doesn't expose per-file callbacks,
        # so we poll the filesystem instead.
        task = prog.add_task("download", total=total, filename=repo_id.split("/")[-1])
        import threading, time
        stop = threading.Event()
        def watch():
            while not stop.is_set():
                done = 0
                if local_dir.exists():
                    for f in local_dir.rglob("*"):
                        if f.is_file(): done += f.stat().st_size
                prog.update(task, completed=min(done, total))
                time.sleep(1.0)
        t = threading.Thread(target=watch, daemon=True); t.start()
        try:
            allow = None if include_weights else [
                "README.md","quickstart.py","requirements.txt","docs/*","ollama/Modelfile",
                "release_export_manifest.json","LICENSE*","VERSION*"]
            snapshot_download(repo_id=repo_id, local_dir=str(local_dir),
                              token=token, allow_patterns=allow)
        finally:
            stop.set(); t.join(timeout=2)
            prog.update(task, completed=total)
    return local_dir
