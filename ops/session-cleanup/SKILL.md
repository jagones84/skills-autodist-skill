---
name: session-cleanup
description: Use when WebUI shows stale Telegram/CLI/TUI/subagent sessions, the user says "clean sessions", "cancella sessioni", "pulisci chat list", or Hermes state.db has grown too large. Identifies the active session, archives (soft) or deletes (hard) the rest, VACUUMs the DB, and restarts the gateway.
---

# Cleaning up Hermes sessions

The WebUI chat list lives in `~/.hermes/state.db` (SQLite). When a session is created but never closed, it stays visible. Old Telegram/CLI/TUI/subagent sessions pile up: after 5–10 hours of normal use the WebUI shows 10+ entries; after days, hundreds.

## When to use

Trigger on any of:
- WebUI shows >5 sessions and the user wants them gone
- `~/.hermes/state.db` is large (>10 MB) and growing
- User says "cancella sessioni", "pulisci chat", "clean chat", "delete sessions"
- The user has just done a model switch / provider change and old sessions are stale

## Procedure (read this BEFORE touching the DB)

1. **Locate the DB**: `~/.hermes/state.db` (NOT under `Repositories/`). Always run `find ~ -name state.db` first if unsure.

2. **Snapshot for rollback** (mandatory, do not skip):
   ```bash
   DB="$HOME/.hermes/state.db"
   TS=$(date -u +%Y%m%d-%H%M)
   BAK="$HOME/.hermes/state.db.bak-session-cleanup-$TS"
   cp -a "$DB" "$BAK"
   echo "Backup: $BAK ($(stat -c%s "$BAK") bytes)"
   ```
   Keep the backup until the user confirms the cleanup is correct. Never delete it without being told.

3. **Inventory first — never blind DELETE**:
   ```bash
   sqlite3 "$DB" "SELECT id, source, substr(title,1,40), message_count,
                  datetime(created_at,'unixepoch','localtime'),
                  datetime(updated_at,'unixepoch','localtime')
                  FROM sessions ORDER BY updated_at DESC;"
   ```
   Show the user the table, then ask which to keep. **The default is: keep only the one most-recently-updated session** (the active conversation). Always confirm before destructive operations.

4. **Hard delete (default for old stuff)**:
   ```bash
   KEEP="<session_id_to_keep>"   # e.g. 20260907_151339_49312034
   sqlite3 "$DB" "DELETE FROM messages WHERE session_id != '$KEEP';"
   sqlite3 "$DB" "DELETE FROM sessions WHERE id != '$KEEP';"
   sqlite3 "$DB" "VACUUM;"
   ```
   This is irreversible. The backup is the only rollback.

5. **Soft delete (if you only want them hidden from WebUI)**:
   ```bash
   sqlite3 "$DB" "UPDATE sessions SET archived = 1 WHERE id != '$KEEP';"
   ```
   Reversible. The rows stay but the WebUI hides them.

6. **Verify**:
   ```bash
   echo "sessioni: $(sqlite3 "$DB" 'SELECT COUNT(*) FROM sessions;')"
   echo "messaggi: $(sqlite3 "$DB" 'SELECT COUNT(*) FROM messages;')"
   ```

7. **Restart the gateway** so the WebUI reloads:
   ```bash
   ~/.local/bin/hermes gateway restart     # or full path if in a venv
   sleep 8
   curl -sS http://127.0.0.1:8787/api/sessions | python3 -m json.tool | head -20
   ```

8. **Report to the user**:
   - Backup path + size
   - Before counts: N sessions, M messages
   - After counts: K sessions, L messages
   - New gateway PID
   - Confirm "Hey" or whichever session was preserved

## Pitfalls

- **DB location drift**: the Hermes state DB is `~/.hermes/state.db`, NOT under `Repositories/hermes-agent/state/`. An older revision lived in the repo; do not assume.
- **No `pip` in `uv venv`**: the gateway Python is `~/.hermes/.venv/bin/python` (uv-managed). `pip` is not on PATH. Use the venv's Python directly, not `pip install` into it.
- **Don't write the DB through `Z:\` UNC from a Windows Trae session**: PowerShell here cannot write `Z:\.hermes\state.db` reliably. Run all DB ops over `ssh dgx '...'`.
- **Always inventory first**. The active conversation is the row with the highest `updated_at`. Killing it would lose the in-flight context. A wrong `KEEP=` is unrecoverable without the backup.
- **BOM in JSON from the webui**: `curl` on Windows may prepend a UTF-8 BOM (0xEF 0xBB 0xBF) that breaks `json.load`. If a parse fails, retry with `curl ... | python3 -c "import sys; sys.stdin = open(sys.stdin.fileno(), encoding='utf-8', errors='ignore') ..."`. Cleaner: do all checks via `ssh dgx '...'` to keep output in UTF-8.
- **`hermes gateway restart` is async**: it returns immediately and the new process may take 5–10s to bind 8787. Always `sleep 8` before re-checking the WebUI.
- **The `messages` table is the real cost**: 44 sessions × 80 messages avg = 3.5k rows / 10 MB. Deleting sessions without `DELETE FROM messages` first leaves orphans that bloat the file (VACUUM only reclaims pages that are completely empty).

## One-shot script (for the user's `trash/`)

Save as `trash/clean-hermes-sessions.sh` on the DGX:

```bash
#!/usr/bin/env bash
set -e
DB="$HOME/.hermes/state.db"
KEEP="${1:?usage: $0 <keep_session_id>}"
TS=$(date -u +%Y%m%d-%H%M)
BAK="$HOME/.hermes/state.db.bak-cleanup-$TS"
cp -a "$DB" "$BAK"
echo "Backup: $BAK"
echo "PRIMA: $(sqlite3 "$DB" 'SELECT COUNT(*) FROM sessions;') sessioni, $(sqlite3 "$DB" 'SELECT COUNT(*) FROM messages;') messaggi"
sqlite3 "$DB" "DELETE FROM messages WHERE session_id != '$KEEP';"
sqlite3 "$DB" "DELETE FROM sessions WHERE id != '$KEEP';"
sqlite3 "$DB" "VACUUM;"
echo "DOPO:  $(sqlite3 "$DB" 'SELECT COUNT(*) FROM sessions;') sessioni, $(sqlite3 "$DB" 'SELECT COUNT(*) FROM messages;') messaggi"
sqlite3 "$DB" "SELECT '  KEEP: ' || id || ' [' || source || '] ' || substr(coalesce(title,'-'),1,40) FROM sessions;"
"$HOME/.local/bin/hermes" gateway restart
```

Usage: `ssh dgx 'bash /home/jagones/Repositories/trash/clean-hermes-sessions.sh 20260907_151339_49312034'`

## Verification

After a successful cleanup:
- `curl -sS http://127.0.0.1:8787/api/sessions | python3 -m json.tool` shows only the kept session
- WebUI chat list shows 1 entry
- `~/.hermes/state.db` size dropped noticeably
- Backup file exists and is non-zero
