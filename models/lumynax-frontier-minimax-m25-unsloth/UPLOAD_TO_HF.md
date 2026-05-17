# Upload LumynaX Frontier MiniMax M2.5 Unsloth

Upload the whole release folder, not just the GGUF file.

Private first:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\publish_huggingface_release.ps1 -ReleaseDir .\data\releases\tinyluminax-minimax-m25-release -RepoId AbteeXAILab/lumynax-frontier-minimax-m25-unsloth -Private
```

Public release:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\publish_huggingface_release.ps1 -ReleaseDir .\data\releases\tinyluminax-minimax-m25-release -RepoId AbteeXAILab/lumynax-frontier-minimax-m25-unsloth -Public
```

The folder includes `README.md`, `LICENSE.txt`, `.gitattributes`, `checksums.sha256`,
`release_export_manifest.json`, the GGUF file, Ollama files, and the Space bundle.
