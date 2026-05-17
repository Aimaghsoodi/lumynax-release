---
license: apache-2.0
library_name: custom
tags:
- abteex-ai-labs
- lumynax
- sovereigncode
- data-capsule
- coding-agent
- governance
- new-zealand
- aotearoa
- sovereign-ai
- local-first
language:
- en
- mi
---

# AbteeX SovereignCode

<!-- abteex-sovereigncode-card:v1 -->

<p align="center"><em>Sovereign intelligence, held in the light.</em></p>
<p align="center"><em>Ko te mārama te tūāpapa &mdash; the light is the foundation.</em></p>

<p align="center">
  <strong>A local-first coding agent with Data Capsule sovereignty controls.</strong><br/>
  AbteeX AI Labs &mdash; Aotearoa New Zealand.
</p>

<p align="center">
  <a href="#what-it-is">What it is</a> &middot;
  <a href="#quickstart">Quickstart</a> &middot;
  <a href="#data-capsule">Data Capsule</a> &middot;
  <a href="#policy-decision-point">Policy decision point</a> &middot;
  <a href="#audit-ledger">Audit ledger</a> &middot;
  <a href="#roadmap">Roadmap</a> &middot;
  <a href="#companion-products">Companions</a>
</p>

![SovereignCode](https://img.shields.io/badge/AbteeX-SovereignCode-e08a2c?style=for-the-badge) ![Stage scaffold](https://img.shields.io/badge/stage-product%20scaffold-0a0a0b?style=for-the-badge) ![Runtime python](https://img.shields.io/badge/runtime-python%203.11%2B-726b62?style=for-the-badge) ![License Apache 2.0](https://img.shields.io/badge/license-Apache--2.0-9a5416?style=for-the-badge) ![Card v1](https://img.shields.io/badge/card-v1-111827?style=for-the-badge)

## What It Is

**AbteeX SovereignCode** is the AbteeX AI Labs coding-agent product built on the LumynaX release family. It is conceptually close to an OpenCode-style terminal coding assistant, but the centre of gravity is *AI sovereignty*: every model call, tool call, file edit, and outbound action is evaluated against a **Data Capsule** policy before execution.

It is for organisations that want local-first coding assistance without losing control over source code, regulated records, Iwi or community-held data, health data, procurement records, or other sensitive operational context.

## Five Commitments

| Commitment | Product Meaning |
| --- | --- |
| Data capsules | Every workspace, dataset, or customer context can carry machine-readable purpose, residency, retention, export, and training controls. |
| Policy before tools | Shell commands, file writes, network calls, commits, and model calls are checked **before** execution. |
| Local-first inference | High-impact or restricted data routes to local or LumynaX-governed models by default. |
| Human review | External effects require explicit approval, visible diffs, and audit records. |
| Provenance | Model identity, source files, policy decisions, prompts, outputs, and release metadata remain traceable. |

## Why This Is Different

Most coding agents optimise for speed. SovereignCode optimises for **controlled autonomy**: it can still plan, edit, test, and explain code, but it treats data rights, residency, consent, provenance, and human approval as *runtime primitives* &mdash; not policy text on a wiki.

## Quickstart

Clone and install:

```bash
hf download AbteeXAILab/sovereigncode --local-dir sovereigncode --repo-type model
cd sovereigncode
pip install -r requirements.txt
```

Evaluate an **allowed** local-edit request against the example capsule:

```bash
python -m sovereigncode.cli evaluate \
  --capsule examples/capsule.restricted-nz-code.json \
  --request examples/request.allowed-local-edit.json
```

Expected: `allowed: true` with obligations including `write_immutable_audit_record`, `preserve_capsule_id_in_agent_trace`, and `show_diff_before_write_or_commit`.

Evaluate a **denied** training request:

```bash
python -m sovereigncode.cli evaluate \
  --capsule examples/capsule.restricted-nz-code.json \
  --request examples/request.denied-training.json \
  --allow-denied-exit-zero
```

Expected: `allowed: false` with reason `capsule.training_allowed = false`.

## Data Capsule

A Data Capsule is the policy envelope attached to a workspace, dataset, tenant, case, source-file set, or prompt context.

```json
{
  "capsule_id": "cap-nz-code-001",
  "subject_id": "abx-workspace",
  "jurisdiction": "NZ",
  "sensitivity": "restricted",
  "allowed_purposes": ["coding_assistance", "inference", "test_generation"],
  "denied_purposes": ["ad_training", "third_party_resale"],
  "resident_regions": ["NZ"],
  "data_classes": ["source_code", "policy", "runtime_logs"],
  "retention_days": 14,
  "export_allowed": false,
  "training_allowed": false
}
```

Capsules carry:

- `allowed_purposes` / `denied_purposes`
- `resident_regions`
- `retention_days`
- `training_allowed` / `export_allowed`
- `data_classes`
- `schema_context`
- `consent_record`

## Policy Decision Point

The PDP answers one question before every sensitive action:

> *Can this actor, for this purpose, in this region, using this model/tool, touch this capsule?*

Decisions are one of: `allow`, `deny`, or `allow_with_obligations`. Every decision produces a structured record:

| Field | Meaning |
| --- | --- |
| `capsule_id` | The capsule the action touches. |
| `actor` | Who initiated the action. |
| `purpose` | Declared purpose (e.g. `coding_assistance`). |
| `action` | The tool action requested. |
| `model_id` | Resolved model identity (often via [MaramaRoute](https://huggingface.co/AbteeXAILab/marama-route)). |
| `decision` | `allow` / `deny` / `allow_with_obligations`. |
| `reasons` | Ordered list of policy reasons. |
| `obligations` | Required follow-up actions. |
| `request_hash` | Stable SHA-256 of the canonical request. |
| `timestamp` | ISO 8601 UTC. |

## Tool Broker

The broker is the enforcement layer for shell commands, file writes, git commits, network calls, package installs, model calls, retrieval queries, and training jobs. Every tool call passes through the PDP first.

## Audit Ledger

Every decision creates an immutable audit record. Records are append-only and hash-chained &mdash; usable as evidence for regulators, customers, and internal review.

## Sovereignty & Run Contract

| Field | Value |
| --- | --- |
| Publisher | AbteeX AI Labs |
| Family | LumynaX sovereign products |
| Sovereign intent | Local-first coding assistance with policy-before-tools enforcement. |
| Runtime residency | Operator's environment; restricted data routes to local or LumynaX-governed models. |
| License | Apache-2.0 |
| Stage | Product scaffold &mdash; PDP and audit engine executable; full terminal loop in P1. |
| Router integration | First-class with [LumynaX MaramaRoute](https://huggingface.co/AbteeXAILab/marama-route). |

## Roadmap

| Milestone | Outcome |
| --- | --- |
| **P0 scaffold** *(now)* | Policy engine, audit records, CLI, examples, docs. |
| **P1 terminal loop** | Local terminal agent with plan / edit / test workflow. |
| **P2 tool broker** | Policy wrappers for shell, git, file writes, package installs, HTTP. |
| **P3 MaramaRoute integration** | Sovereign model routing for every model call. |
| **P4 workspace UI** | Browser console showing plan, policy, diffs, tests, approvals. |
| **P5 enterprise controls** | Tenant policies, SSO hooks, signed audit exports, policy packs. |

## Source Grounding

The sovereignty model is inspired by the Data Capsule pattern described in the ScienceDirect article identified by PII `S2543925125000166` &mdash; especially its emphasis on semantic metadata, ontology-based federation, and dynamic usage-control policies. This repository uses that idea as product architecture inspiration; it does not copy the paper text or implementation.

## Companion Products

| Product | Purpose |
| --- | --- |
| [LumynaX MaramaRoute](https://huggingface.co/AbteeXAILab/marama-route) | Sovereign model router across the LumynaX release family. SovereignCode delegates model selection to MaramaRoute. |
| [LumynaX Live Demo](https://huggingface.co/spaces/AbteeXAILab/lumynax-live-demo) | Public browser demo of a LumynaX-infused GGUF release. |
| [SovereignCode Live](https://huggingface.co/spaces/AbteeXAILab/sovereigncode-demo) | Interactive policy evaluator &mdash; paste a capsule and request, see the decision. |
| [AbteeXAILab on Hugging Face](https://huggingface.co/AbteeXAILab) | The full LumynaX release family. |

## Aotearoa Kaupapa

SovereignCode is built in and for Aotearoa New Zealand. Iwi data sovereignty, health-information governance, and procurement transparency are not retro-fits &mdash; they are the runtime contract. The product treats data rights, residency, consent, provenance, and human approval as primitives.

## Limitations & Responsible Use

- The PDP enforces declared policy. It does not detect every possible deceptive prompt or covert exfiltration channel.
- The current release is a *product scaffold*. Full terminal loop, tool broker, and workspace UI ship in P1–P4.
- For high-impact decisions, use human review and domain-specific evaluation.
- Audit records help, but auditability is a process &mdash; not a guarantee.

---

<p align="center"><em>Local roots, global work. &middot; Sovereignty is a design property, not a deployment option.</em></p>
<p align="center"><sub>AbteeX AI Labs &middot; <a href="https://abteex.com">abteex.com</a> &middot; <a href="https://lumynax.com">lumynax.com</a> &middot; <a href="https://huggingface.co/AbteeXAILab">huggingface.co/AbteeXAILab</a></sub></p>
