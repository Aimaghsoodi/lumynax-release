"""Verify Pack C (Document & Retrieval stack) upstreams non-gated + sizes."""
import os
from huggingface_hub import HfApi
api = HfApi(token=os.environ["HF_TOKEN"])

CANDS = [
    ("facebook/nougat-base", "academic doc OCR"),
    ("naver-clova-ix/donut-base", "doc understanding"),
    ("microsoft/trocr-large-printed", "printed OCR"),
    ("microsoft/trocr-large-handwritten", "handwritten OCR"),
    ("microsoft/layoutlmv3-base", "doc layout+text"),
    ("microsoft/table-transformer-detection", "table detection"),
    ("nomic-ai/nomic-embed-text-v2-moe", "modern embed MoE"),
    ("ibm-granite/granite-embedding-278m-multilingual", "multilingual embed"),
]
for r, note in CANDS:
    try:
        info = api.repo_info(r, files_metadata=True)
        sz = sum(s.size or 0 for s in info.siblings if s.rfilename.lower().endswith((".safetensors",".bin",".pt",".onnx")))
        gated = getattr(info, "gated", False)
        print(f"{r:<60} gated={str(gated):<8} {sz/1e6:>6.0f} MB  {note}")
    except Exception as e:
        print(f"{r:<60} ERR {str(e)[:60]}")
