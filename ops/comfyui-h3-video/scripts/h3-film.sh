#!/usr/bin/env bash
# h3-film.sh - film lungo a scene concatenate (catena VERIFICATA video/h3_turbo).
#
# Perche' cosi': la catena genera UNA SCENA PER VOLTA, quindi la memoria dipende solo dai
# frame della singola scena (~5-6,5 s), NON dal totale -> N grande e' sicuro; il montaggio
# ancora ogni scena agli ultimi 22 frame + audio della precedente (continuita' C1).
#
# Uso:
#   h3-film.sh new <titolo> <scene> [durata]   # spec + dry-run, nessuna GPU
#   h3-film.sh run <titolo>                   # libera RAM + server + run + supervisore
#   h3-film.sh status <titolo>                # avanzamento
#   h3-film.sh verify <titolo>                # C0/C1/C2 + audio sui giunti
#   h3-film.sh stop <titolo>                  # ferma runner e supervisore
#
# Esempio 10 minuti:  h3-film.sh new mio_film 106 5.0   &&   h3-film.sh run mio_film
set -uo pipefail

PROJ=/home/jagones/Repositories/diffusion-pipelines/video/h3_turbo
PY=/home/jagones/wan555/venv/bin/python3
D="$(cd "$(dirname "$0")" && pwd)"

usage() {
  grep '^#' "$0" | sed 's/^# \{0,1\}//' | sed -n '2,16p'
}

spec_of() { printf '%s/film_specs/%s.json' "$PROJ" "$1"; }
out_of()  { printf '%s/outputs/film_%s' "$PROJ" "$1"; }
clips_of(){ ls -1 "$(out_of "$1")" 2>/dev/null | grep -cE '^[0-9]+_s[0-9]+\.mp4$'; }

cmd_new() {
  local title="${1:?manca <titolo>}" n="${2:?manca <scene>}" dur="${3:-5.0}"
  cd "$PROJ" || exit 1
  $PY gen_film_spec.py --scenes "$n" --duration "$dur" --title "$title" \
      --out "film_specs/$title.json" || exit 1
  echo
  echo "-- dry-run (nessuna GPU) --"
  $PY make_film.py "film_specs/$title.json" --dry-run | tail -3
  echo
  echo "ora:  h3-film.sh run $title"
}

cmd_run() {
  local title="${1:?manca <titolo>}"
  [ -f "$(spec_of "$title")" ] || { echo "spec assente: $(spec_of "$title")" >&2; exit 2; }
  mkdir -p "$PROJ/logs"
  bash "$D/h3-free-vram.sh" --kill
  bash "$D/h3-server.sh" start || exit 1
  echo
  setsid nohup $PY "$PROJ/make_film.py" "film_specs/$title.json" --bundle \
      >> "$PROJ/logs/$title.log" 2>&1 < /dev/null &
  echo "make_film avviato (log: $PROJ/logs/$title.log)"
  sleep 20
  setsid nohup $PY "$PROJ/h3_supervise.py" --spec "film_specs/$title.json" \
      >> "$PROJ/logs/${title}_supervisor.out" 2>&1 < /dev/null &
  echo "supervisore avviato (auto-resume + riavvio server)"
  sleep 8
  echo
  cmd_status "$title"
}

cmd_status() {
  local title="${1:?manca <titolo>}" out film
  out="$(out_of "$title")"; film="$out/$title.mp4"
  printf 'titolo        : %s\n' "$title"
  printf 'clip di scena : %s\n' "$(clips_of "$title")"
  printf 'film montato  : %s\n' "$([ -f "$film" ] && echo "PRESENTE ($film)" || echo 'non ancora')"
  pgrep -f "make_film.py.*$title" >/dev/null 2>&1 && echo 'runner        : attivo' || echo 'runner        : FERMO'
  pgrep -f "h3_supervise.py.*$title" >/dev/null 2>&1 && echo 'supervisore   : attivo' || echo 'supervisore   : FERMO'
  echo "-- log runner --";      tail -3 "$PROJ/logs/$title.log" 2>/dev/null
  echo "-- log supervisore --"; tail -2 "$PROJ/logs/${title}_supervisor.log" 2>/dev/null
  free -g | awk 'NR==2{printf "RAM: used=%sG avail=%sG\n", $3, $7}'
}

cmd_verify() {
  local title="${1:?manca <titolo>}" out frames
  out="$(out_of "$title")"
  [ -f "$out/$title.mp4" ] || { echo "film assente: $out/$title.mp4" >&2; exit 2; }
  cd "$PROJ" || exit 1
  frames=$($PY - "$title" <<'EOF'
import json, sys
from h3_single_scene import snap_frames, snap_len
t = sys.argv[1]
s = json.load(open(f"film_specs/{t}.json"))
b = snap_frames(float(s["scenes"][0].get("duration", 5.0)))
k = int(s.get("guide_frames", 22))
print(" ".join([str(b)] + [str(snap_len(b + k) - k)] * (len(s["scenes"]) - 1)))
EOF
)
  $PY verify_junctions.py "$out/$title.mp4" --frames $frames
}

cmd_stop() {
  local title="${1:?manca <titolo>}"
  pkill -f "h3_supervise.py.*$title" && echo 'supervisore fermato' || echo 'supervisore non attivo'
  pkill -f "make_film.py.*$title"     && echo 'runner fermato'      || echo 'runner non attivo'
}

case "${1:-help}" in
  new)    shift; cmd_new "$@" ;;
  run)    shift; cmd_run "$@" ;;
  status) shift; cmd_status "$@" ;;
  verify) shift; cmd_verify "$@" ;;
  stop)   shift; cmd_stop "$@" ;;
  *)      usage ;;
esac
