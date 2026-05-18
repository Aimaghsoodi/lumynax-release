# Upload checklist (AbteeX AI Labs)

This scaffold was generated and pushed by `S:\hf-publish\add_8_more_models.py`.
The repo is structured to be cloned whole and verified locally before running.

```bash
hf download AbteeXAILab/lumynax-longctx-qwen25-7b-1m-gguf --local-dir lumynax-longctx-qwen25-7b-1m-gguf
cd lumynax-longctx-qwen25-7b-1m-gguf
pip install -r requirements.txt
python quickstart.py --interactive
```

To regenerate or refresh, re-run the script — `huggingface_hub.HfApi.upload_folder`
is idempotent.
