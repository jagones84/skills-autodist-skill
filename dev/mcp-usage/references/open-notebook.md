# open-notebook MCP server — discovery, artifacts, download

The `open-notebook` MCP is declared by `url:` (HTTP) in config — the server runs as a daemon and the Hermes MCP transport proxies it. Tools surface as `mcp__open_notebook__*`. Backend = FastAPI + SurrealDB (the open-notebook-pr / open-notebook-mcp repos).

## Two slots: the MCP port and the API port

The MCP endpoint answers JSON-RPC (initialize / tools/list / tool calls) on the `url:` port (e.g. `http://127.0.0.1:8892/mcp`). The FastAPI backend — which the *download* URL points at — is a DIFFERENT port (e.g. `5056`). The MCP `download_url` field is relative (`/api/artifacts/<id>/download`); join it to the API base (`http://127.0.0.1:5056/api/artifacts/...`), not the MCP URL. Discovery with `ss -tlnp` + curl each candidate API port until `/api/artifacts/...` returns 200.

Dependences: the API needs a `surreal-commands-worker` process for async jobs (artifact generation, embeddings); without it jobs queue forever in `running`. Check `ps aux | grep surreal-commands-worker` before declaring an artifact stuck.

## discover_sources — does it load real content?

Yes. `discover_sources(query, notebook_id, limit, embed, dry_run, ...)` searches the web (provider e.g. `tavily`), ranks hits, and creates a Source per hit IN THE notebook you pass (`notebook_id` is required — you choose the destination).

The `embed` flag decides how much content is loaded:
- `embed: true` → downloads the URL, converts to Markdown (stored as `full_text`), splits into chunks AND vector-embeds them → the source becomes searchable via `search` / `ask_question`.
- `embed: false` (default) → saves only the link record, `embedded_chunks: 0`, NOT searchable.

So "discover then ask questions about the sources" requires `embed: true`. Verify real content load with `get_source(source_id)` and check `embedded` + `embedded_chunks > 0` (and `full_text` present) — those are the evidence it fetched the page, not just stored the URL.

## generate_artifact — choose kind; DIAGRAMS ONLY with kind="deck"

`generate_artifact(notebook_id, kind, formats, language, title, instructions, sections, model_id)`. Generation is async — `get_artifact` returns `job_status` (`running` → `completed`); poll until it settles; allow several minutes for a multi-section doc.

- `instructions` is the free-form prompt (forwarded verbatim to the writer LLM). Ask for style, emphasis, and diagrams here.
- `formats`: `md`, `html`, `docx`, `pptx`. `kind`: `report` or `deck` (`slides` is accepted as an alias for `deck`).
- **Mermaid diagrams only render with `kind="deck"`.** Verified in the backend source: `allow_diagrams=kind == "deck"` (artifact_commands.py); `report` sets it False, so no diagram fences are requested. A "report" you asked to include diagrams will come back as text-only.
- Diagram pipeline: the writer emits ` ```mermaid ` fences → `render_diagrams` converts each to a PNG via a browserless engine (`mermaidx` wheel — no Node needed, ~0.2s each) and embeds the image. If no engine is installed the fences stay as plain text.

## Download an artifact

`GET <api_base>/api/artifacts/<artifact_id>/download?format=docx|md` returns the file. `?format=` selects the format; omit for the default (`md`). Check `content-type` / `content-disposition` in the headers to confirm the right file came back.
