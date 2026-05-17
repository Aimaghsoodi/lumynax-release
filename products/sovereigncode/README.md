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
- opencode
language:
- en
- mi
---

# AbteeX SovereignCode
<!-- abteex-sovereigncode-card:v3 -->

Standalone release package for `AbteeXAILab/sovereigncode`.

## Install

```bash
hf download AbteeXAILab/sovereigncode --local-dir sovereigncode --repo-type model
cd sovereigncode
pip install -e .
python quickstart.py
```

## Included Runtime Commands

```bash
python -m sovereigncode.cli evaluate --capsule examples/capsule.restricted-nz-code.json --request examples/request.allowed-local-edit.json
python -m sovereigncode.cli plan-turn --capsule examples/capsule.restricted-nz-code.json --request examples/request.allowed-local-edit.json --route-request examples/request.code-restricted.json --registry configs/lumynax_model_registry.json
python -m sovereigncode.cli policy-matrix --capsule examples/capsule.restricted-nz-code.json --request examples/request.allowed-local-edit.json
python -m sovereigncode.cli tool-check --capsule examples/capsule.restricted-nz-code.json --request examples/request.allowed-local-edit.json --tool-name workspace_reader --action read_context
python -m sovereigncode.cli opencode-config
python -m sovereigncode.cli ui --smoke
python -m sovereigncode.cli serve --smoke
python -m sovereigncode.cli audit --limit 5
python -m sovereigncode.cli ui --port 8788 --open
python -m sovereigncode.cli serve --port 8788 --open
```

# AbteeX SovereignCode

AbteeX SovereignCode is the proposed AbteeX AI Labs coding-agent product built on LumynaX. It is conceptually close to an OpenCode-style terminal coding assistant, but the centre of gravity is AI sovereignty: every model call, tool call, file edit, and outbound action is evaluated against a Data Capsule policy before execution.

## Product Position

SovereignCode is for organisations that want local-first coding assistance without losing control over source code, regulated records, Iwi or community-held data, health data, procurement records, or other sensitive operational context.

The product is designed around five commitments:

| Commitment | Product Meaning |
| --- | --- |
| Data capsules | Every workspace, dataset, or customer context can carry machine-readable purpose, residency, retention, export, and training controls. |
| Policy before tools | Shell commands, file writes, network calls, commits, and model calls are checked before execution. |
| Local-first inference | High-impact or restricted data routes to local or LumynaX-governed models by default. |
| Human review | External effects require explicit approval, visible diffs, and audit records. |
| Provenance | Model identity, source files, policy decisions, prompts, outputs, and release metadata remain traceable. |

## Why This Is Different

Most coding agents optimise for speed. SovereignCode optimises for controlled autonomy: it can still plan, edit, test, and explain code, but it treats data rights, residency, consent, provenance, and human approval as runtime primitives instead of policy text on a wiki.

The initial product scaffold includes:

- A deterministic Data Capsule policy decision point.
- Personal-detail consent checks for anonymous, pseudonymous, identifiable, and sensitive identifiable contexts.
- A CLI evaluator for governed code/data requests.
- A governed coding-turn planner that combines policy, audit, tool grants, and MaramaRoute model selection.
- A dependency-free browser operator console for policy evaluation and coding-turn planning.
- Audit-record generation with stable request hashes.
- Product architecture and launch roadmap.
- Example capsules for restricted New Zealand source-code work.
- A path to integrate with LumynaX MaramaRoute for sovereign model selection.

## Quickstart

From the repo root:

```bash
py -3 -m tinyluminax.products.sovereigncode.cli evaluate \
  --capsule products/abx-sovereigncode/examples/capsule.restricted-nz-code.json \
  --request products/abx-sovereigncode/examples/request.allowed-local-edit.json
```

Expected result: `allowed: true` with obligations such as audit logging, local runtime routing, and visible diff review.

Plan a complete governed coding-agent turn:

```bash
py -3 -m tinyluminax.products.sovereigncode.cli plan-turn \
  --capsule products/abx-sovereigncode/examples/capsule.restricted-nz-code.json \
  --request products/abx-sovereigncode/examples/request.allowed-local-edit.json \
  --route-request products/lumynax-marama-route/examples/request.code-restricted.json \
  --registry products/lumynax-marama-route/configs/lumynax_model_registry.json
```

Run the policy/tool matrix:

```bash
py -3 -m tinyluminax.products.sovereigncode.cli policy-matrix \
  --capsule products/abx-sovereigncode/examples/capsule.restricted-nz-code.json \
  --request products/abx-sovereigncode/examples/request.allowed-local-edit.json
```

Check one tool before execution:

```bash
py -3 -m tinyluminax.products.sovereigncode.cli tool-check \
  --capsule products/abx-sovereigncode/examples/capsule.restricted-nz-code.json \
  --request products/abx-sovereigncode/examples/request.allowed-local-edit.json \
  --tool-name workspace_reader \
  --action read_context
```

Emit an OpenCode-compatible workspace config:

```bash
py -3 -m tinyluminax.products.sovereigncode.cli opencode-config
```

Denied training example:

```bash
py -3 -m tinyluminax.products.sovereigncode.cli evaluate \
  --capsule products/abx-sovereigncode/examples/capsule.restricted-nz-code.json \
  --request products/abx-sovereigncode/examples/request.denied-training.json \
  --allow-denied-exit-zero
```

Run the browser operator console:

```bash
py -3 -m tinyluminax.products.sovereigncode.cli ui --port 8788 --open
```

Run the local policy API, persistent audit ledger, and browser console:

```bash
py -3 -m tinyluminax.products.sovereigncode.cli serve --port 8788 --open
```

Smoke-check the service without opening a browser:

```bash
py -3 -m tinyluminax.products.sovereigncode.cli serve --smoke
```

Read the audit ledger:

```bash
py -3 -m tinyluminax.products.sovereigncode.cli audit --limit 10
```

The service exposes `GET /health`, `GET /v1/audit`, `POST /v1/evaluate`, `POST /v1/plan-turn`, `POST /v1/tool-check`, `POST /v1/policy-matrix`, and the existing browser `/api/*` routes. It writes JSONL audit records to `.sovereigncode/audit.jsonl` by default.

Smoke-check the UI routes without opening a browser:

```bash
py -3 -m tinyluminax.products.sovereigncode.cli ui --smoke
```

## Product Modules

| Module | Purpose |
| --- | --- |
| Workspace Indexer | Builds a local map of files, policies, secrets, data classes, and repository ownership. |
| Data Capsule PDP | Decides whether a request is allowed, denied, or allowed with obligations. |
| Tool Broker | Wraps shell, file, git, network, package, and model actions with policy checks. |
| Policy API Service | Serves policy evaluation, turn planning, tool checks, policy matrix, and audit reads over local HTTP. |
| LumynaX Runtime Adapter | Routes model calls to local GGUF, local API, or approved LumynaX model endpoints. |
| Audit Ledger | Stores append-only JSONL decision records, prompt/output hashes, file diffs, and approval metadata. |
| Operator Console | Shows the plan, policy decision, diff, tests, and approval gate before external effects. |
| Policy Matrix | Evaluates common tool/action scenarios against the same Data Capsule. |
| Provider Exporter | Emits OpenCode-compatible workspace config pointing through MaramaRoute. |

## New Zealand Launch Shape

| Layer | Product Decision |
| --- | --- |
| Default region | `NZ` residency, with explicit opt-in for `AU` or global routes. |
| Default data posture | Local-first for restricted, health, personal, Iwi, taonga, and regulated operational context. |
| Buyer control | Tenant policy packs define purpose, retention, model allowlists, exports, and approval rules. |
| Personal sovereignty | Personal data is tagged by detail level and consent scope before it enters prompts or traces. |
| OpenCode compatibility | Configure SovereignCode through MaramaRoute as an OpenAI-compatible provider. |
| Commercial wedge | Start with governed code assistance for New Zealand teams that cannot send private workspaces to a generic cloud coding agent. |

## Real Product Surfaces

| Surface | File |
| --- | --- |
| Data Capsule JSON Schema | `schemas/data_capsule.schema.json` |
| NZ personal sovereignty policy pack | `policy-packs/nz-personal-sovereignty.yaml` |
| OpenCode-compatible integration guide | `integrations/opencode-compatible-provider.md` |
| OpenCode provider example | `examples/opencode.marama-route.json` |
| Personal profile capsule | `examples/capsule.personal-sovereignty-profile.json` |
| Personal-memory request | `examples/request.personal-memory-read.json` |
| Browser operator console | `python -m tinyluminax.products.sovereigncode.cli ui` |
| Local policy API service | `python -m tinyluminax.products.sovereigncode.cli serve` |
| Audit ledger reader | `python -m tinyluminax.products.sovereigncode.cli audit` |
| Policy/tool matrix | `python -m tinyluminax.products.sovereigncode.cli policy-matrix` |
| Tool gate check | `python -m tinyluminax.products.sovereigncode.cli tool-check` |
| OpenCode workspace export | `python -m tinyluminax.products.sovereigncode.cli opencode-config` |
| Product blueprint | `product_blueprint.md` |

## Source Grounding

The sovereignty model is inspired by the Data Capsule pattern described in the ScienceDirect article identified by PII `S2543925125000166`, especially its emphasis on semantic metadata, ontology-based federation, and dynamic usage-control policies. This repository uses that idea as product architecture inspiration; it does not copy the paper text or implementation.

## Stage

This is a local runtime product surface, not the final commercial application. The policy engine, router integration, CLI package, policy matrix, tool gate checks, capsule summaries, OpenCode config export, operator checklist, browser operator console, local policy API, and persistent audit ledger are working now. The full terminal editing loop remains a later layer, but policy, routing, audit, and OpenCode-facing configuration are executable today.


# AbteeX SovereignCode Product Blueprint

## One-Sentence Product

SovereignCode is a local-first coding agent for New Zealand teams that need code
assistance, model routing, personal-data controls, and audit-ready tool use in
one governed workflow.

## Core User Jobs

| User | Job | SovereignCode Response |
| --- | --- | --- |
| Individual developer | Use an AI coding assistant without exposing private files or personal preferences. | Local capsule, pseudonymous personal profile, resident model route, no training by default. |
| Startup or SME | Refactor and test private code while keeping customer data out of generic SaaS logs. | Workspace capsule, local route, diff review, audit hash. |
| Council or public-sector team | Use AI on operational code and documents with retention and residency controls. | Tenant policy pack, NZ residency, approval gates, signed audit export. |
| Iwi or community data steward | Keep community-held context under explicit purpose and consent boundaries. | High-impact sensitivity, local/LumynaX-only model rule, export denial by default. |
| Internal platform owner | Give developers one coding assistant with central policy. | OpenAI-compatible provider, CLI planner, future SSO and policy server. |

## Product Pillars

1. Capsule-first context: every workspace, profile, dataset, and prompt context
   resolves to a Data Capsule before agent work starts.
2. Personal sovereignty: personal detail is classified before prompt assembly,
   and consent scopes gate how profile context can be used.
3. Governed autonomy: read, plan, patch, test, shell, network, commit, and
   publish actions are separate tool grants.
4. Open integration: OpenCode and similar clients connect through MaramaRoute's
   OpenAI-compatible gateway.
5. Audit without hoarding: records retain decision hashes, obligations, model
   identity, and reasons while prompt retention stays constrained.

## Minimum Product Loop

```text
developer asks for a coding task
  -> resolve `.sovereigncode/capsule.json`
  -> evaluate SovereignRequest
  -> build MaramaRoute request
  -> select resident LumynaX model
  -> produce plan
  -> request approval for writes or shell
  -> apply patch
  -> run tests
  -> store audit record
```

## Product Modules To Build Next

| Module | MVP Definition | Implementation Notes |
| --- | --- | --- |
| Workspace indexer | Reads repo files, ignores secrets/build outputs, tags data classes. | Start with `rg --files`, `.gitignore`, and capsule include/exclude rules. |
| Tool broker | Wraps file write, shell, git, package install, HTTP, and model calls. | Reuse policy decisions and emit one audit record per effectful tool call. |
| Terminal UI | Shows plan, selected model, obligations, diff, and test output. | Keep compatible with OpenCode-style terminal use. |
| Personal profile store | Keeps user preferences and memory under a personal capsule. | Local encrypted file first, tenant vault later. |
| Audit ledger | Append-only local JSONL with hash chain. | Export signed bundles for enterprise customers. |
| Tenant policy server | Central policy packs, model allowlists, API keys, quotas. | Only needed after local MVP works. |

## Default Plans

| Plan | Buyer | Included |
| --- | --- | --- |
| Local Developer | individual NZ developer | local capsule, local audit, MaramaRoute provider config |
| Team Sovereign | startup or SME | shared policy pack, route registry, team audit export |
| Regulated Workspace | council, health-adjacent, community data project | stronger approval gates, retention controls, signed audit, SSO-ready policy server |

## First Non-Negotiables

- Never train on a capsule unless `training_allowed` is explicitly true.
- Never export restricted or personal context unless `export_allowed` is true
  and the request carries human approval.
- Never route high-impact data to a non-local or non-LumynaX-governed model.
- Never apply file writes without a visible diff obligation.
- Never hide selected model identity from the audit record.
