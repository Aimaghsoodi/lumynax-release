"""Serial resume v2 — full stage wipe between every model, plus inline per-shard.
Streaming + watchdog + cleanup that actually frees disk between shards."""
import os, sys, time, shutil, threading, fnmatch
from pathlib import Path
from huggingface_hub import HfApi, hf_hub_download

TOKEN = os.environ["HF_TOKEN"]
api = HfApi(token=TOKEN)
STAGE = Path(r"C:\Users\ijadimaa\AppData\Local\Temp\hf-stage")
LOG = Path(r"S:\hf-publish\resume_v2.log")

def log(m):
    line = f"[{time.strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    LOG.open("a", encoding="utf-8").write(line+"\n")

def free_gb():
    return shutil.disk_usage(str(STAGE.parent)).free / (1024**3)

def wipe_stage():
    if STAGE.exists():
        try:
            shutil.rmtree(STAGE, ignore_errors=True)
        except: pass
    STAGE.mkdir(parents=True, exist_ok=True)
    log(f"  stage wiped. free={free_gb():.1f} GB")

def hum(n):
    n = float(n)
    for u in ("B","KB","MB","GB","TB"):
        if n<1024 or u=="TB": return f"{n:.2f} {u}"
        n /= 1024

def already_at_dest(dst, path, size):
    try:
        info = api.repo_info(dst, files_metadata=True, token=TOKEN)
        for s in info.siblings:
            if s.rfilename == path and (s.size or 0) == size and size > 0:
                return True
    except: pass
    return False

def mirror_one_file(src_repo, dst_repo, path, size):
    """Stream one file with watchdog, return True on success."""
    if already_at_dest(dst_repo, path, size):
        log(f"    SKIP (already on dest): {path}")
        return True
    free = free_gb()
    need = size / 1e9
    if free < need + 3:
        wipe_stage()
        free = free_gb()
        if free < need + 3:
            log(f"    !! not enough space: need {need:.1f} GB have {free:.1f} GB")
            return False
    log(f"    download {path} ({hum(size)})  free={free:.1f}GB")
    holder = {"path": None, "err": None}
    done = threading.Event()
    def _do():
        try:
            holder["path"] = hf_hub_download(repo_id=src_repo, filename=path,
                local_dir=str(STAGE / dst_repo.split('/')[-1]), token=TOKEN)
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
        elif time.time() - last_change > 600:
            log(f"    STALL >10min, abandoning {path}")
            return False
    if holder["err"]:
        log(f"    download FAIL: {type(holder['err']).__name__}: {str(holder['err'])[:120]}")
        return False
    dt = time.time() - t0
    log(f"    downloaded in {dt:.0f}s ({(size/dt)/1e6:.1f} MB/s)")
    local = holder["path"]
    # upload
    t1 = time.time()
    try:
        api.upload_file(path_or_fileobj=local, path_in_repo=path,
                        repo_id=dst_repo, repo_type="model", token=TOKEN,
                        commit_message=f"weights: mirror {Path(path).name}")
        log(f"    uploaded in {time.time()-t1:.0f}s")
    except Exception as e:
        log(f"    upload FAIL: {e}")
        try: Path(local).unlink()
        except: pass
        return False
    try: Path(local).unlink()
    except: pass
    # cleanup .cache after every file
    cache = STAGE / dst_repo.split('/')[-1] / ".cache"
    if cache.exists():
        try: shutil.rmtree(cache, ignore_errors=True)
        except: pass
    return True

def mirror_model(dst, src, patterns):
    log(f"\n>>>>>> {dst}  <-  {src}")
    wipe_stage()  # always start clean
    files = api.repo_info(src, files_metadata=True, token=TOKEN).siblings
    matched = [(f.rfilename, f.size or 0) for f in files
               if any(fnmatch.fnmatch(f.rfilename, p) for p in patterns)]
    matched.sort(key=lambda x: x[1])  # smallest shard first
    log(f"  {len(matched)} files matched, total {hum(sum(s for _,s in matched))}")
    ok = fail = 0
    for path, size in matched:
        if mirror_one_file(src, dst, path, size):
            ok += 1
        else:
            fail += 1
    log(f"  done: {ok} ok, {fail} fail")
    wipe_stage()
    return ok, fail


PLAN = [
    ("AbteeXAILab/lumynax-coder-codellama-70b-instruct-gguf",
     "TheBloke/CodeLlama-70B-Instruct-GGUF", ["codellama-70b-instruct.Q4_K_M.gguf"]),
    ("AbteeXAILab/lumynax-reasoning-deepseek-r1-distill-llama-70b-gguf",
     "bartowski/DeepSeek-R1-Distill-Llama-70B-GGUF", ["DeepSeek-R1-Distill-Llama-70B-Q4_K_M.gguf"]),
    ("AbteeXAILab/lumynax-frontier-coder-deepseek-v25-1210-gguf",
     "bartowski/DeepSeek-V2.5-1210-GGUF", ["DeepSeek-V2.5-1210-Q4_K_M/*.gguf"]),
    ("AbteeXAILab/lumynax-frontier-coder-qwen3-480b-a35b-gguf",
     "unsloth/Qwen3-Coder-480B-A35B-Instruct-GGUF", ["Q4_K_M/*.gguf"]),
    ("AbteeXAILab/lumynax-reasoning-deepseek-prover-v2-671b-gguf",
     "unsloth/DeepSeek-Prover-V2-671B-GGUF", ["Q4_K_M/*.gguf"]),
]


def main():
    log(f"=== resume v2 start === free={free_gb():.1f} GB ===")
    for i, (dst, src, pats) in enumerate(PLAN, 1):
        log(f"\n[{i}/{len(PLAN)}]  {dst}")
        try:
            mirror_model(dst, src, pats)
        except Exception as e:
            log(f"  FATAL: {e}")
    log("=== resume v2 end ===")


if __name__ == "__main__":
    main()
