# Upload LumynaX Infused OLMo 2 0425 1B Instruct GGUF

Upload the whole release folder, not just the GGUF file.

Private first:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\publish_huggingface_release.ps1 -ReleaseDir .\data\releases\lumynax-infused-olmo2-1b-0425-gguf-v1 -RepoId AbteeXAILab/lumynax-infused-olmo2-1b-0425-gguf -Private
```

Public release:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\publish_huggingface_release.ps1 -ReleaseDir .\data\releases\lumynax-infused-olmo2-1b-0425-gguf-v1 -RepoId AbteeXAILab/lumynax-infused-olmo2-1b-0425-gguf -Public
```

The folder includes `README.md`, `LICENSE.txt`, `.gitattributes`, `checksums.sha256`,
`release_export_manifest.json`, the GGUF file, Ollama files, and the Space bundle.
