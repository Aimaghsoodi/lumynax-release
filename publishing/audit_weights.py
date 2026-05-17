"""Audit every repo on AbteeXAILab — list weight files (>10MB) and total size."""
import json, os
from pathlib import Path
from huggingface_hub import HfApi

TOKEN = os.environ["HF_TOKEN"]
api = HfApi(token=TOKEN)
REG = Path(r"\\waikato\users\Hamilton\GtoLdtop\ijadimaa\Desktop\Startup\TinyLuminaX\products\lumynax-marama-route\configs\lumynax_model_registry.json")

WEIGHT_EXT = (".gguf", ".safetensors", ".bin", ".pt", ".onnx")

def human(n):
    n = float(n or 0)
    for u in ("B","KB","MB","GB","TB"):
        if n < 1024 or u == "TB": return f"{n:6.2f} {u}"
        n /= 1024

reg = json.loads(REG.read_text(encoding="utf-8"))
rows = []
for m in reg["models"]:
    rid = m["repo_id"]
    try:
        info = api.repo_info(rid, files_metadata=True, token=TOKEN)
        weights = [(s.rfilename, s.size or 0) for s in info.siblings if s.rfilename.lower().endswith(WEIGHT_EXT)]
        total = sum(s for _, s in weights)
        rows.append((rid, len(weights), total, weights))
    except Exception as e:
        rows.append((rid, -1, 0, [("ERROR: "+str(e)[:80], 0)]))

print(f"{'repo':<70} {'#w':>4} {'size':>10}")
print("-"*92)
no_weights = []
has_weights = []
for rid, nw, total, ws in rows:
    mark = "  " if nw>0 else "!!"
    print(f"{mark} {rid:<66} {nw:>4} {human(total):>10}")
    if nw <= 0: no_weights.append(rid)
    else: has_weights.append((rid, total))

print()
print(f"=== {len(has_weights)} repos with weights, {len(no_weights)} without ===")
print(f"=== total bytes in weight files: {human(sum(t for _,t in has_weights))} ===")
print()
print("Repos WITHOUT weight files:")
for r in no_weights: print("  -", r)
