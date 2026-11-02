#!/usr/bin/env bash
# h3-free-vram.sh - libera la memoria prima di un run H3 lungo (DGX Spark, RAM unificata).
#
# Perche': su GB10 RAM di CPU e VRAM sono lo stesso pool (121 GB). Il server H3 in preset
# `int8` occupa ~76 GB; un llama-server attivo ne mangia ~38 GB -> earlyoom/OOM. Va spento.
# `:8188` (ComfyUI immagini) va spento per lo stesso motivo.
#
# Uso:
#   h3-free-vram.sh            # solo report (non tocca niente)
#   h3-free-vram.sh --kill     # ferma llama-server e :8188
set -uo pipefail

show() {
  free -g | awk 'NR==2{printf "  RAM: used=%sG free=%sG avail=%sG\n", $3, $4, $7}'
  echo "  processi GPU:"
  if nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader 2>/dev/null | grep -q .; then
    nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader 2>/dev/null | sed 's/^/    /'
  else
    echo "    (nessuno)"
  fi
}

echo "== stato attuale =="
show

echo
echo "== chi occupa la memoria =="
if pgrep -f "llama-server" >/dev/null 2>&1; then
  pgrep -af "llama-server" | cut -c1-120 | sed 's/^/  llama-server: /'
else
  echo "  llama-server: nessuno"
fi
if pgrep -f "ComfyUI/main.py" >/dev/null 2>&1; then
  echo "  ComfyUI :8188: ATTIVO"
else
  echo "  ComfyUI :8188: spento"
fi

if [ "${1:-}" != "--kill" ]; then
  echo
  echo "solo report. Per liberare davvero:  h3-free-vram.sh --kill"
  exit 0
fi

echo
echo "== libero =="
if pkill -f "llama-server"; then echo "  llama-server fermato"; else echo "  llama-server: niente da fermare"; fi
if pgrep -f "ComfyUI/main.py" >/dev/null 2>&1; then
  pkill -f "ComfyUI/main.py" && echo "  ComfyUI :8188 fermato"
else
  echo "  ComfyUI :8188 gia' spento"
fi
sleep 6

echo
echo "== dopo =="
show
echo
echo "NOTA: non serve (ne' funziona) abbassare oom_score_adj da utente normale:"
echo "      richiede CAP_SYS_RESOURCE e fallisce con EPERM. Vedi H3_RECIPE.md par.10."
