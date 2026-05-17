"""
Stream-mirror weights from upstream repos to the 8 new AbteeXAILab repos.

Strategy: for each file, download to local stage -> upload to dest -> delete local.
Resume-safe: skips files that already exist at dest with the right size.

Writes progress to S:\\hf-publish\\mirror_progress.log so it can be tailed.
"""
from __future__ import annotations
import fnmatch
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

from huggingface_hub import HfApi, hf_hub_download

TOKEN = os.environ["HF_TOKEN"]
api = HfApi(token=TOKEN)

STAGE = Path(r"C:\Users\ijadimaa\AppData\Local\Temp\hf-stage")
STAGE.mkdir(parents=True, exist_ok=True)
LOG = Path(r"S:\hf-publish\mirror_progress.log")


def log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


# Mirror plan -- ordered smallest first so we get fast confirmations
MIRROR_PLAN: List[Dict[str, Any]] = [
    # 1) DBRX -- Q2_K is the highest-quality non-imatrix quant for DBRX on HF (no Q4_K_M exists)
    {
        "dest": "AbteeXAILab/lumynax-frontier-dbrx-instruct-132b-gguf",
        "source": "mradermacher/dbrx-instruct-GGUF",
        "patterns": ["dbrx-instruct.Q2_K.gguf"],
        "size_hint_gb": 48,
    },
    # 2) Qwen2.5-VL-72B -- Q4_K_M 47.4 GB + mmproj ~2 GB
    {
        "dest": "AbteeXAILab/lumynax-multimodal-qwen25-vl-72b-instruct-gguf",
        "source": "ggml-org/Qwen2.5-VL-72B-Instruct-GGUF",
        "patterns": ["*Q4_K_M*.gguf", "*mmproj*"],
        "size_hint_gb": 50,
    },
    # 3) Mixtral-8x22B -- 2 shards, 80 GB
    {
        "dest": "AbteeXAILab/lumynax-frontier-mixtral-8x22b-instruct-gguf",
        "source": "MaziyarPanahi/Mixtral-8x22B-Instruct-v0.1-GGUF",
        "patterns": ["*.Q4_K_M-*of-*.gguf"],
        "size_hint_gb": 80,
    },
    # 4) MiniMax-M2 -- 3 shards, 129 GB
    {
        "dest": "AbteeXAILab/lumynax-frontier-minimax-m2-230b",
        "source": "unsloth/MiniMax-M2-GGUF",
        "patterns": ["Q4_K_M/*"],
        "size_hint_gb": 129,
    },
    # 5) Qwen3-235B -- 3 shards, 132 GB
    {
        "dest": "AbteeXAILab/lumynax-frontier-qwen3-235b-a22b-instruct",
        "source": "unsloth/Qwen3-235B-A22B-Instruct-2507-GGUF",
        "patterns": ["Q4_K_M/*"],
        "size_hint_gb": 132,
    },
    # 6) InternVL3-78B -- 33 safetensors + tokenizer + config, ~152 GB
    {
        "dest": "AbteeXAILab/lumynax-multimodal-internvl3-78b-instruct",
        "source": "OpenGVLab/InternVL3-78B-Instruct",
        "patterns": [
            "model-*.safetensors",
            "model.safetensors.index.json",
            "config.json",
            "tokenizer*",
            "preprocessor_config.json",
            "added_tokens.json",
            "special_tokens_map.json",
            "generation_config.json",
            "configuration_internvl_chat.py",
            "modeling_internvl_chat.py",
            "conversation.py",
        ],
        "size_hint_gb": 152,
    },
    # 7) GLM-4.6 -- 5 shards, 201 GB
    {
        "dest": "AbteeXAILab/lumynax-reasoning-glm46-355b-moe",
        "source": "unsloth/GLM-4.6-GGUF",
        "patterns": ["Q4_K_M/*"],
        "size_hint_gb": 201,
    },
    # 8) Pixtral-Large -- 52 safetensors shards, ~245 GB
    {
        "dest": "AbteeXAILab/lumynax-multimodal-pixtral-large-124b",
        "source": "mistralai/Pixtral-Large-Instruct-2411",
        "patterns": [
            "consolidated-*.safetensors",
            "consolidated.safetensors.index.json",
            "params.json",
            "tekken.json",
            "tokenizer.model*",
            "tokenizer.json",
            "tokenizer_config.json",
            "config.json",
        ],
        "size_hint_gb": 245,
    },
]


def list_with_meta(repo: str) -> List[Dict[str, Any]]:
    info = api.repo_info(repo, files_metadata=True, token=TOKEN)
    return [{"path": s.rfilename, "size": s.size or 0} for s in info.siblings]


def matches(name: str, patterns: List[str]) -> bool:
    return any(fnmatch.fnmatch(name, p) for p in patterns)


def already_at_dest(dest: str, dest_files: List[Dict[str, Any]], path: str, size: int) -> bool:
    for f in dest_files:
        if f["path"] == path and f["size"] == size and size > 0:
            return True
    return False


def hum(n: float) -> str:
    n = float(n)
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or u == "TB":
            return f"{n:.2f} {u}"
        n /= 1024


def free_gb() -> float:
    total, used, free = shutil.disk_usage(str(STAGE))
    return free / (1024 ** 3)


def mirror_repo(plan: Dict[str, Any]) -> Dict[str, Any]:
    dest = plan["dest"]
    source = plan["source"]
    patterns = plan["patterns"]
    log(f"\n=== {dest}  <-  {source} ===")
    log(f"    free local: {free_gb():.1f} GB, target ~{plan.get('size_hint_gb','?')} GB")

    src_files = list_with_meta(source)
    matched = [f for f in src_files if matches(f["path"], patterns)]
    matched.sort(key=lambda x: x["size"])  # smallest first
    if not matched:
        log(f"  WARNING no files matched in {source} for patterns {patterns}")
        return {"dest": dest, "matched": 0, "uploaded": 0, "skipped": 0}

    dest_files = []
    try:
        dest_files = list_with_meta(dest)
    except Exception as e:
        log(f"  could not list dest (will treat as empty): {e}")

    total = sum(f["size"] for f in matched)
    log(f"  {len(matched)} matched files, total {hum(total)}")

    stage_dir = STAGE / dest.split("/")[-1]
    stage_dir.mkdir(parents=True, exist_ok=True)

    uploaded = 0
    skipped = 0
    failed: List[str] = []

    for i, f in enumerate(matched, 1):
        path = f["path"]
        size = f["size"]
        if already_at_dest(dest, dest_files, path, size):
            log(f"  [{i}/{len(matched)}] SKIP (already there, exact size): {path}")
            skipped += 1
            continue
        # ensure enough free space
        need_gb = size / (1024 ** 3)
        free = free_gb()
        if free < need_gb + 2:
            log(f"  [{i}/{len(matched)}] !! only {free:.1f} GB free, need {need_gb:.1f}. Cleaning stage...")
            for p in stage_dir.rglob("*"):
                if p.is_file():
                    try: p.unlink()
                    except: pass
            free = free_gb()
            if free < need_gb + 2:
                log(f"  STOP: still only {free:.1f} GB free, cannot continue.")
                failed.append(path); break

        # download with stall watchdog
        t0 = time.time()
        log(f"  [{i}/{len(matched)}] download {path} ({hum(size)})  free={free:.1f}GB")
        import threading
        download_done = threading.Event()
        local_holder = {"path": None, "error": None}
        def _do_download():
            try:
                local_holder["path"] = hf_hub_download(
                    repo_id=source, filename=path,
                    local_dir=str(stage_dir),
                    token=TOKEN,
                )
            except Exception as e:
                local_holder["error"] = e
            finally:
                download_done.set()
        t = threading.Thread(target=_do_download, daemon=True)
        t.start()
        # watchdog: check .incomplete file growth every 60s, abort if stalled > 300s
        last_size = -1; last_change = time.time()
        while not download_done.wait(60):
            # find the .incomplete file under stage_dir
            cur_size = 0
            try:
                for inc in stage_dir.rglob("*.incomplete"):
                    cur_size = max(cur_size, inc.stat().st_size)
            except Exception:
                pass
            if cur_size != last_size:
                last_size = cur_size
                last_change = time.time()
            elif time.time() - last_change > 300:
                log(f"    STALL detected: no growth for {int(time.time()-last_change)}s at {hum(cur_size)}. Aborting this file.")
                failed.append(path)
                # cannot cleanly cancel the thread; the next loop iteration will reuse stage and resume
                break
        if not download_done.is_set():
            # bail out of this file; thread may leak but the .incomplete will resume next run
            continue
        if local_holder["error"]:
            log(f"    download FAIL: {type(local_holder['error']).__name__}: {local_holder['error']}")
            failed.append(path); continue
        local = local_holder["path"]
        dt_dl = time.time() - t0
        log(f"    downloaded in {dt_dl:.0f}s ({(size/dt_dl)/1e6:.1f} MB/s)")

        # upload
        t1 = time.time()
        try:
            api.upload_file(
                path_or_fileobj=local,
                path_in_repo=path,
                repo_id=dest,
                repo_type="model",
                token=TOKEN,
                commit_message=f"weights: mirror {Path(path).name} from {source}",
            )
            dt_up = time.time() - t1
            log(f"    uploaded in {dt_up:.0f}s ({(size/dt_up)/1e6:.1f} MB/s)")
            uploaded += 1
        except Exception as e:
            log(f"    upload FAIL: {type(e).__name__}: {e}")
            failed.append(path)
            try: Path(local).unlink()
            except: pass
            continue

        # cleanup
        try:
            Path(local).unlink()
        except Exception:
            pass
        # remove empty parent dirs in stage
        try:
            p = Path(local).parent
            while p != stage_dir and p.exists() and not any(p.iterdir()):
                p.rmdir(); p = p.parent
        except Exception:
            pass

    return {"dest": dest, "matched": len(matched), "uploaded": uploaded, "skipped": skipped, "failed": failed}


def main() -> None:
    log(f"=== MIRROR RUN START === free local: {free_gb():.1f} GB ===")
    only = sys.argv[1] if len(sys.argv) > 1 else None
    results = []
    for plan in MIRROR_PLAN:
        if only and only not in plan["dest"]:
            continue
        try:
            results.append(mirror_repo(plan))
        except KeyboardInterrupt:
            log("interrupted.")
            break
        except Exception as e:
            log(f"FATAL mirroring {plan['dest']}: {e}")
            results.append({"dest": plan["dest"], "error": str(e)})
    log("\n=== SUMMARY ===")
    for r in results:
        log(f"  {r}")
    log("=== MIRROR RUN END ===")


if __name__ == "__main__":
    main()
