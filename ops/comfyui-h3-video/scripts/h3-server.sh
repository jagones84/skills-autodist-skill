#!/usr/bin/env bash
# h3-server.sh - start|stop|status del server H3 affiancato (:8189). La 0.13.0 (:8188) NON si tocca.
set -euo pipefail
PORT=8189
BASE=/home/jagones/ComfyUI-H3
case "${1:-status}" in
  start)
    if curl -s -o /dev/null -w '%{http_code}' -m 3 "http://127.0.0.1:$PORT/" | grep -q 200; then
      echo "H3 gia' attivo su :$PORT"; exit 0
    fi
    cd "$BASE"
    setsid nohup bash run_h3.sh > server.log 2>&1 < /dev/null &
    echo "H3 avviato (log: $BASE/server.log); attendo..."
    for i in $(seq 1 60); do
      if curl -s -o /dev/null -w '%{http_code}' -m 3 "http://127.0.0.1:$PORT/" | grep -q 200; then
        echo "pronto"; exit 0
      fi
      sleep 5
    done
    echo "TIMEOUT: H3 non pronto"; exit 1 ;;
  stop)
    pkill -f 'ComfyUI-H3/venv/bin/pytho[n]' && echo "H3 fermato" || echo "H3 non attivo" ;;
  status)
    code=$(curl -s -o /dev/null -w '%{http_code}' -m 3 "http://127.0.0.1:$PORT/" || true)
    if [ "$code" = 200 ]; then echo "H3 UP (:$PORT)"; else echo "H3 DOWN (code=$code)"; fi ;;
  *) echo "uso: h3-server.sh start|stop|status" >&2; exit 2 ;;
esac
