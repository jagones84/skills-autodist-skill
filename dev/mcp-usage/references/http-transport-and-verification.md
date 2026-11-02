# Verifying & probing HTTP-transport MCP servers

An MCP server declared by `url:` alone (`mcp_servers.<name>: {url: http://host:port/mcp}`) is a long-lived daemon reached over HTTP, not a stdio subprocess. Use this recipe to confirm it is ACTIVE and to list the tools it actually exposes.

## 1. Is it enabled?

Read `~/.hermes/config.yaml`, `mcp_servers:` block. A server with `enabled: false` is REGISTERED but NOT loaded — do not report it as live. Servers without the flag default to enabled. A proxy endpoint (e.g. `lazy-mcp`) may re-expose other servers (voice-studio, cccc, clodds, ...) — query the proxy itself to learn what it serves.

## 2. Is the daemon listening?

```bash
ss -tlnp | grep <port>
```
If nothing listens, the server is down regardless of config.

## 3. List its tools (JSON-RPC POST)

```bash
curl -s -m 6 -X POST http://127.0.0.1:<port>/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"probe","version":"1.0"}}}'
```
Then, in a second request, list tools:

```bash
data='{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
curl -s -X POST http://127.0.0.1:<port>/mcp -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" -d "$data" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); [print('-',t['name']) for t in d['result']['tools']]; print('TOTAL:',len(d['result']['tools']))"
```

Re-invoking `tools/list` after a reload is the single most reliable way to detect that the server gained/lost tools (a working library surfaced a 33-to-38 tool jump after a reload).

## 4. Prove a tool works, don't just list it

`tools/list` proves presence, not function. Invoke at least one cheap read tool end-to-end through Hermes (`tool_call` on `mcp__<server>__<tool>`) and confirm a real result, not an error envelope.

## Pitfall: IDs gone stale after reload

Restarting/reloading an MCP server commonly re-imports its backend DB with fresh IDs. Reusing a notebook/artifact/session ID captured earlier in the same conversation returns `not found`. The fix: re-run the relevant `list_*` tool immediately before the call that consumes the ID. This is an ID-freshness rule, not a server bug.
