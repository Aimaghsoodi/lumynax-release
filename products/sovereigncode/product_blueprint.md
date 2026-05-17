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
