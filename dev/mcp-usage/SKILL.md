---
name: mcp-usage
description: Use when working with MCP servers — stdio (SDK subprocess) or HTTP/streamable transport — including verifying which configured servers are actually enabled and probing their live tool lists. Also covers the technique of listing a server's tools with a raw tools/list JSON-RPC POST.
---

# Calling MCP servers from Hermes

Configured MCP servers live under `mcp_servers:` in `~/.hermes/config.yaml` (each has a `command`, `args`, optional `env`). They are often NOT surfaced as directly-callable tools in a session's toolset. To actually invoke one, launch it as a subprocess and talk to it over stdio with the official MCP Python SDK.

## Procedure

1. Read the target server's `command` / `args` / `env` out of `~/.hermes/config.yaml` (grep the `mcp_servers:` block).
2. Pick a working MCP SDK. Do NOT trust bare `python3 -c "import mcp"` — see pitfall below.
3. Launch the server with `StdioServerParameters` and wrap the streams in `ClientSession`, using `templates/mcp_stdio_call.py` as the known-good starter.
4. `initialize()` first, then `list_tools()` (sanity check before calling), then `call_tool(name, args)`.
5. Before parsing a tool result, print the raw `content[i].text` shape once — return format varies per server (see pitfalls).
6. Prefer a server with zero external dependencies for a first smoke test (e.g. `filesystem`) — no network, no auth, trivially verifiable.

## HTTP-transport servers & live verification

Not every configured MCP server is a stdio subprocess. Some are declared with a `url:` alone (no `command:`), e.g. `open-notebook: {url: http://127.0.0.1:8892/mcp}` — the server runs as a long-lived daemon and Hermes reaches it over HTTP. See `references/http-transport-and-verification.md` for the exact probe recipe.

## Pitfalls

- The Deferred-tool catalog (the list of tool_ names you can load on demand) shows EVERY server Hermes can surface — including ones disabled in config. A server with `enabled: false` under `mcp_servers:` is REGISTERED but NOT active; do not claim it's live from the catalog. Read the `enabled:` flag in `~/.hermes/config.yaml` AND probe the live endpoint (`tools/list` POST) before reporting a server as active. (A server may instead be reachable via a proxy like `lazy-mcp` even when its own `enabled` is false — verify the proxy's own response, not the direct one.)
- Cached resource IDs go STALE after a server reload. Restarting/reloading an MCP server often re-imports its backend DB with brand-new IDs (notebook IDs, artifact IDs, session IDs). A previously-valid ID returns `not found` after reload. ALWAYS re-`list_*` the entity you are about to target right before calling the tool that takes its ID — never reuse an ID captured earlier in the same conversation.
- Recording a dry-run/discovery result OUTSIDE a tool that takes an id (e.g. `discover_sources` with `notebook_id`) fails `not found` if the notebook id came from an earlier list — the fix is re-listing with the current DB, not re-checking the tool's schema.
- Bare `import mcp` from system Python may resolve to a CLI binary named `mcp` (e.g. `/home/jagones/.local/bin/mcp`), not the SDK — you get `ImportError: cannot import name 'ClientSession' from 'mcp'`. Do not debug `__init__`; just create a dedicated venv (next pitfall).
- A `uv venv` does NOT ship a `pip` binary. Install into it with `uv pip install --python <venv>/bin/python "mcp[cli]"` (uv's pip front-end), not the venv's pip.
- Do not assume a server's stdout content is JSON. The `filesystem` server returns lines already formatted as `[DIR] name` / `[FILE] name` — `json.loads` throws. Print a raw sample first, then parse to the actual format.
- Skip chained-shell pipelines (`timeout 120 x 2>&1 | tail`) — the security scanner flags nested/unresolvable executables and blocks the call. Run the command plain; output auto-truncates.
- npx first-run installs the server package and can be slow — a generous timeout (120s) is safer than the default.

## Support files

- `templates/mcp_stdio_call.py` — known-good stdio client that lists a server's tools and calls `filesystem.list_directory` + `read_file`.
- `references/http-transport-and-verification.md` — probe recipe for `url:`-declared MCP servers: enabled-flag check, listening-port check, `tools/list` JSON-RPC POST, and the stale-IDs-after-reload rule.
- `references/open-notebook.md` — the `open-notebook` MCP workflow: `discover_sources` embed behavior, the `generate_artifact` `instructions` field, the **`kind="deck"`-enables-Mermaid-diagrams** rule, the separate API port for downloads, and the `surreal-commands-worker` dependency for async jobs.
