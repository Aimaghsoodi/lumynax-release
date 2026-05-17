"""Push the three Spaces (model repos already pushed)."""
import os
from pathlib import Path
from huggingface_hub import HfApi

TOKEN = os.environ["HF_TOKEN"]
api = HfApi(token=TOKEN)
ORG = "AbteeXAILab"

SPACES = [
    (f"{ORG}/sovereigncode-demo", r"S:\hf-publish\space-sovereigncode"),
    (f"{ORG}/marama-route-demo",  r"S:\hf-publish\space-marama-route"),
]

for repo_id, local_dir in SPACES:
    print(f"\n=== space {repo_id} ===")
    api.create_repo(repo_id=repo_id, repo_type="space", private=False, exist_ok=True, space_sdk="gradio", token=TOKEN)
    api.upload_folder(
        folder_path=local_dir,
        repo_id=repo_id,
        repo_type="space",
        token=TOKEN,
        commit_message="feat: publication-ready Space (AbteeX/LumynaX unified surface)",
        ignore_patterns=["__pycache__/*", "*.pyc", "*.bak", "fetch_and_patch.py"],
    )
    print("  uploaded.")

print("\n=== patch live demo ===")
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

print("\n=== ALL DONE ===")
