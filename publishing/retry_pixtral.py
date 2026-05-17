"""Retry-loop just the 5 missing Pixtral shards. Runs until all done or 6 retries each."""
import os, sys, time, shutil, threading
from pathlib import Path
from huggingface_hub import HfApi, hf_hub_download

TOKEN = os.environ["HF_TOKEN"]
api = HfApi(token=TOKEN)
SRC = "mistralai/Pixtral-Large-Instruct-2411"
DST = "AbteeXAILab/lumynax-multimodal-pixtral-large-124b"
STAGE = Path(r"C:\Users\ijadimaa\AppData\Local\Temp\hf-stage\pixtral-retry")
STAGE.mkdir(parents=True, exist_ok=True)
LOG = Path(r"S:\hf-publish\pixtral_retry.log")

def log(m):
    line = f"[{time.strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    LOG.open("a", encoding="utf-8").write(line + "\n")

def missing():
    info = api.repo_info(DST, files_metadata=True, token=TOKEN)
    have = {s.rfilename for s in info.siblings if 'consolidated' in s.rfilename and s.size}
    expected = {f'consolidated-{i:05d}-of-00052.safetensors' for i in range(1,53)}
    return sorted(expected - have)

def fetch_with_watchdog(path, timeout_stall=600):
    """Download with 10-min stall watchdog."""
    holder = {"path": None, "error": None}
    done = threading.Event()
    def _do():
        try:
            holder["path"] = hf_hub_download(repo_id=SRC, filename=path, local_dir=str(STAGE), token=TOKEN)
        except Exception as e:
            holder["error"] = e
        finally:
            done.set()
    t = threading.Thread(target=_do, daemon=True); t.start()
    last_size = -1; last_change = time.time()
    while not done.wait(60):
        cur = 0
        for inc in STAGE.rglob("*.incomplete"):
            try: cur = max(cur, inc.stat().st_size)
            except: pass
        if cur != last_size: last_size = cur; last_change = time.time()
        elif time.time() - last_change > timeout_stall:
            log(f"  stall: no growth for {int(time.time()-last_change)}s at {cur/1e9:.2f} GB")
            return None
    if holder["error"]:
        log(f"  download err: {holder['error']}")
        return None
    return holder["path"]

def upload(local, path):
    try:
        api.upload_file(path_or_fileobj=local, path_in_repo=path, repo_id=DST, repo_type="model",
                        token=TOKEN, commit_message=f"weights: mirror {Path(path).name} (retry)")
        return True
    except Exception as e:
        log(f"  upload err: {e}")
        return False

def cleanup_stage():
    for p in STAGE.rglob("*"):
        if p.is_file():
            try: p.unlink()
            except: pass

def main():
    for attempt in range(1, 11):  # up to 10 passes
        miss = missing()
        if not miss:
            log(f"=== all Pixtral shards on dest after attempt {attempt-1}. DONE.")
            return
        log(f"=== attempt {attempt}: {len(miss)} shards still missing ===")
        for path in miss:
            log(f"--- retry {path}")
            cleanup_stage()
            local = fetch_with_watchdog(path, timeout_stall=600)
            if not local:
                log(f"  skip (couldn't download this pass)")
                continue
            log(f"  downloaded {Path(local).stat().st_size/1e9:.2f} GB")
            if upload(local, path):
                log(f"  uploaded OK")
            try: Path(local).unlink()
            except: pass
        wait = min(60 * attempt, 600)
        log(f"--- end of pass {attempt}, sleeping {wait}s before next pass ---")
        time.sleep(wait)
    log("=== max attempts reached. Run script again to continue. ===")

if __name__ == "__main__":
    main()
