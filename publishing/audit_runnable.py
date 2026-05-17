"""Audit all 58 repos: do they have weights + quickstart.py + requirements.txt + README?"""
import json, os
from pathlib import Path
from huggingface_hub import HfApi

TOKEN = os.environ["HF_TOKEN"]
api = HfApi(token=TOKEN)
REG = Path(r"\\waikato\users\Hamilton\GtoLdtop\ijadimaa\Desktop\Startup\TinyLuminaX\products\lumynax-marama-route\configs\lumynax_model_registry.json")
WEIGHT_EXT = (".gguf", ".safetensors", ".bin", ".pt", ".onnx")

reg = json.loads(REG.read_text(encoding="utf-8"))
print(f"Auditing {len(reg['models'])} repos for runnability...\n")
print(f"{'repo':<70} {'wt':>3} {'rd':>3} {'qs':>3} {'rq':>3} {'lic':>4} {'mod':>4}")
print("-"*92)
not_runnable = []
for m in reg["models"]:
    rid = m["repo_id"]
    try:
        files = api.list_repo_files(rid, token=TOKEN)
        has_weights = any(f.lower().endswith(WEIGHT_EXT) for f in files)
        has_readme = "README.md" in files
        has_quickstart = any(f == "quickstart.py" or f.endswith("/quickstart.py") for f in files)
        has_reqs = "requirements.txt" in files
        has_license = any("license" in f.lower() or "licence" in f.lower() for f in files)
        has_modelfile = any(f.endswith("Modelfile") for f in files)
    except Exception as e:
        print(f"  {rid:<68} ERR {str(e)[:80]}")
        continue
    flag = lambda b: "OK " if b else "-- "
    name = rid.split("/")[-1]
    print(f"{name:<70} {flag(has_weights)} {flag(has_readme)} {flag(has_quickstart)} {flag(has_reqs)} {flag(has_license)} {flag(has_modelfile)}")
    missing = []
    if not has_weights: missing.append("weights")
    if not has_quickstart: missing.append("quickstart")
    if not has_reqs: missing.append("requirements")
    if missing:
        not_runnable.append((rid, missing))

print()
print(f"=== {len(not_runnable)} repos missing key files for one-command run ===")
for rid, miss in not_runnable:
    print(f"  {rid}: missing {miss}")
