import os, json, shutil
from huggingface_hub import hf_hub_download
from pathlib import Path
p = hf_hub_download("AbteeXAILab/marama-route", "configs/lumynax_model_registry.json",
                    token=os.environ["HF_TOKEN"], force_download=True)
r = json.loads(open(p, encoding="utf-8").read())
print(f"live registry: {r['model_count']} models, {len(r['models'])} entries")
# Push to network path if reachable, else S:\ local
local = Path(r"S:\hf-publish\marama-route\configs\lumynax_model_registry.json")
local.parent.mkdir(parents=True, exist_ok=True)
shutil.copy(p, local)
print(f"synced to {local}")
# Also try network path
try:
    net = Path(r"\\waikato\users\Hamilton\GtoLdtop\ijadimaa\Desktop\Startup\TinyLuminaX\products\lumynax-marama-route\configs\lumynax_model_registry.json")
    net.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(p, net)
    print(f"synced to {net}")
except Exception as e:
    print(f"network path unreachable: {e}")
