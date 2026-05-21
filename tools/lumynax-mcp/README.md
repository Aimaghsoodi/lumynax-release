# lumynax-mcp — Model Context Protocol server for the LumynaX family

Expose all 98 LumynaX models as MCP tools to **Claude Desktop**, **Cursor**, **Zed**, or any other MCP client. The model becomes a callable tool with full metadata (modalities, context, sovereignty tier, residency, license).

## Install

```bash
pip install lumynax-mcp
```

## Configure (Claude Desktop example)

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "lumynax": {
      "command": "lumynax-mcp",
      "env": {
        "LUMYNAX_GATEWAY_URL": "http://localhost:8080/v1",
        "LUMYNAX_GATEWAY_KEY": "lumynax-local-dev"
      }
    }
  }
}
```

Restart Claude Desktop. Claude now sees the LumynaX family.

## Tools exposed

| Tool | Purpose |
| --- | --- |
| `lumynax_route(prompt, ...)` | MaramaRoute — pick the best model for a request |
| `lumynax_chat(model, messages, enable_web_search)` | Run chat completion via the gateway; optionally enable self-hosted web search |
| `lumynax_list(tier, modality, max_params_b)` | List matching models |
| `lumynax_info(model)` | Full metadata for a model |
| `lumynax_web_search(query)` | Direct web search via the gateway's SearXNG |

## Without the gateway

If `LUMYNAX_GATEWAY_URL` is unreachable, `lumynax_route`, `lumynax_list`, and `lumynax_info` still work — they read the live registry from `AbteeXAILab/marama-route` on Hugging Face. `lumynax_chat` and `lumynax_web_search` require the gateway.

## Made in Aotearoa New Zealand

Part of the **LumynaX** sovereign-AI release family from **AbteeX AI Labs**. [abteex.com](https://abteex.com) · [lumynax.com](https://lumynax.com)

*Ko te mārama te tūāpapa.*
