"""Create + push all product repos and Spaces to AbteeXAILab on Hugging Face."""
from __future__ import annotations

import os
from pathlib import Path
from huggingface_hub import HfApi

TOKEN = os.environ["HF_TOKEN"]
api = HfApi(token=TOKEN)
ORG = "AbteeXAILab"


PUSHES = [
    # (repo_type, repo_id, local_dir, exclude)
    ("model",  f"{ORG}/sovereigncode",      r"S:\hf-publish\sovereigncode",        []),
    ("model",  f"{ORG}/marama-route",       r"S:\hf-publish\marama-route",         []),
    ("space",  f"{ORG}/sovereigncode-demo", r"S:\hf-publish\space-sovereigncode",  []),
    ("space",  f"{ORG}/marama-route-demo",  r"S:\hf-publish\space-marama-route",   []),
]


def push_new(repo_type: str, repo_id: str, local_dir: str) -> None:
    print(f"\n=== {repo_type} {repo_id} ===")
    space_sdk = "gradio" if repo_type == "space" else None
    api.create_repo(repo_id=repo_id, repo_type=repo_type, private=False, exist_ok=True, space_sdk=space_sdk, token=TOKEN)
    print("  repo ensured.")
    api.upload_folder(
        folder_path=local_dir,
        repo_id=repo_id,
        repo_type=repo_type,
        token=TOKEN,
        commit_message="feat: publication-ready scaffold (AbteeX/LumynaX unified surface)",
        ignore_patterns=["__pycache__/*", "*.pyc", "*.bak", "fetch_and_patch.py"],
    )
    print("  uploaded.")


def patch_live_demo() -> None:
    print(f"\n=== space {ORG}/lumynax-live-demo (patch) ===")
    for fn in ("app.py", "README.md"):
        local = Path(r"S:\hf-publish\space-live-demo") / fn
        api.upload_file(
            path_or_fileobj=str(local),
            path_in_repo=fn,
            repo_id=f"{ORG}/lumynax-live-demo",
            repo_type="space",
            token=TOKEN,
            commit_message=f"polish: {fn} (sister-product cross-links, brand footer, new examples)",
        )
        print(f"  pushed {fn}")


if __name__ == "__main__":
    for rt, rid, ld, _ in PUSHES:
        push_new(rt, rid, ld)
    patch_live_demo()
    print("\n=== ALL DONE ===")
    print("Model repos:")
    print(f"  https://huggingface.co/{ORG}/sovereigncode")
    print(f"  https://huggingface.co/{ORG}/marama-route")
    print("Spaces:")
    print(f"  https://huggingface.co/spaces/{ORG}/sovereigncode-demo")
    print(f"  https://huggingface.co/spaces/{ORG}/marama-route-demo")
    print(f"  https://huggingface.co/spaces/{ORG}/lumynax-live-demo (patched)")
