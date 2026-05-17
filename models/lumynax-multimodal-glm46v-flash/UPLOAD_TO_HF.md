# Upload LumynaX Multimodal GLM 4.6V Flash

Upload the whole release folder, not just the GGUF file.

Private first:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\publish_huggingface_release.ps1 -ReleaseDir .\data\releases\lumynax-multimodal-glm46v-flash-v1 -RepoId AbteeXAILab/lumynax-multimodal-glm46v-flash -Private
```

Public release:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\publish_huggingface_release.ps1 -ReleaseDir .\data\releases\lumynax-multimodal-glm46v-flash-v1 -RepoId AbteeXAILab/lumynax-multimodal-glm46v-flash -Public
```

The folder includes `README.md`, `LICENSE.txt`, `.gitattributes`, `checksums.sha256`,
`release_export_manifest.json`, the GGUF file, Ollama files, and the Space bundle.
