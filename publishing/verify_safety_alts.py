from huggingface_hub import HfApi
import os
api = HfApi(token=os.environ["HF_TOKEN"])
for r in ["KoalaAI/Text-Moderation","protectai/deberta-v3-base-prompt-injection-v2","MoritzLaurer/deberta-v3-large-zeroshot-v2.0"]:
    try:
        info = api.repo_info(r, files_metadata=True)
        sz = sum(s.size or 0 for s in info.siblings if s.rfilename.lower().endswith((".safetensors",".bin")))
        gated = getattr(info, "gated", None)
        print(f"{r}: gated={gated}, size={sz/1e6:.0f} MB")
    except Exception as e:
        print(f"{r}: ERR {e}")
