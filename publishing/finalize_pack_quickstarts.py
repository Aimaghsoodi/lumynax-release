"""
Refresh quickstart.py for the 24 Pack A/C/B repos so they load LOCAL
mirrored weights (no upstream call needed).
"""
import os, sys
sys.path.insert(0, r"S:\hf-publish")
from huggingface_hub import HfApi
from finalize_new_quickstarts import render as _render

api = HfApi(token=os.environ["HF_TOKEN"])
TOKEN = os.environ["HF_TOKEN"]

# (repo_id, primary_filename, mmproj_or_None, kind)
NEW_REPOS = {
    # Pack A
    "AbteeXAILab/lumynax-speech-whisper-large-v3-turbo":      ("model.safetensors",                                            None, "safetensors_vision"),
    "AbteeXAILab/lumynax-speech-kokoro-82m-tts":              ("kokoro-v1_0.pth",                                              None, "safetensors_vision"),
    "AbteeXAILab/lumynax-reranker-bge-v2-m3":                 ("model.safetensors",                                            None, "safetensors_vision"),
    "AbteeXAILab/lumynax-guard-text-moderation":              ("model.safetensors",                                            None, "safetensors_vision"),
    "AbteeXAILab/lumynax-math-qwen25-math-7b-gguf":           ("Qwen2.5-Math-7B-Instruct-Q4_K_M.gguf",                         None, "gguf_single"),
    "AbteeXAILab/lumynax-translate-nllb-200-3b":              ("pytorch_model-00001-of-00003.bin",                             None, "safetensors_vision"),
    "AbteeXAILab/lumynax-coder-deepseek-v2-lite-16b-gguf":    ("DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf",                  None, "gguf_single"),
    "AbteeXAILab/lumynax-chat-hermes-3-llama31-8b-gguf":      ("Hermes-3-Llama-3.1-8B-Q4_K_M.gguf",                            None, "gguf_single"),
    # Pack C
    "AbteeXAILab/lumynax-doc-nougat-base":                    ("model.safetensors",                                            None, "safetensors_vision"),
    "AbteeXAILab/lumynax-doc-donut-base":                     ("model.safetensors",                                            None, "safetensors_vision"),
    "AbteeXAILab/lumynax-ocr-trocr-large-printed":            ("model.safetensors",                                            None, "safetensors_vision"),
    "AbteeXAILab/lumynax-ocr-trocr-large-handwritten":        ("model.safetensors",                                            None, "safetensors_vision"),
    "AbteeXAILab/lumynax-doc-layoutlmv3-base":                ("model.safetensors",                                            None, "safetensors_vision"),
    "AbteeXAILab/lumynax-doc-table-transformer-detection":    ("model.safetensors",                                            None, "safetensors_vision"),
    "AbteeXAILab/lumynax-embed-nomic-v2-moe":                 ("model.safetensors",                                            None, "safetensors_vision"),
    "AbteeXAILab/lumynax-embed-granite-278m-multilingual":    ("model.safetensors",                                            None, "safetensors_vision"),
    # Pack B
    "AbteeXAILab/lumynax-frontier-qwen25-72b-instruct-gguf":  ("Qwen2.5-72B-Instruct-Q4_K_M.gguf",                             None, "gguf_single"),
    "AbteeXAILab/lumynax-frontier-olmo2-32b-instruct":        ("model.safetensors.index.json",                                 None, "safetensors_vision"),
    "AbteeXAILab/lumynax-chat-yi-15-34b-gguf":                ("Yi-1.5-34B-Chat-Q4_K_M.gguf",                                  None, "gguf_single"),
    "AbteeXAILab/lumynax-reasoning-internlm3-8b-gguf":        ("internlm3-8b-instruct-Q4_K_M.gguf",                            None, "gguf_single"),
    "AbteeXAILab/lumynax-multimodal-aria-25b-moe":            ("model.safetensors.index.json",                                 None, "safetensors_vision"),
    "AbteeXAILab/lumynax-multimodal-llava-next-34b":          ("model.safetensors.index.json",                                 None, "safetensors_vision"),
    "AbteeXAILab/lumynax-reasoning-qwq-32b-gguf":             ("qwq-32b-q4_k_m.gguf",                                          None, "gguf_single"),
    "AbteeXAILab/lumynax-frontier-phi-4-14b-gguf":            ("phi-4-Q4_K_M.gguf",                                            None, "gguf_single"),
}

def main():
    for repo, info in NEW_REPOS.items():
        print(f"=== {repo}")
        try:
            content = _render(repo, info)
            api.upload_file(
                path_or_fileobj=content.encode("utf-8"),
                path_in_repo="quickstart.py",
                repo_id=repo, repo_type="model", token=TOKEN,
                commit_message="docs(quickstart): load mirrored local weights (no upstream fetch)",
            )
            print("  pushed local-load quickstart.py")
        except Exception as e:
            print(f"  FAIL: {e}")

if __name__ == "__main__":
    main()
