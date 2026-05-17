# Upload LumynaX Infused Zephyr 7B Beta GGUF

Upload the whole release folder, not just the GGUF file.

Private first:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\publish_huggingface_release.ps1 -ReleaseDir .\data\releases\lumynax-infused-zephyr-7b-beta-gguf-v1 -RepoId AbteeXAILab/lumynax-infused-zephyr-7b-beta-gguf -Private
```

Public release:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\publish_huggingface_release.ps1 -ReleaseDir .\data\releases\lumynax-infused-zephyr-7b-beta-gguf-v1 -RepoId AbteeXAILab/lumynax-infused-zephyr-7b-beta-gguf -Public
```

The folder includes `README.md`, `LICENSE.txt`, `.gitattributes`, `checksums.sha256`,
`release_export_manifest.json`, the GGUF file, Ollama files, and the Space bundle.
