#!/usr/bin/env bash
# h3-watch.sh <cartella_film> [minuti=5] - se la catena muore e il film non e' completo, RIPRENDE (resume).
set -uo pipefail
D="${1:?uso: h3-watch.sh <cartella_film> [minuti]}"
MIN="${2:-5}"
CHAIN=/home/jagones/Repositories/comfyui-mcp/workflow_files/runners/h3_chain.py
SPEC="$D/H3_CHAIN.json"
PIDFILE="$D/logs/RUN.pid"
RUNLOG="$D/logs/RUN_resume.log"
log="$D/logs/WATCH.log"; mkdir -p "$D/logs"
echo -500 > /proc/self/oom_score_adj 2>/dev/null || true

find_running_pid() {
  if [ -f "$PIDFILE" ]; then
    pid="$(cat "$PIDFILE" 2>/dev/null || true)"
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      printf '%s\n' "$pid"
      return 0
    fi
    rm -f "$PIDFILE"
  fi
  pid="$(ps -eo pid=,args= | awk -v chain="$CHAIN" -v spec="$SPEC" '
    index($0, chain) && index($0, spec) && $0 !~ /h3-watch\.sh/ {print $1; exit}
  ')"
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
    printf '%s\n' "$pid" > "$PIDFILE"
    printf '%s\n' "$pid"
    return 0
  fi
  return 1
}

start_resume() {
  (
    cd "$D"
    echo -500 > /proc/self/oom_score_adj 2>/dev/null || true
    setsid nohup python3 "$CHAIN" --spec "$SPEC" --skip-existing >> "$RUNLOG" 2>&1 < /dev/null &
    echo $! > "$PIDFILE"
  )
  cat "$PIDFILE"
}

while true; do
  ts=$(date "+%F %T")
  n=$(ls "$D"/logs/*_meta.json 2>/dev/null | wc -l)
  tot=$(python3 -c "import json;print(len(json.load(open('$SPEC'))['blocks']))" 2>/dev/null || echo "?")
  OUT=$(python3 -c "import json;print(json.load(open('$SPEC'))['out'])" 2>/dev/null || echo "")
  if [ -n "$OUT" ] && [ -f "$OUT" ]; then
    echo "$ts COMPLETO: $OUT" >> "$log"
    break
  fi
  if pid="$(find_running_pid)"; then
    echo "$ts attiva ($n/$tot) pid=$pid" >> "$log"
  else
    new_pid="$(start_resume)"
    echo "$ts CATENA FERMA ($n/$tot) -> riprendo pid=$new_pid" >> "$log"
    sleep 20
  fi
  sleep $((MIN*60))
done
