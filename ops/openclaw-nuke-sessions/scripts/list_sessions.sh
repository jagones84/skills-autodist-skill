#!/bin/bash
# list_sessions.sh - lista sessioni del coordinator con primo messaggio utente
# Uso: list_sessions.sh [--db <path>] [--limit N] [--status done|failed|all]
set -eu

DB="${HOME}/.openclaw/agents/coordinator/agent/openclaw-agent.sqlite"
LIMIT=30
STATUS="all"

while [ $# -gt 0 ]; do
  case "$1" in
    --db) DB="$2"; shift 2;;
    --limit) LIMIT="$2"; shift 2;;
    --status) STATUS="$2"; shift 2;;
    -h|--help)
      echo "Uso: list_sessions.sh [--db <path>] [--limit N] [--status done|failed|all]"
      exit 0;;
    *) echo "Argomento sconosciuto: $1"; exit 1;;
  esac
done

[ -f "$DB" ] || { echo "ERRORE: DB non trovato: $DB" >&2; exit 1; }

STATUS_FILTER=""
case "$STATUS" in
  done)   STATUS_FILTER="AND sw.status = 'done'";;
  failed) STATUS_FILTER="AND sw.status = 'failed'";;
  all|"") STATUS_FILTER="";;
  *) echo "Status non valido: $STATUS"; exit 1;;
esac

# Query: per ogni sessione in session_windows, prendi il primo messaggio user
# (seq=0 e tipo user). Se non c'e', mostra "?" per la colonna primo_msg.
sqlite3 -header -column "$DB" "
WITH first_msgs AS (
  SELECT te.session_id,
         substr(te.event_json, 1, 80) AS primo_msg
  FROM transcript_events te
  WHERE te.seq = 0
)
SELECT substr(sw.session_id, 1, 8) || '...' AS sid,
       substr(sw.session_key, 1, 60) AS key,
       sw.status,
       coalesce(fm.primo_msg, '(no msg)') AS primo_msg
FROM session_windows sw
LEFT JOIN first_msgs fm ON fm.session_id = sw.session_id
WHERE 1=1 $STATUS_FILTER
ORDER BY sw.created_at DESC
LIMIT $LIMIT;
"
