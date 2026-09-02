# LumynaX Release Archive

> **Legacy model collection · Outdated research artifacts**

This repository preserves the public packaging source, manifests, runtime scaffolds, and reproducibility assets for early LumynaX model experiments. The model packs under [`models/`](models/) are no longer maintained, are not recommended for production, and do not represent the current capabilities, architecture, or safety standards of AbteeX AI Labs.

## How infusion works

**LumynaX Core is the core intelligence model.** It governs the inference path and integrates selected open-source models as specialised execution layers.

```text
Prompt  →  LumynaX Core  →  Infused model / MoE experts  →  LumynaX Core  →  Response
```

**LumynaX infusion** is the controlled composition of LumynaX Core with a compatible open-source model:

- **Routed infusion** directs inference through the selected model without modifying its weights.
- **MoE infusion** can compose compatible model weights as specialised experts when required by the architecture.

LumynaX Core remains the primary intelligence and orchestration layer in either configuration, applying sovereignty controls, context, agentic planning, and inference optimisation around execution. Infusion does not automatically imply a weight merge; each release manifest records the method used by its pack.

## Archive scope

| | |
|---|---|
| **Model packs** | 98 historical releases |
| **Infused packs** | 96 routed model integrations |
| **Native models** | 2 early LumynaX-native releases |
| **Status** | Outdated and retained for research provenance only |

- [`models/`](models/) contains the archived model packages.
- [`registry/`](registry/) contains historical registry metadata.
- [`deployments/`](deployments/) and [`spaces/`](spaces/) contain experimental deployment scaffolds.
- [Hugging Face](https://huggingface.co/AbteeXAILab) hosts the corresponding model artifacts.

The repository also contains experimental routing and sovereign-computing utilities. Their presence does not imply production readiness; review each package's own status and licence before use.

## Provenance

Treat each pack's `release_export_manifest.json`, `checksums.sha256`, and `LICENSE.txt` as authoritative. Source-model weights remain subject to their original licences.

- [AbteeX AI Labs](https://abteex.com)
- [LumynaX](https://lumynax.com)
- [Contact](mailto:aimaghsoodi@abteex.com)

---

**AbteeX AI Labs · Aotearoa New Zealand**
