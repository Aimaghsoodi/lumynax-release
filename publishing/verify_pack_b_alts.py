"""Find non-gated substitutes for Pack B."""
import os
from huggingface_hub import HfApi
api = HfApi(token=os.environ["HF_TOKEN"])

ALTS = [
    ("allenai/OLMo-2-1124-13B-Instruct", "13B OLMo fully-open"),
    ("allenai/OLMo-2-1124-7B-Instruct",  "7B OLMo fully-open"),
    ("allenai/OLMo-2-0325-32B-Instruct", "32B OLMo (newer date)"),
    ("Qwen/Qwen2.5-VL-32B-Instruct",     "Qwen vision 32B"),
    ("mistralai/Mistral-Nemo-Instruct-2407","Mistral Nemo 12B"),
    ("Salesforce/blip2-flan-t5-xxl",     "BLIP-2 multimodal"),
    ("liuhaotian/llava-v1.6-34b",        "LLaVA-Next 34B"),
    ("HuggingFaceM4/Idefics3-8B-Llama3", "Idefics3 multimodal"),
    ("Salesforce/Llama-xLAM-2-8b-fc-r",  "xLAM tool-call agent"),
    ("microsoft/phi-4",                  "Phi-4 14B"),
    ("ibm-granite/granite-3.1-8b-instruct","IBM Granite 3.1 8B"),
    ("Qwen/QwQ-32B",                     "QwQ 32B reasoning"),
    ("Qwen/QwQ-32B-Preview",             "QwQ-32B-Preview reasoning"),
]
for r, note in ALTS:
    try:
        info = api.repo_info(r, files_metadata=True)
        sz = sum(s.size or 0 for s in info.siblings if s.rfilename.lower().endswith((".safetensors",".bin")))
        gated = getattr(info, "gated", False)
        print(f"{r:<50} gated={str(gated):<8} {sz/1e9:>5.1f} GB  {note}")
    except Exception as e:
        print(f"{r:<50} ERR")
