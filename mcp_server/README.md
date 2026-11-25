# TimeTracker MCP server

Sidecar MCP server that exposes role-scoped tools over TimeTracker `/api/v1`.

See [docs/integrations/MCP.md](../docs/integrations/MCP.md) for setup (stdio, Streamable HTTP, OAuth).

```bash
export TIMETRACKER_BASE_URL=http://localhost:8080
export TIMETRACKER_API_TOKEN=tt_...
python -m mcp_server --transport stdio
```
