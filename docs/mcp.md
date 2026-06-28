# Driving LiveTransit from Claude Desktop (MCP)

LiveTransit exposes its read-only tools over the **Model Context Protocol (MCP)**, so any
MCP host — **Claude Desktop**, Cursor, etc. — can call them and drive the live MBTA system.
The host supplies the LLM; our server is pure data tools, so it uses **no LLM quota**.

**Tools exposed:** `get_vehicle_positions`, `predict_eta`, `get_service_alerts`,
`plan_trip`, `search_docs`, `get_weather` — the same functions the in-app agent uses
(read-only, one source of truth).

## Prerequisite
The stack must be running so the tools have data: `docker compose up -d`.

## Connect Claude Desktop (stdio)
Add this to your `claude_desktop_config.json`
(Settings → Developer → Edit Config), adjusting the paths to your checkout:

```json
{
  "mcpServers": {
    "livetransit": {
      "command": "C:\\path\\to\\LiveTransit Copilot\\.venv\\Scripts\\python.exe",
      "args": ["-m", "backend.app.mcp.server"],
      "cwd": "C:\\path\\to\\LiveTransit Copilot"
    }
  }
}
```

Restart Claude Desktop. The `livetransit` tools appear in the tools menu. Try asking:
*"Use livetransit to plan a trip from Kendall to Boylston"* or *"What MBTA alerts are on the Blue Line?"*

## Networked transport (Streamable HTTP)
For a deployed/remote host, run the server over Streamable HTTP instead of stdio:

```bash
python -m backend.app.mcp.server http
```

## Quick local check (no Claude Desktop)
Any MCP client can list and call the tools. With the stack up, an stdio client that runs
`python -m backend.app.mcp.server` can `list_tools()` (returns the six above) and
`call_tool("get_vehicle_positions", {"route": "Red"})` to get live positions back.
