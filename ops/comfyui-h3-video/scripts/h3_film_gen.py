#!/usr/bin/env python3
"""h3_film_gen.py <DEST> [nblocchi] [secs] [img_partenza]
Genera una cartella film H3 riproducibile: H3_CHAIN.json + run_film.sh + PLAN.md.
NON genera video. I prompt IR restano segnaposto <SOSTITUIRE-TU: ...>."""
import json, os, sys


dest = sys.argv[1]
nb = int(sys.argv[2]) if len(sys.argv) > 2 else 50
sec = float(sys.argv[3]) if len(sys.argv) > 3 else 12.0
img = sys.argv[4] if len(sys.argv) > 4 else "<PATH_IMG_PARTENZA>"

os.makedirs(dest, exist_ok=True)
os.makedirs(os.path.join(dest, "prompts"), exist_ok=True)
os.makedirs(os.path.join(dest, "logs"), exist_ok=True)
os.makedirs(os.path.join(dest, "reports"), exist_ok=True)


def block(i):
    first = i == 0
    return {
        "name": "B%02d" % i,
        "mode": "r2v" if first else "continuation",
        "seconds": sec,
        "seed": 1000 + i,
        "refs": [img] if first else None,
        "prompt_ir": {
            "subject_definitions": ["<SOSTITUIRE-TU: identita' del soggetto, identica in ogni shot>"],
            "shots": [
                {
                    "text": "<SOSTITUIRE-TU: testo IR di questo blocco (350-500 parole, formato ufficiale; "
                    "usa h3_prompt_ir.py). Placeholder neutro: single continuous take, camera pushes "
                    "in very slowly, photorealistic, no captions or text.>"
                }
            ],
            "soundscape": "<SOSTITUIRE-TU: room tone / respiro / suoni coerenti>",
            "music": "Sustained low synth pad, slow tempo, one deep pulse every two seconds, no build.",
        },
    }


blocks = []
for i in range(nb):
    b = block(i)
    if b["refs"] is None:
        del b["refs"]
    blocks.append(b)

spec = {
    "_comment": "FILM MiniMax-H3. PROMPT = SEGNAPOSTO: scriverli e validare con h3_prompt_ir.py. Vedi PLAN.md.",
    "preset": "fasth3-distill",
    "out": os.path.join(dest, "FILM_H3.mp4"),
    "workdir": dest,
    "logdir": os.path.join(dest, "logs"),
    "concat_mode": "reencode",
    "inherit_refs": True,
    "continuation_style": "clip",
    "film": {
        "style": "Live-action, cinematic, 35mm, shallow depth of field, subtle film grain.",
        "language": "English",
    },
    "defaults": {
        "fps": 24,
        "canvas": [960, 544],
        "seconds": sec,
        "steps": 4,
        "sampler": "res_multistep",
        "scheduler": "simple",
        "seed": 1000,
    },
    "blocks": blocks,
}
with open(os.path.join(dest, "H3_CHAIN.json"), "w", newline="\n", encoding="utf-8") as fh:
    json.dump(spec, fh, indent=2, ensure_ascii=False)

run = """#!/usr/bin/env bash
# run_film.sh - entry point unico per un film H3. Generato da h3_film_gen.py.
set -euo pipefail
D="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHAIN=/home/jagones/Repositories/comfyui-mcp/workflow_files/runners/h3_chain.py
WATCH=/home/jagones/.openclaw/workspace/skills/comfyui-h3-video/scripts/h3-watch.sh
SPEC="$D/H3_CHAIN.json"
LOGDIR="$D/logs"
RUNLOG="$LOGDIR/RUN_resume.log"
PIDFILE="$LOGDIR/RUN.pid"
mkdir -p "$LOGDIR"

set_oom_guard() {
  echo -500 > /proc/self/oom_score_adj 2>/dev/null || true
}

launch_bg() {
  (
    cd "$D"
    set_oom_guard
    setsid nohup python3 "$CHAIN" --spec "$SPEC" --skip-existing >> "$RUNLOG" 2>&1 < /dev/null &
    echo $! > "$PIDFILE"
  )
  echo "resume in background: PID $(cat "$PIDFILE")"
}

status() {
  python3 - "$SPEC" "$PIDFILE" <<'PY'
import json, os, sys
spec_path, pidfile = sys.argv[1:3]
spec = json.load(open(spec_path, encoding="utf-8"))
workdir = spec.get("workdir") or os.path.dirname(os.path.abspath(spec["out"]))
logdir = spec.get("logdir") or os.path.join(workdir, "logs")
tot = len(spec.get("blocks", []))
done = 0
if os.path.isdir(logdir):
    done = sum(1 for n in os.listdir(logdir) if n.endswith("_meta.json"))
print(f"spec: {spec_path}")
print(f"output: {spec['out']}")
print(f"progress: {done}/{tot}")
if os.path.exists(spec["out"]):
    print("state: COMPLETE")
else:
    pid = ""
    if os.path.exists(pidfile):
        pid = open(pidfile, encoding="utf-8").read().strip()
    if pid:
        print(f"pidfile: {pid}")
    print("state: INCOMPLETE")
PY
  if [ -f "$PIDFILE" ]; then
    PID="$(cat "$PIDFILE" 2>/dev/null || true)"
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
      echo "process: RUNNING ($PID)"
    else
      echo "process: STOPPED"
    fi
  else
    echo "process: UNKNOWN"
  fi
}

case "${1:-check}" in
  check)   python3 "$CHAIN" --spec "$SPEC" --dry-run ;;
  run)     set_oom_guard; python3 "$CHAIN" --spec "$SPEC" ;;
  resume)  set_oom_guard; python3 "$CHAIN" --spec "$SPEC" --skip-existing ;;
  only)    set_oom_guard; python3 "$CHAIN" --spec "$SPEC" --only "${2:?indice}" ;;
  watch)   exec bash "$WATCH" "$D" "${2:-5}" ;;
  resume-bg) launch_bg ;;
  status)  status ;;
  *) echo "uso: run_film.sh [check|run|resume|only N|watch [min]|resume-bg|status]"; exit 2 ;;
esac
"""
rp = os.path.join(dest, "run_film.sh")
open(rp, "w", newline="\n", encoding="utf-8").write(run)
os.chmod(rp, 0o755)

plan = """# FILM H3 - PREPARATO (non lanciato)

## File
| file | ruolo |
|---|---|
| `H3_CHAIN.json` | COPIONE (dati): {nb} blocchi x {sec}s = {tot}s |
| `run_film.sh` | SCRIPT di lancio: check / run / resume / watch / status / only N |
| `prompts/` | i testi IR per blocco (350-500 parole) |
| `logs/` | grafi+meta per blocco (li crea h3_chain.py) |
| `reports/` | analisi, note crash, benchmark, QA umana |
| `FILM_H3.mp4` | output finale |

I PROMPT sono segnaposto `<SOSTITUIRE-TU: ...>`: scrivili con `h3_prompt_ir.py`, poi `run_film.sh check`.

## Lancio (quando decidi)
```bash
bash run_film.sh check     # valida (no GPU)
bash run_film.sh run       # genera da zero/foreground
bash run_film.sh resume    # riprende foreground con --skip-existing
bash run_film.sh only N    # rigenera il blocco N
bash run_film.sh watch 5   # watchdog ogni 5 min
bash run_film.sh status    # stato locale senza GPU
```

Regola: primo blocco `r2v` (refs=immagine), gli altri `continuation` (ultimo frame + audio del precedente).
Default consigliato DGX Spark: {nb} blocchi x {sec}s, preset `fasth3-distill`, `960x544`, `4 step`.
Se il run viene ucciso di notte: `resume` o `watch`, non rilanciare mai da zero.
""".format(nb=nb, sec=sec, tot=int(nb * sec))
open(os.path.join(dest, "PLAN.md"), "w", newline="\n", encoding="utf-8").write(plan)
print("preparato:", dest, "->", nb, "blocchi x", sec, "s =", int(nb * sec), "s")
