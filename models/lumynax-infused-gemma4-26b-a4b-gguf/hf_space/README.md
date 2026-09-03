---
title: LumynaX Infused Gemma4 26B A4B GGUF Demo
colorFrom: green
colorTo: blue
sdk: gradio
app_file: app.py
pinned: false
short_description: Legacy LumynaX demo. Outdated; not for production.
tags:
- legacy
- outdated
---

# LumynaX Infused Gemma4 26B A4B GGUF · Legacy demo

> **Outdated research interface · Not for production**

This Space scaffold belongs to [`AbteeXAILab/lumynax-infused-gemma4-26b-a4b-gguf`](https://huggingface.co/AbteeXAILab/lumynax-infused-gemma4-26b-a4b-gguf). It is no longer maintained and does not represent the current LumynaX Core experience.

## How infusion works

**LumynaX Core is the core intelligence model.** It governs the inference path and integrates selected open-source models as specialised execution layers.

```text
Prompt  →  LumynaX Core  →  Infused model / MoE experts  →  LumynaX Core  →  Response
```

**LumynaX infusion** is the controlled composition of LumynaX Core with a compatible open-source model. Depending on the model family and deployment objective, the integration can operate in two ways:

- **Routed infusion** — LumynaX Core directs inference through the selected model without modifying its weights.
- **MoE infusion** — when required by the architecture, compatible model weights can be composed as specialised experts within a Mixture-of-Experts design.

In both cases, LumynaX Core remains the primary intelligence and orchestration layer, applying sovereignty controls, context, agentic planning, and inference optimisation around model execution. Infusion does not automatically imply a weight merge; each release manifest records the method used by that pack.

This interface exposes only the historical package runtime. Consult the model pack's `release_export_manifest.json` for its recorded infusion method, weights, runtime, and provenance.

- [Model artifacts](https://huggingface.co/AbteeXAILab/lumynax-infused-gemma4-26b-a4b-gguf)
- [AbteeX AI Labs](https://abteex.com)
- [Contact](mailto:aimaghsoodi@abteex.com)
