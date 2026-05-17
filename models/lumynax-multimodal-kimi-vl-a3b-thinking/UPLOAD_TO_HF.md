# Upload LumynaX Multimodal Kimi VL A3B Thinking

Upload the whole release folder, not just the GGUF file.

Private first:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\publish_huggingface_release.ps1 -ReleaseDir .\data\releases\lumynax-multimodal-kimi-vl-a3b-thinking-v1 -RepoId AbteeXAILab/lumynax-multimodal-kimi-vl-a3b-thinking -Private
```

Public release:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\publish_huggingface_release.ps1 -ReleaseDir .\data\releases\lumynax-multimodal-kimi-vl-a3b-thinking-v1 -RepoId AbteeXAILab/lumynax-multimodal-kimi-vl-a3b-thinking -Public
```

The folder includes `README.md`, `LICENSE.txt`, `.gitattributes`, `checksums.sha256`,
`release_export_manifest.json`, the GGUF file, Ollama files, and the Space bundle.
