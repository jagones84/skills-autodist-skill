#!/bin/bash
# nuke_sessions.sh - cancellazione multi-tabella di N sessioni con FK off
# Uso: nuke_sessions.sh --ids "id1 id2 ..." --keys "key1 key2 ..." [--db <path>] [--dry-run]
set -eu

DB="${HOME}/.openclaw/agents/coordinator/agent/openclaw-agent.sqlite"
IDS=""
KEYS=""
DRY_RUN=0
TS=$(date +%Y%m%d-%H%M%S)
SQLFILE="${HOME}/.openclaw/tmp/nuke_${TS}.sql"
PREVIEW="/tmp/nuke_preview.sql"

while [ $# -gt 0 ]; do
  case "$1" in
    --ids)       IDS="$2"; shift 2;;
    --keys)      KEYS="$2"; shift 2;;
    --db)        DB="$2"; shift 2;;
    --dry-run)   DRY_RUN=1; shift;;
    -h|--help)
      cat <<EOF
Uso: nuke_sessions.sh --ids "<uuid1> <uuid2> ..." --keys "<key1> <key2> ..." [--db <path>] [--dry-run]

Esempio:
  nuke_sessions.sh \\
    --ids 'c697cd0c-5a79-424c-8d62-fe8ebd5b23a8 47e2bedf-106c-406f-b399-d7d63cc74ad7' \\
    --keys 'agent:coordinator:openai-user:voxta-e3b0c44298fc-20260908 ...'
EOF
      exit 0;;
    *) echo "Argomento sconosciuto: $1" >&2; exit 1;;
  esac
done

[ -z "$IDS" ] && [ -z "$KEYS" ] && { echo "ERRORE: specificare almeno --ids o --keys" >&2; exit 1; }
[ -f "$DB" ] || { echo "ERRORE: DB non trovato: $DB" >&2; exit 1; }

# Costruisci IN clause da spazio-separato
if [ -n "$IDS" ]; then
  IN_SID=$(printf "'%s'," $IDS); IN_SID="${IN_SID%,}"
else
  IN_SID="''"  # placeholder vuoto, le query con IN ($IN_SID) saranno no-op
fi
if [ -n "$KEYS" ]; then
  IN_KEY=$(printf "'%s'," $KEYS); IN_KEY="${IN_KEY%,}"
else
  IN_KEY="''"
fi

echo "[nuke ${TS}] DB: $DB"
echo "[nuke ${TS}] ${DRY_RUN:+DRY-RUN (no modifiche)}$([ "$DRY_RUN" -eq 0 ] && echo " BACKUP + DELETE")"
echo "[nuke ${TS}] IDs: $(echo $IDS | wc -w)  Keys: $(echo $KEYS | wc -w)"

if [ "$DRY_RUN" -eq 0 ]; then
  if fuser "$DB" 2>/dev/null | grep -q .; then
    echo "[nuke ${TS}] ERRORE: DB ha processi lockanti, esco."
    exit 1
  fi
  BAK="${DB}.bak-pre-nuke-${TS}"
  echo "[nuke ${TS}] Backup DB -> $BAK"
  cp -a "$DB" "$BAK"
fi

# Mapping conversation_id (per cancellare conversation_deliveries + conversations)
MAP=$(sqlite3 "$DB" "SELECT DISTINCT conversation_id FROM session_conversations WHERE session_id IN ($IN_SID);" 2>/dev/null || true)
IN_CONV=""
if [ -n "$MAP" ]; then
  IN_CONV=$(echo "$MAP" | sed "s/.*/'&'/" | tr '\n' ',' | sed 's/,$//')
fi
echo "[nuke ${TS}] conversation_id mappati: ${IN_CONV:-nessuno}"

OUTFILE=$([ "$DRY_RUN" -eq 1 ] && echo "$PREVIEW" || echo "$SQLFILE")
mkdir -p "$(dirname "$OUTFILE")"

{
  echo "PRAGMA foreign_keys = OFF;"
  echo "BEGIN TRANSACTION;"
  echo ""
  echo "-- Tabelle con session_id diretto"
  for tbl in session_conversations transcript_events session_transcript_active_events session_transcript_index_state session_transcript_fts transcript_event_identities transcript_rewrite_watermarks trajectory_runtime_events memory_session_tombstones acp_parent_stream_events context_engine_turn_outbox; do
    echo "DELETE FROM ${tbl} WHERE session_id IN ($IN_SID);"
  done
  echo ""
  echo "-- Tabelle con entrambe session_id e session_key"
  for tbl in session_windows session_transcript_archives session_pending_inputs session_goal_operations memory_entry_origins; do
    echo "DELETE FROM ${tbl} WHERE session_id IN ($IN_SID) OR session_key IN ($IN_KEY);"
  done
  echo ""
  echo "-- Tabelle con solo session_key (PK)"
  for tbl in session_nodes session_participants session_progress_cards session_suggestions message_tool_run_outcomes session_members board_tabs board_widgets heartbeat_outcomes; do
    echo "DELETE FROM ${tbl} WHERE session_key IN ($IN_KEY);"
  done
  echo ""
  echo "-- session_nodes anche per current_session_id"
  echo "DELETE FROM session_nodes WHERE current_session_id IN ($IN_SID);"
  echo ""
  echo "-- standing_intents (source_session_id)"
  echo "DELETE FROM standing_intents WHERE source_session_id IN ($IN_SID);"
  echo ""
  if [ -n "$IN_CONV" ]; then
    echo "-- conversation_deliveries + conversations (via conversation_id mappato)"
    echo "DELETE FROM conversation_deliveries WHERE source_session_key IN ($IN_KEY) OR conversation_id IN ($IN_CONV);"
    echo "DELETE FROM conversations WHERE conversation_id IN ($IN_CONV);"
  else
    echo "-- conversation_deliveries (solo source_session_key)"
    echo "DELETE FROM conversation_deliveries WHERE source_session_key IN ($IN_KEY);"
  fi
  echo ""
  echo "COMMIT;"
  echo "PRAGMA foreign_keys = ON;"
  echo "PRAGMA wal_checkpoint(TRUNCATE);"
} > "$OUTFILE"

echo "[nuke ${TS}] SQL generato: $OUTFILE"
if [ "$DRY_RUN" -eq 1 ]; then
  echo "[nuke ${TS}] DRY-RUN: contenuto:"
  cat "$OUTFILE"
  exit 0
fi

echo "[nuke ${TS}] Eseguo SQL"
sqlite3 "$DB" < "$SQLFILE"
echo "[nuke ${TS}] sqlite3 exit: $?"

echo
echo "[nuke ${TS}] VERIFICA POST-DELETE"
for tbl in session_conversations session_windows transcript_events session_transcript_active_events session_transcript_archives session_transcript_index_state session_nodes session_participants session_progress_cards session_suggestions message_tool_run_outcomes session_members memory_session_tombstones standing_intents; do
  sid_cnt=$(sqlite3 "$DB" "SELECT COUNT(*) FROM $tbl WHERE session_id IN ($IN_SID);" 2>/dev/null || echo "n/a")
  skey_cnt=$(sqlite3 "$DB" "SELECT COUNT(*) FROM $tbl WHERE session_key IN ($IN_KEY);" 2>/dev/null || echo "n/a")
  printf "  %-35s sid=%-4s skey=%s\n" "$tbl" "$sid_cnt" "$skey_cnt"
done

echo
echo "[nuke ${TS}] FATTO. Backup: $BAK"
