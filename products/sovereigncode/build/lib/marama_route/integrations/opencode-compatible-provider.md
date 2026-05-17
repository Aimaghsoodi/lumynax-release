# OpenCode-Compatible Provider Integration

## Goal

Make AbteeX SovereignCode usable from OpenCode and similar coding agents without
requiring those tools to understand Data Capsules directly.

The integration shape is:

```text
OpenCode
  -> OpenAI-compatible provider config
  -> MaramaRoute gateway `/v1`
  -> SovereignCode policy and tool broker
  -> LumynaX model runtime
```

## Current Compatibility Target

OpenCode supports custom OpenAI-compatible providers through
`@ai-sdk/openai-compatible` and a provider `baseURL`. OpenRouter exposes an
OpenAI-like chat endpoint at `/api/v1/chat/completions`, with normalized request
and response payloads. MaramaRoute should therefore expose:

- `GET /v1/models`
- `POST /v1/chat/completions`
- `POST /v1/route`
- `GET /v1/route/{decision_id}`

References checked on 2026-05-17:

- https://opencode.ai/docs/providers
- https://openrouter.ai/docs/api-reference/overview/
- https://openrouter.ai/docs/api-reference/chat-completion

## OpenCode Provider Config

Use `examples/opencode.marama-route.json` as the project-local provider file.

The important fields are:

| Field | Value |
| --- | --- |
| `provider.abteex-marama.npm` | `@ai-sdk/openai-compatible` |
| `provider.abteex-marama.options.baseURL` | Local or hosted MaramaRoute `/v1` URL |
| `provider.abteex-marama.options.apiKey` | Environment backed key |
| `provider.abteex-marama.models` | LumynaX model aliases exposed by MaramaRoute |

## SovereignCode Responsibilities

OpenCode sends a normal chat request. SovereignCode and MaramaRoute add:

- capsule resolution from workspace policy files
- purpose and personal-detail checks before prompt assembly
- model routing based on residency, modality, task, and sensitivity
- visible approval gates before file writes, shell commands, network export, or commit
- audit records for policy decisions and route decisions

## Workspace Files

A governed workspace should carry:

```text
.sovereigncode/
  capsule.json
  tenant-policy.yaml
  approvals/
  audit/
opencode.json
```

The agent can start with `capsule.json` and `opencode.json`. The full tool
broker can add approvals and audit persistence in the next build stage.

## Minimum Viable Flow

1. User opens a project in OpenCode.
2. OpenCode uses the `abteex-marama` provider.
3. MaramaRoute dry-runs the chat payload and selects a LumynaX model.
4. SovereignCode checks the workspace Data Capsule before exposing context.
5. The coding agent proposes a plan.
6. File writes require a visible diff and an audit record.
7. Shell, network, commit, and publish actions require explicit approval.

## Similar Clients

Any client that can point at an OpenAI-compatible endpoint should use the same
gateway:

| Client type | Expected integration |
| --- | --- |
| OpenCode | `opencode.json` custom provider |
| Continue-style IDE assistant | OpenAI-compatible base URL and model ids |
| Aider-style terminal assistant | OpenAI-compatible base URL and key |
| Internal agent runner | Direct `/v1/route` and `/v1/chat/completions` calls |
| Browser console | Same API behind tenant auth |
