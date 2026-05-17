# Upload LumynaX Infused Phi-3 Mini 4K Instruct GGUF

Upload the whole release folder, not just the GGUF file.

Private first:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\publish_huggingface_release.ps1 -ReleaseDir .\data\releases\lumynax-infused-phi3-mini-4k-gguf-v1 -RepoId AbteeXAILab/lumynax-infused-phi3-mini-4k-gguf -Private
```

Public release:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\publish_huggingface_release.ps1 -ReleaseDir .\data\releases\lumynax-infused-phi3-mini-4k-gguf-v1 -RepoId AbteeXAILab/lumynax-infused-phi3-mini-4k-gguf -Public
```

The folder includes `README.md`, `LICENSE.txt`, `.gitattributes`, `checksums.sha256`,
`release_export_manifest.json`, the GGUF file, Ollama files, and the Space bundle.
