---
name: "crashwatch"
description: "Real-time crash forensics monitor (1Hz power/temp/mem/per-process) running as a persistent systemd service that survives process kills, reboots, and sudden power events. Use BEFORE launching any long-running CPU+GPU workload (OpenClaw, Hermes, ComfyUI, training, multi-model inference) so that if the box dies you have the last 1-2 seconds of telemetry on disk. Also use AFTER a crash to reconstruct what happened in the moments before death."
---

# crashwatch — Real-time crash forensics

## Scopo

Questa skill gestisce il monitor real-time "scatola nera" della macchina
(DGX Spark, GB10 128GB unified). Tre differenze chiave rispetto a un
one-shot `nvidia-smi`:

| | one-shot `nvidia-smi` | `quick-vram-monitor` | `crashwatch` |
|---|---|---|---|
| Frequenza | istantanea | istantanea | **1Hz continuo** |
| Sopravvive a kill del processo | no | no | **si** (systemd `Restart=on-failure`) |
| Sopravvive a crash hardware | no (snapshot) | no (snapshot) | **si** (flush+fsync per riga) |
| File su disco dopo l'evento | no | no | **CSV in `outputs/crashwatch_*.csv`** |
| Telemetria | solo GPU | GPU+CPU snapshot | GPU + CPU + mem + top proc + alerts |

Senza `crashwatch` acceso, un crash improvviso del DGX non lascia nessuna
evidenza di cosa stava succedendo a power/temp/mem/processi nell'ultimo
secondo. Con `crashwatch` acceso, il CSV contiene quei dati: e' la
**scatola nera** del carico.

## Quando Invocarla

### Prima di lanciare un carico lungo

Invocare `crashwatch start` PRIMA di:
- avviare un render ComfyUI / WAN 2.2 / training / inferenza
- lanciare un modello locale (llama-server, vLLM) che possa impattare
  il thermal/power envelope
- riprodurre un crash noto (stress test mirato)
- qualunque sessione in cui l'utente dice "tieni d'occhio la macchina"

```bash
~/Programs/VRAM_shield/scripts/crashwatch.sh start
# output: unit attiva, path del CSV (formato outputs/crashwatch_YYYYMMDD_HHMM.csv)
```

### Dopo un crash / freeze / reboot improvviso

Invocare `crashwatch path && crashwatch stats && crashwatch tail`
NON APPENA la macchina e' tornata su:

```bash
CSV=$(~/Programs/VRAM_shield/scripts/crashwatch.sh path)
echo "tape: $CSV"
~/Programs/VRAM_shield/scripts/crashwatch.sh stats
# samples  = 2639
# GPU temp  max 85.0 C  min 46.0 C  avg 62.8 C
# GPU power max 94.61 W min 12.10 W avg 39.72 W
# CPU temp  max 96.2 C  min 49.7 C  avg 72.5 C
tail -5 "$CSV"   # ultimi sample prima della morte
```

## Procedura Standard (sequenza completa)

### 1. Accensione pre-carico

```bash
~/Programs/VRAM_shield/scripts/crashwatch.sh start
```

Lo script:
- crea `~/Programs/VRAM_shield/outputs/crashwatch_YYYYMMDD_HHMM.csv` (formato HHMM, mai sovrascritto dopo restart)
- lancia `monitor_realtime.py --hz 1 --out <file>` come systemd user unit `crashwatch.service`
- imposta `Restart=on-failure` + `RestartSec=3`: se il monitor muore, riparte da solo
- ogni riga e' scritta con `flush()+os.fsync()` quindi e' davvero su disco, non in buffer

Prerequisite (gia' attivo su DGX): `sudo loginctl enable-linger $USER`.

### 2. Verifica live

```bash
~/Programs/VRAM_shield/scripts/crashwatch.sh status
# crashwatch: ATTIVO
#   last csv : /home/jagones/Programs/VRAM_shield/outputs/crashwatch_20260909_2323.csv
# ...
```

### 3. Analisi post-crash (in ordine di priorita')

Dopo che la macchina e' ripartita, il CSV piu' recente contiene gli
ultimi 1-2 secondi reali. Controlla **in ordine**:

1. `gpu_temp_c >= 95` -> **thermal emergency GPU**
2. `cpu_max_temp_c >= 95` -> **thermal emergency CPU/LPDDR5x** (spesso la
   causa vera su GB10: LPDDR5x vive sullo stesso SoC)
3. `gpu_power_w` spike poi 0 -> **driver hang o power event**
4. `oom_kill_total` aumentato -> kernel OOM-killer (non lo Shield, ma rivela
   processi bugiardi)
5. `driver_err_30s > 0` -> errori del driver NVIDIA nei 30s precedenti
6. `dashboard_equiv_gb` (auto-computed) -> cosa avrebbe letto la Dashboard NVIDIA
7. `alert_*` = 1 -> quale soglia e' stata superata per prima

### 4. Spegnimento

```bash
~/Programs/VRAM_shield/scripts/crashwatch.sh stop
```

Lascia il CSV su disco per analisi successive.

## Subcommand

| Sub | Cosa fa |
|---|---|
| `start` | avvia (idempotente: se gia' attivo, stampa `status`) |
| `stop` | ferma la unit (CSV resta su disco) |
| `status` | stato unit + path CSV attivo |
| `tail` | ultime 20 righe del CSV attivo |
| `stats` | max/min/avg GPU temp, GPU power, CPU temp |
| `path` | solo il path del CSV (utile per piping) |
| `restart` | stop + start (apre un CSV nuovo) |

## Soglie (in `scripts/monitor_realtime.py`)

```python
THERMAL_WARN_C = 85
THERMAL_CRIT_C = 93
CPU_THERMAL_WARN_C = 85
CPU_THERMAL_CRIT_C = 95
MEM_WARN_PCT = 90
MEM_CRIT_PCT = 95
GB10_DASHBOARD_OVERHEAD_MIB = 8192
```

`alert_gpu_thermal`, `alert_cpu_thermal`, `alert_mem_crit` vengono impostati
a 1 se il valore nell'ultimo sample supera la soglia.

## CSV columns (29 totali)

```
timestamp, epoch_ms,
gpu_temp_c, gpu_power_w, gpu_util_pct,
gpu_clock_graph_mhz, gpu_clock_sm_mhz, gpu_clock_mem_mhz,
gpu_mem_used_mib, gpu_alloc_total_mib,
cpu_max_temp_c, cpu_avg_temp_c, cpu_avg_freq_mhz, cpu_max_freq_mhz, cpu_util_pct,
sys_mem_total_mib, sys_mem_used_mib, sys_mem_available_mib, sys_mem_pct,
dashboard_equiv_mib, dashboard_equiv_gb,
oom_kill_total, driver_err_30s,
top_gpu_pid, top_gpu_name, top_gpu_used_mib,
alert_gpu_thermal, alert_cpu_thermal, alert_mem_crit
```

`N/A` esplicito per campi non disponibili (es. `gpu_clock_mem_mhz`, `gpu_mem_used_mib`
su GB10 unified memory).

## Relazione Con Le Altre Skill

- **`quick-vram-monitor`**: snapshot one-shot, 4 campi JSON. Usare per
  "quanto sta consumando ADESSO?". **Complementare**, non sostituto:
  crashwatch e' per il "cosa e' successo appena prima del death".
- **`log-forensics`**: post-mortem su log testuali (gateway, NDJSON,
  systemd journal). `crashwatch` fornisce il nastro numerico continuo
  (power/temp/mem) che `log-forensics` non ha.
- **`state-inspector`**: ispezione dei layer di stato (requested,
  selected, configured, runtime, evidence). Usare per capire "quale
  modello sta girando"; `crashwatch` per "quanto sta soffrendo la
  macchina".
- **`system-resource-monitor`**: monitor cumulativo (long-term averages).
  `crashwatch` e' il registratore di volo ad alta fedelta'.

## Pitfalls

- **Niente venv attivo**: lo script `crashwatch.sh` crea la venv al primo
  avvio (richiede `python3 -m venv` + `pip install nvidia-ml-py psutil`).
  Tempo di bootstrap: 10-20 secondi.
- **`linger` non abilitato**: senza `sudo loginctl enable-linger $USER`,
  la unit muore quando termina il login grafico (GNOME logout / reboot).
  Verificare con `loginctl show-user $USER | grep Linger` (deve essere
  `Linger=yes`).
- **CSV non ruotato**: il naming HHMM (non HHMMSS) evita overwrite dopo
  restart. Se si vuole ruotare, `crashwatch.sh restart` apre un file nuovo.
- **Disk pressure**: 1Hz x 29 colonne x ~150 byte/row = ~13 MB/ora. Tenere
  d'occhio `df -h ~/Programs/VRAM_shield/outputs/` se si lascia acceso
  giorni.

## Implementazione

- Script: `~/Programs/VRAM_shield/scripts/crashwatch.sh` (wrapper bash)
- Monitor: `~/Programs/VRAM_shield/scripts/monitor_realtime.py` (Python, 1Hz)
- Unit: `crashwatch.service` (systemd transient, `Restart=on-failure`)
- Venv: `~/Programs/VRAM_shield/venv/`
- Output: `~/Programs/VRAM_shield/outputs/crashwatch_YYYYMMDD_HHMM.csv`
- Doc: `~/Programs/VRAM_shield/README.md` sezione "Real-Time Crash Forensics"

## Background: 3 crash DGX in 2 giorni, zero evidenza

Il 2026-09-08 e 2026-09-09 il DGX Spark ha subito 3 hard crash
(istantanei, no log, no OOM, no panic). Software escluso: il pattern
era incompatibile con un singolo processo (1x a 81GB+256K ctx,
1x idle 30.5h, 1x idle 40min). Verdetto provvisorio: HW
(alimentatore o board). Senza `crashwatch` attivo, il 4o crash sara'
altrettanto opaco. Con `crashwatch` attivo, il prossimo CSV dira'
se era thermal, power, driver hang, o memoria.
