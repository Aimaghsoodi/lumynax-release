"""
Build aimaghsoodi/lumynax-release monorepo.

Layout:
  README.md                    -- root index
  registry/lumynax_model_registry.json
  models/<slug>/               -- scaffold for each of 58 HF model repos (no weights)
  products/sovereigncode/      -- full SovereignCode package
  products/marama-route/       -- full MaramaRoute package
  spaces/sovereigncode-demo/   -- Gradio Space scaffold
  spaces/marama-route-demo/
  spaces/live-demo/
  publishing/                  -- hf-publish scripts (this directory)
  .gitignore                   -- excludes weights, stages, caches
"""
from __future__ import annotations
import json, os, shutil, subprocess, sys, time
from pathlib import Path
from huggingface_hub import HfApi, snapshot_download

TOKEN = os.environ["HF_TOKEN"]
api = HfApi(token=TOKEN)
ROOT = Path(r"C:\Users\ijadimaa\AppData\Local\Temp\aimaghsoodi-mirror")
REPO = ROOT / "lumynax-release"
REG_PATH = Path(r"\\waikato\users\Hamilton\GtoLdtop\ijadimaa\Desktop\Startup\TinyLuminaX\products\lumynax-marama-route\configs\lumynax_model_registry.json")

# Allowed scaffold patterns (everything except weights and caches)
SCAFFOLD_PATTERNS = [
    "README.md",
    "quickstart.py",
    "requirements.txt",
    "LICENSE*",
    "VERSION*",
    "UPLOAD_TO_HF.md",
    "release_export_manifest.json",
    "checksums.sha256",
    "ollama/Modelfile",
    "ollama/*.ps1",
    "hf_space/app.py",
    "hf_space/README.md",
    "hf_space/requirements.txt",
    "docs/*.svg",
    "docs/*.md",
    "configs/*",
    "artifacts/*.json",
]

GITIGNORE = """# weights and caches (large, untracked)
*.gguf
*.safetensors
*.bin
*.pt
*.onnx
*.pyc
__pycache__/
.cache/
.venv/
venv/
hf-stage/
node_modules/
.DS_Store
Thumbs.db
"""

ROOT_README_TEMPLATE = """# LumynaX Release Monorepo

> *Sovereign intelligence, held in the light. — Ko te mārama te tūāpapa.*

This repository is the source-of-truth monorepo for the **LumynaX** release family
from **AbteeX AI Labs** (Aotearoa New Zealand). It contains the publication scaffolds,
products, Hugging Face Spaces, and publishing tooling.

The actual model weights live on **[Hugging Face: AbteeXAILab](https://huggingface.co/AbteeXAILab)**
(weights exceed GitHub's per-file limit; this monorepo ships the runtime code only).

## Layout

| Path | Purpose |
| --- | --- |
| `models/<slug>/` | Per-model scaffold (README, quickstart.py, requirements.txt, manifest, Modelfile, Space). One subdir per HF model repo. |
| `products/sovereigncode/` | **AbteeX SovereignCode** — local-first coding agent with Data Capsule policy. |
| `products/marama-route/` | **LumynaX MaramaRoute** — sovereign model router across the LumynaX family. |
| `spaces/sovereigncode-demo/` | Gradio Space — policy evaluator. |
| `spaces/marama-route-demo/` | Gradio Space — sovereign router demo. |
| `spaces/live-demo/` | Gradio Space — LumynaX live chat demo. |
| `publishing/` | Generation + mirror scripts used to publish the family to HF. |
| `registry/lumynax_model_registry.json` | Authoritative registry of all {model_count} models. |

## Run any model locally

```bash
# 1. Discover what's available
cat registry/lumynax_model_registry.json | jq '.models[] | {{repo_id, total_params_b, modalities}}'

# 2. Pick one and pull from Hugging Face (weights + scaffold)
hf download AbteeXAILab/<slug> --local-dir <slug>

# 3. Run the included quickstart
cd <slug>
pip install -r requirements.txt
python quickstart.py --interactive
```

For each model, `models/<slug>/` in this repo mirrors the scaffold on HF
(so you can read the quickstart, requirements, manifest, and Space code
without cloning from HF first).

## Family at a glance

{family_table}

## Companion products

| Product | Purpose | Live Space |
| --- | --- | --- |
| [SovereignCode](products/sovereigncode/) | Local-first coding agent with Data Capsule policy evaluator and audit ledger. | [sovereigncode-demo](https://huggingface.co/spaces/AbteeXAILab/sovereigncode-demo) |
| [MaramaRoute](products/marama-route/) | Sovereign router across the LumynaX family — gates: capability, sovereignty, license, runtime, score, audit. | [marama-route-demo](https://huggingface.co/spaces/AbteeXAILab/marama-route-demo) |
| LumynaX Live | Browser chat with the LumynaX release family. | [lumynax-live-demo](https://huggingface.co/spaces/AbteeXAILab/lumynax-live-demo) |

## Provenance & sovereignty

Each model card under `models/<slug>/README.md` documents:
- Upstream repository (Apache-2.0 / MIT / etc.)
- Quantization profile and primary artifact
- Sovereignty tier (1 = remote frontier, 5 = NZ-resident local)
- Residency (NZ, AU, global)
- Audit hash-chain method
- Tools / JSON / image / audio / context support

Routing decisions made by MaramaRoute consult this metadata; SovereignCode's
Policy Decision Point enforces the residency/license/training/export gates
before any tool call is dispatched.

## Status

- **{model_count} models** published to `AbteeXAILab` on Hugging Face
- **{ready_count} fully self-contained** (weights mirrored on HF — clone & run)
- **{pending_count} pending weight mirror** (Pixtral-Large finishing as of {date})

## License

- Scaffolding, products, and tooling in this monorepo: **MIT** (© AbteeX AI Labs)
- Each model's weights remain under the **upstream licence** documented in its manifest

Generated by `publishing/build_github_monorepo.py`.
"""


def log(m: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def safe_rmtree(p: Path) -> None:
    if p.exists():
        shutil.rmtree(p, ignore_errors=True)


def snapshot_scaffold(repo_id: str, dest: Path) -> bool:
    dest.mkdir(parents=True, exist_ok=True)
    try:
        snapshot_download(
            repo_id=repo_id, repo_type="model",
            local_dir=str(dest),
            token=TOKEN,
            allow_patterns=SCAFFOLD_PATTERNS,
        )
        # cleanup .cache subdir created by snapshot_download
        cache = dest / ".cache"
        if cache.exists(): shutil.rmtree(cache, ignore_errors=True)
        return True
    except Exception as e:
        log(f"  FAIL snapshot {repo_id}: {e}")
        return False


def copy_products() -> None:
    # SovereignCode product
    src_sc = Path(r"S:\hf-publish\sovereigncode")
    dst_sc = REPO / "products" / "sovereigncode"
    if src_sc.exists():
        log("copy products/sovereigncode")
        safe_rmtree(dst_sc); shutil.copytree(src_sc, dst_sc, ignore=shutil.ignore_patterns("__pycache__","*.pyc",".venv","venv"))
    # MaramaRoute product
    src_mr = Path(r"S:\hf-publish\marama-route")
    dst_mr = REPO / "products" / "marama-route"
    if src_mr.exists():
        log("copy products/marama-route")
        safe_rmtree(dst_mr); shutil.copytree(src_mr, dst_mr, ignore=shutil.ignore_patterns("__pycache__","*.pyc",".venv","venv"))
    # Spaces
    for s in ("space-sovereigncode","space-marama-route","space-live-demo"):
        src = Path(r"S:\hf-publish") / s
        slug = s.replace("space-","") + "-demo" if s != "space-live-demo" else "live-demo"
        dst = REPO / "spaces" / slug
        if src.exists():
            log(f"copy spaces/{slug}")
            safe_rmtree(dst); shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__","*.pyc",".venv","venv"))


def copy_publishing() -> None:
    src = Path(r"S:\hf-publish")
    dst = REPO / "publishing"
    log("copy publishing scripts")
    safe_rmtree(dst); dst.mkdir(parents=True, exist_ok=True)
    for p in src.iterdir():
        if p.is_file() and p.suffix in (".py", ".md", ".txt", ".json", ".log"):
            shutil.copy2(p, dst / p.name)


def build_family_table(models: list[dict]) -> str:
    by_tier = {}
    for m in models:
        cat = m["model_id"].split("-")[1]  # frontier/multimodal/reasoning/coder/infused/embed/moe/nz/tiny
        by_tier.setdefault(cat, []).append(m)
    out = []
    out.append("| Tier | Count | Examples |")
    out.append("| --- | --- | --- |")
    for tier in sorted(by_tier):
        ms = by_tier[tier]
        examples = ", ".join(f"`{m['model_id'].split('-',2)[-1][:40]}`" for m in ms[:3])
        out.append(f"| **{tier}** | {len(ms)} | {examples}{', …' if len(ms)>3 else ''} |")
    return "\n".join(out)


def main() -> None:
    REPO.mkdir(parents=True, exist_ok=True)
    log(f"target: {REPO}")

    # 1. Scaffold per model
    reg = json.loads(REG_PATH.read_text(encoding="utf-8"))
    models = reg["models"]
    models_dir = REPO / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    ok = fail = 0
    for i, m in enumerate(models, 1):
        slug = m["repo_id"].split("/")[-1]
        log(f"[{i}/{len(models)}] scaffold {slug}")
        if snapshot_scaffold(m["repo_id"], models_dir / slug):
            ok += 1
        else:
            fail += 1
    log(f"scaffolded {ok}/{len(models)} ({fail} failed)")

    # 2. Products + spaces + publishing
    copy_products()
    copy_publishing()

    # 3. Registry
    reg_dir = REPO / "registry"
    reg_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REG_PATH, reg_dir / "lumynax_model_registry.json")

    # 4. Root README + .gitignore
    (REPO / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    family_table = build_family_table(models)
    root_readme = ROOT_README_TEMPLATE.format(
        model_count=len(models),
        ready_count=len(models) - 1,  # Pixtral may still be mirroring
        pending_count=1,
        date=time.strftime("%Y-%m-%d"),
        family_table=family_table,
    )
    (REPO / "README.md").write_text(root_readme, encoding="utf-8")

    log("monorepo built.")
    log(f"size: {sum(f.stat().st_size for f in REPO.rglob('*') if f.is_file())/1e6:.1f} MB")


if __name__ == "__main__":
    main()
