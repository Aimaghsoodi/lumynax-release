# LumynaX Infused Mistral 7B Instruct v0.3 GGUF

> **Legacy release · Outdated research artifact**

This repository documents an early LumynaX experiment. It is no longer maintained, is not recommended for production, and does not represent the current capabilities, architecture, or safety standards of AbteeX AI Labs.

## How infusion works

**LumynaX Core is the core intelligence model.** It governs the inference path and integrates selected open-source models as specialised execution layers.

```text
Prompt  →  LumynaX Core  →  Infused model / MoE experts  →  LumynaX Core  →  Response
```

**LumynaX infusion** is the controlled composition of LumynaX Core with a compatible open-source model. Depending on the model family and deployment objective, the integration can operate in two ways:

- **Routed infusion** — LumynaX Core directs inference through the selected model without modifying its weights.
- **MoE infusion** — when required by the architecture, compatible model weights can be composed as specialised experts within a Mixture-of-Experts design.

In both cases, LumynaX Core remains the primary intelligence and orchestration layer, applying sovereignty controls, context, agentic planning, and inference optimisation around model execution. Infusion does not automatically imply a weight merge; each release manifest records the method used by that pack.

## This release

| | |
|---|---|
| **Infused model** | [`mistralai/Mistral-7B-Instruct-v0.3`](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3) |
| **Infusion method** | Routed runtime and identity integration |
| **Weight composition** | None — this pack preserves the source-model weights |
| **Runtime** | llama.cpp |
| **Release** | v1 |
| **Status** | Outdated and retained for research provenance only |

This package predates the current LumynaX Core implementation. Its included identity, runtime, or deployment wrappers are historical release components—not the complete modern LumynaX pipeline.

## Archive access

The code and artifacts remain available for reproducibility. Before evaluation, verify [`checksums.sha256`](checksums.sha256), inspect [`release_export_manifest.json`](release_export_manifest.json), and review [`LICENSE.txt`](LICENSE.txt).

- [Model card and artifacts on Hugging Face](https://huggingface.co/AbteeXAILab/lumynax-infused-mistral-7b-v03-gguf)
- [AbteeX AI Labs](https://abteex.com)
- [LumynaX](https://lumynax.com)
- [Contact](mailto:aimaghsoodi@abteex.com)

---

**AbteeX AI Labs · Aotearoa New Zealand**
