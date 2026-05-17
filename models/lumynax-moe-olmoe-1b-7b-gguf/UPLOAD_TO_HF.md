# Upload LumynaX MoE OLMoE 1B-7B Instruct GGUF

Upload the whole release folder, not just the GGUF file.

Private first:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\publish_huggingface_release.ps1 -ReleaseDir .\data\releases\lumynax-moe-olmoe-1b-7b-gguf-v1 -RepoId AbteeXAILab/lumynax-moe-olmoe-1b-7b-gguf -Private
```

Public release:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\publish_huggingface_release.ps1 -ReleaseDir .\data\releases\lumynax-moe-olmoe-1b-7b-gguf-v1 -RepoId AbteeXAILab/lumynax-moe-olmoe-1b-7b-gguf -Public
```

The folder includes `README.md`, `LICENSE.txt`, `.gitattributes`, `checksums.sha256`,
`release_export_manifest.json`, the GGUF file, Ollama files, and the Space bundle.
