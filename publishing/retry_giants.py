"""Retry-loop just the missing Qwen3-Coder-480B + Prover-V2-671B shards.
Each pass: wipe stage, check what's missing on dest, mirror what's needed."""
import os, sys, time, shutil, threading, fnmatch
from pathlib import Path
sys.path.insert(0, r"S:\hf-publish")
from huggingface_hub import HfApi, hf_hub_download

TOKEN = os.environ["HF_TOKEN"]
api = HfApi(token=TOKEN)
STAGE = Path(r"C:\Users\ijadimaa\AppData\Local\Temp\hf-stage")
LOG = Path(r"S:\hf-publish\retry_giants.log")

def log(m):
    line = f"[{time.strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    LOG.open("a", encoding="utf-8").write(line+"\n")

def free_gb():
    return shutil.disk_usage(str(STAGE.parent)).free / (1024**3)

def wipe():
    if STAGE.exists():
        shutil.rmtree(STAGE, ignore_errors=True)
    STAGE.mkdir(parents=True, exist_ok=True)

def missing(dst, src, patterns):
    src_files = api.repo_info(src, files_metadata=True, token=TOKEN).siblings
    matched = [(f.rfilename, f.size or 0) for f in src_files
               if any(fnmatch.fnmatch(f.rfilename, p) for p in patterns)]
    dst_files = {s.rfilename: (s.size or 0) for s in api.repo_info(dst, files_metadata=True, token=TOKEN).siblings}
    missing = [(p,s) for p,s in matched if dst_files.get(p,0) != s or s == 0]
    return matched, missing

def mirror_one(src, dst, path, size, attempt):
    if free_gb() < (size/1e9 + 0.5):
        wipe()
        if free_gb() < (size/1e9 + 0.5):
            log(f"    !! still not enough space ({free_gb():.1f} GB)")
            return False
    log(f"  [attempt {attempt}] download {path} ({size/1e9:.1f} GB)  free={free_gb():.1f} GB")
    holder = {"path": None, "err": None}
    done = threading.Event()
    def _do():
        try:
            holder["path"] = hf_hub_download(repo_id=src, filename=path,
                local_dir=str(STAGE / dst.split('/')[-1]), token=TOKEN)
        except Exception as e:
            holder["err"] = e
        finally:
            done.set()
    th = threading.Thread(target=_do, daemon=True); th.start()
    last_size = -1; last_change = time.time(); t0 = time.time()
    while not done.wait(60):
        cur = 0
        try:
            for inc in (STAGE).rglob("*.incomplete"):
                cur = max(cur, inc.stat().st_size)
        except: pass
        if cur != last_size:
            last_size = cur; last_change = time.time()
        elif time.time() - last_change > 900:  # 15-min stall
            log(f"    STALL >15min, abandoning"); return False
    if holder["err"]:
        log(f"    download FAIL: {str(holder['err'])[:120]}"); return False
    log(f"    downloaded in {time.time()-t0:.0f}s")
    local = holder["path"]
    t1 = time.time()
    try:
        api.upload_file(path_or_fileobj=local, path_in_repo=path, repo_id=dst,
                        repo_type="model", token=TOKEN, commit_message=f"weights: retry {Path(path).name}")
        log(f"    uploaded in {time.time()-t1:.0f}s")
    except Exception as e:
        log(f"    upload FAIL: {str(e)[:120]}")
        try: Path(local).unlink()
        except: pass
        return False
    try: Path(local).unlink()
    except: pass
    cache = STAGE / dst.split('/')[-1] / ".cache"
    if cache.exists():
        shutil.rmtree(cache, ignore_errors=True)
    return True

TARGETS = [
    ("AbteeXAILab/lumynax-frontier-coder-qwen3-480b-a35b-gguf",
     "unsloth/Qwen3-Coder-480B-A35B-Instruct-GGUF", ["Q4_K_M/*.gguf"]),
    ("AbteeXAILab/lumynax-reasoning-deepseek-prover-v2-671b-gguf",
     "unsloth/DeepSeek-Prover-V2-671B-GGUF", ["Q4_K_M/*.gguf"]),
]

MAX_PASSES = 6
for attempt in range(1, MAX_PASSES+1):
    log(f"\n=== PASS {attempt}/{MAX_PASSES} ===")
    any_missing = False
    for dst, src, pats in TARGETS:
        matched, miss = missing(dst, src, pats)
        log(f"\n{dst}: {len(matched)-len(miss)}/{len(matched)} done; missing {len(miss)}")
        if not miss: continue
        any_missing = True
        wipe()
        miss.sort(key=lambda x: x[1])  # smallest first
        for path, size in miss:
            mirror_one(src, dst, path, size, attempt)
    if not any_missing:
        log("=== ALL DONE ==="); break
    log(f"--- end pass {attempt}, sleeping 60s before next ---")
    time.sleep(60)
log("=== retry_giants end ===")
