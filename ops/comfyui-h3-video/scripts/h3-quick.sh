#!/usr/bin/env bash
# h3-quick.sh - esegue il runner H3 e consegna il video nel workspace.
# Usage: h3-quick.sh <argomenti di h3_run.py>
set -euo pipefail
WS=/home/jagones/.openclaw/workspace
RUNNER=/home/jagones/Repositories/comfyui-mcp/workflow_files/runners/h3_run.py
LOG="$(mktemp)"
set +e
python3 "$RUNNER" "$@" 2>&1 | tee "$LOG"
rc=${PIPESTATUS[0]}
set -e
OUT="$(grep -oE '/[^ ]+\.mp4' "$LOG" | tail -n1 || true)"
rm -f "$LOG"
if [ "$rc" != 0 ] || [ -z "${OUT:-}" ] || [ ! -f "$OUT" ]; then
  echo "ERRORE: run fallito o nessun mp4 prodotto (rc=$rc)"; exit 1
fi
mkdir -p "$WS"
DEST="$WS/$(basename "$OUT")"
cp -f "$OUT" "$DEST"
echo "READY_TO_SEND: $DEST"
