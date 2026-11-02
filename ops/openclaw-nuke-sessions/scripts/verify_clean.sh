#!/bin/bash
# verify_clean.sh - verifica che le sessioni target siano sparite e le canoniche intatte
# Uso: verify_clean.sh --keys "<key1> <key2> ..." [--canon-keys "<key1> ..."] [--db <path>]
set -eu

DB="${HOME}/.openclaw/agents/coordinator/agent/openclaw-agent.sqlite"
TARGET_KEYS=""
CANON_KEYS="agent:coordinator:main:heartbeat agent:coordinator:telegram:direct:407582054:heartbeat agent:coordinator:openai-user:voxta-4b3df473b005-20260908 agent:coordinator:openai-user:voxta-9caa8e59fbb2-20260908 agent:coordinator:openai-user:voxta-547ec369c8e5-20260908"

while [ $# -gt 0 ]; do
  case "$1" in
    --keys)        TARGET_KEYS="$2"; shift 2;;
    --canon-keys)  CANON_KEYS="$2"; shift 2;;
    --db)          DB="$2"; shift 2;;
    -h|--help)
      echo "Uso: verify_clean.sh --keys \"<key1> ...\" [--canon-keys \"<key1> ...\"] [--db <path>]"
      exit 0;;
    *) echo "Argomento sconosciuto: $1" >&2; exit 1;;
  esac
done

[ -f "$DB" ] || { echo "ERRORE: DB non trovato: $DB" >&2; exit 1; }

echo "=== Integrity check ==="
sqlite3 "$DB" "PRAGMA integrity_check;"
echo
echo "=== Foreign key check (vuoto = OK) ==="
sqlite3 "$DB" "PRAGMA foreign_key_check;"
echo

if [ -n "$TARGET_KEYS" ]; then
  IN_TGT=$(printf "'%s'," $TARGET_KEYS); IN_TGT="${IN_TGT%,}"
  echo "=== Target keys (devono essere 0 ovunque) ==="
  for tbl in session_windows session_nodes session_conversations transcript_events session_transcript_active_events session_transcript_index_state session_transcript_archives session_participants session_progress_cards session_suggestions message_tool_run_outcomes session_members memory_session_tombstones standing_intents board_tabs board_widgets heartbeat_outcomes; do
    cnt=$(sqlite3 "$DB" "SELECT COUNT(*) FROM $tbl WHERE session_key IN ($IN_TGT);" 2>/dev/null || echo "n/a")
    if [ "$cnt" = "0" ]; then
      printf "  %-35s OK (0)\n" "$tbl"
    else
      printf "  %-35s ANCORA PRESENTI: %s\n" "$tbl" "$cnt"
    fi
  done
  echo
fi

if [ -n "$CANON_KEYS" ]; then
  IN_CAN=$(printf "'%s'," $CANON_KEYS); IN_CAN="${IN_CAN%,}"
  echo "=== Canoniche (devono essere > 0) ==="
  for tbl in session_windows session_nodes session_conversations transcript_events; do
    cnt=$(sqlite3 "$DB" "SELECT COUNT(*) FROM $tbl WHERE session_key IN ($IN_CAN);" 2>/dev/null)
    printf "  %-35s %s record\n" "$tbl" "$cnt"
  done
fi
