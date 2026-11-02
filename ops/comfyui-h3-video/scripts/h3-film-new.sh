#!/usr/bin/env bash
# h3-film-new.sh <nome> [nblocchi=100] [secs=6] [img_partenza]
# Crea una cartella di produzione H3 (copione + run + PLAN + prompts + reports). NON genera video.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NAME="${1:?uso: h3-film-new.sh <nome> [nblocchi] [secs] [img]}"
NB="${2:-100}"; SEC="${3:-6}"
IMG="${4:-}"
DEST="/home/jagones/ComfyUI/outputs/$(date +%Y%m%d)_film_h3_${NAME}"
[ -e "$DEST" ] && { echo "esiste: $DEST"; exit 1; }
if [ -n "$IMG" ]; then
  python3 "$HERE/h3_film_gen.py" "$DEST" "$NB" "$SEC" "$IMG"
else
  python3 "$HERE/h3_film_gen.py" "$DEST" "$NB" "$SEC"
fi
echo "creato: $DEST"
echo "prossimi passi:" 
echo "  1) scrivi i prompt IR in $DEST/H3_CHAIN.json (segnaposto <SOSTITUIRE-TU>)"
echo "  2) bash $DEST/run_film.sh check"
echo "  3) bash $DEST/run_film.sh resume"
echo "  4) bash $DEST/run_film.sh watch 5     # opzionale, per ripresa automatica"
echo "  5) bash $DEST/run_film.sh status"
