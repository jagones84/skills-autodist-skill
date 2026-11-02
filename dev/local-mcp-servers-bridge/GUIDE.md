# Local MCP Servers Bridge (SOLO ↔ Trae/VSCode)

This skill is **documentation/instructions** that teaches an agent how to reliably use your **local MCP servers** that you already configure in **Trae/VSCode** under `mcpServers`.

## 0) Important limitations

- A *skill* cannot magically “enable” MCP servers by itself.
  - The MCP servers must be **enabled and running** via your Trae/VSCode MCP configuration.
  - Once Trae/VSCode exposes them to SOLO sessions, the agent can call their tools.

## 1) Security (do this first)

Your pasted config contains **hardcoded secrets/tokens**. Assume they are compromised:

1. **Rotate/Revoke** any exposed tokens (Discord bot token, GitHub PAT, RapidAPI keys, HuggingFace tokens, Telegram credentials, OpenRouter keys, etc.).
2. **Never commit** secrets to git (even in private repos).
3. Prefer:
   - OS-level env vars (Windows “Environment Variables”)
   - or a local `.env` file *loaded by your launcher* (not by MCP automatically unless your client supports it)

See `.env.template` in this package for suggested variable names.

## 2) Common config fixes for Windows + MCP

### 2.1 Remove backticks in args

In JSON `args`, strings like:

- `` `https://example.com` ``

should be:

- `https://example.com`

Backticks are not “quotes” here; they become part of the literal argument and often break tools like `mcp-remote`.

### 2.2 Split `command` vs `args`

Bad (often fails because `command` is not an executable):

```json
{ "command": "npx -y @lmcc-dev/mult-fetch-mcp-server", "args": [] }
```

Good:

```json
{ "command": "npx", "args": ["-y", "@lmcc-dev/mult-fetch-mcp-server"] }
```

### 2.3 Use `cmd.exe /c` only when you must

If you need to patch `PATH` temporarily, using:

```json
{ "command": "cmd.exe", "args": ["/c", "set PATH=...;%PATH% && npx -y ..."] }
```

is fine on Windows. Otherwise, prefer direct `command: "npx"` with args.

### 2.4 Timeouts

If a server does heavy imports or launches Docker, increase `timeout` (e.g. 600–3600).

## 3) Pre-flight checklist before expecting SOLO to use the tools

1. Set `disabled: false` for the server(s) you want.
2. Confirm Node/Python paths exist (absolute paths recommended).
3. Start Trae/VSCode and ensure the MCP server shows “running/connected”.
4. Test server manually in a terminal:
   - `npx -y <package>`
   - or run the exact `command` + `args` you configured
5. Only then try tool calls from SOLO.

## 4) Usage recipes (agent-facing)

### 4.1 Filesystem server (recommended baseline)

Typical flow:
1. `list_allowed_directories`
2. `list_directory` (pick a directory)
3. `read_file` / `read_multiple_files`
4. `search_files`
5. `write_file` / `edit_file` only when user explicitly wants changes

### 4.2 Chart server

When user asks for a chart:
1. Collect data (from filesystem or web)
2. Call `create_chart` / `render_graph`
3. Save the artifact to an output folder the user can access

### 4.3 Remote MCP via `mcp-remote`

Ensure URLs are plain strings (no backticks) and auth headers come from env vars if possible.

## 5) Troubleshooting quick hits

- **Server not visible** in SOLO session:
  - It is still `disabled: true`, or Trae didn’t reload config, or the server crashes on start.
- **npx installs every time / slow**:
  - Consider installing globally, pinning versions, or using a local Node project + `node_modules`.
- **Python venv path issues**:
  - Use absolute interpreter paths and verify `python.exe` exists.
- **Docker servers fail**:
  - Ensure Docker Desktop is running and the image exists (`docker pull ...`).

