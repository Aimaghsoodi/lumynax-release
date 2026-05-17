# AbteeX SovereignCode Architecture

## North Star

SovereignCode should feel like a capable local coding agent, but every action must be accountable to data sovereignty and AI sovereignty controls. The product should never silently send sensitive code or governed data to a remote model, execute an external command, or publish a change without a visible decision trail.

## Control Plane

```text
User intent
  -> Workspace indexer
  -> Data Capsule resolver
  -> Sovereignty policy decision point
  -> LumynaX MaramaRoute model selection
  -> Tool broker
  -> Human review gate
  -> Audit ledger
```

## Core Concepts

### Data Capsule

A Data Capsule is the policy envelope attached to a workspace, dataset, tenant, case, source file set, or prompt context. It carries:

- `allowed_purposes`
- `denied_purposes`
- `resident_regions`
- `retention_days`
- `training_allowed`
- `export_allowed`
- `data_classes`
- `schema_context`
- `consent_record`

### Policy Decision Point

The policy decision point answers one question before every sensitive action: can this actor, for this purpose, in this region, using this model/tool, touch this capsule?

The first implementation lives at `src/tinyluminax/products/sovereigncode/policy.py`.

### Tool Broker

The broker is the enforcement layer for:

- Shell commands
- File writes
- Git commits
- Network calls
- Package installs
- Model calls
- Retrieval queries
- Training or distillation jobs

Each tool call receives a decision: allow, deny, or allow with obligations.

### Audit Ledger

Every decision creates a record containing:

- Capsule id
- Actor
- Purpose
- Action
- Model id
- Decision
- Reasons
- Obligations
- Request hash
- Timestamp

The first implementation lives at `src/tinyluminax/products/sovereigncode/audit.py`.

## Launch Milestones

| Milestone | Outcome |
| --- | --- |
| P0 scaffold | Policy engine, audit records, CLI, examples, docs. |
| P1 terminal loop | Local terminal agent with plan/edit/test workflow. |
| P2 tool broker | Policy wrappers for shell, git, file writes, package installs, and HTTP. |
| P3 MaramaRoute integration | Sovereign model routing for every model call. |
| P4 workspace UI | Browser console showing plan, policy, diffs, tests, and approvals. |
| P5 enterprise controls | Tenant policies, SSO hooks, signed audit exports, policy packs. |

## Aesthetic Direction

The product should follow the AbteeX/LumynaX visual system:

- White or warm paper background.
- Obsidian text.
- Warm amber accent.
- Thin rule-based layouts.
- Editorial headings.
- Mono labels for governance, provenance, and runtime details.
- No generic purple AI gradients.
