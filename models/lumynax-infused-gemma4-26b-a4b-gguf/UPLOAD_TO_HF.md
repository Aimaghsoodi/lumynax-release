# Upload LumynaX Infused Gemma4 26B A4B GGUF

Upload the whole release folder, not just the GGUF file.

Private first:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\publish_huggingface_release.ps1 -ReleaseDir .\data\releases\lumynax-infused-gemma4-26b-a4b-gguf-v1 -RepoId AbteeXAILab/lumynax-infused-gemma4-26b-a4b-gguf -Private
```

Public release:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\publish_huggingface_release.ps1 -ReleaseDir .\data\releases\lumynax-infused-gemma4-26b-a4b-gguf-v1 -RepoId AbteeXAILab/lumynax-infused-gemma4-26b-a4b-gguf -Public
```

The folder includes `README.md`, `LICENSE.txt`, `.gitattributes`, `checksums.sha256`,
`release_export_manifest.json`, the GGUF file, Ollama files, and the Space bundle.
