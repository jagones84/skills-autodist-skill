---
name: dgx-monitor
description: "Monitor onesto della memoria UNIFICATA del DGX Spark (GB10): memoria GPU per-processo, RAM di sistema condivisa, util/watt/temp GPU, CPU%. Trigger: monitor DGX, quanta VRAM, memoria GPU, unified memory, GPU usage, gpu temp, dgx stats, vram dgx spark, monitor memoria DGX, carico GPU."
---

# DGX Monitor (unified memory, GB10)

Monitor corretto per il **DGX Spark**. Sul GB10 CPU e GPU condividono
121GB di LPDDR5x, quindi `nvidia-smi --query-gpu=memory.used/total`
risponde **[N/A] per design**. L'unico analogo sensato della "VRAM usata"
e' la somma della memoria compute **per-processo**.

Output: **un JSON a riga unica**.

## Uso

```bash
python3 ~/Repositories/skills-autodist-skill/ops/dgx-monitor/scripts/dgx-monitor.py
```

## Cosa riporta

| Campo | Significato |
|---|---|
| `gpu.name / utilization_percent / power_w / temperature_c` | stato GPU |
| `gpu_compute_used_mb` | somma allocazioni GPU per-processo (**"VRAM usata"** su GB10) |
| `gpu_compute_processes[]` | pid / nome / memoria dei processi GPU |
| `system_memory_mb` | RAM di sistema (condivisa CPU+GPU), da `/proc/meminfo` |
| `cpu_percent` | carico CPU (campione 100ms) |
| `timestamp` / `iso` | quando e' stato letto |

## Regole d'oro / Gotchas

- **Niente dipendenze pip**: usa solo `nvidia-smi`, `/proc/meminfo`, `/proc/stat`, `/sys/class/thermal`.
- NON fidarsi di `memory.used/total` di nvidia-smi su GB10: e' `[N/A]` by design.
- Se `nvidia-smi` manca, i campi GPU sono `null` ma RAM/CPU/temp funzionano lo stesso.
- Se nvidia-smi non da la temperatura, prende la massima tra le thermal zone.

## Alternativa (da NON usare sul DGX)

`quick-vram-monitor` legge la VRAM via `pynvml` -> sul GB10 restituisce
`null`. Questa skill la sostituisce per il DGX Spark.

## File

- `scripts/dgx-monitor.py` — lo script (JSON a riga unica).
