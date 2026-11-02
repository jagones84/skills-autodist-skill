---
name: "openclaw-model-switch"
description: "Manages the DGX Spark single-port llama.cpp router (:8080) backing the single OpenClaw/Hermes provider `local-dgx-router`. Lists available model aliases (7 in models.ini), verifies which model is currently loaded in VRAM, restarts the router to pick up config changes. Switch between models is automatic via the 'model' field of the OpenAI-compatible request — NO manual kill/relaunch needed per-switch. Invoke when the user asks to change model, free VRAM, verify which model is running, check available aliases, or restart the router. Triggers: 'cambia modello', 'switch model', 'switch to', 'load qwen', 'usa q4', 'usa q8', 'usa flashnext', 'usa nex', 'passa a', 'passa al modello', 'free VRAM', 'libera VRAM', 'which model is running', 'quale modello gira', 'verify model', '/models', '/switch', 'lista modelli', 'reload router', 'restart router', 'riavvia router', 'lista alias', 'available models', 'modelli disponibili'."
---

# OpenClaw Model Switch — DGX Spark single-port router

Use this skill to inspect/control the **single-port llama.cpp router**
on DGX Spark (192.168.1.37, port 8080). It is the **ONE** local backend
exposed to OpenClaw/Hermes via a single provider named `local-dgx-router`
(baseUrl `http://127.0.0.1:8080/v1`). Every model alias listed in
`config/models.ini` is reachable as `local-dgx-router/<alias>` — there
are **NO per-model providers** in OpenClaw/Hermes for this router.

(Other `local-*` providers in `~/.openclaw/openclaw.json` like
`local-qwen3-4b-windows`, `local-tpurtell`, `local-vllm` belong to other
machines/setups, NOT this router. Don't confuse them.)

The old "stack + proxy" architecture (q4/q8/flashnext su porte 8093/8094/
8096/8097/8110/8111, `launch_model.sh`, Python proxy retry-streaming) is
RETIRED. Rollback in `local/backups/pre-router-20260912_0058.zip`.

## Current architecture (read this first)

**ONE entrypoint**: `launchers/router.sh` (mirror DGX di `launchers/router.bat` WIN).

**ONE port**: `:8080`, host `0.0.0.0`. Tutti i modelli sono sezioni di
`config/models.ini` (al momento 5 alias); il router spawna un child
server per-request su una porta effimera, ci carica il modello chiesto,
risponde, lo killa.

**ONE binary**: `.llama-cpp-glm53/build/bin/llama-server` (build 0.3.0-dev,
unica che copre qwen35 / qwen3next / deepseek4 / qwen4exp / glm5next /
nex-n25 — verificato via `strings`).

**Switch is AUTOMATIC on the `model` field of the request**: OpenClaw/Hermes
inviando `model: "local-dgx-router/<alias>"` (o solo `<alias>` se il
provider lo permette) triggerano il caricamento del modello corrispondente.
**No need to kill/relaunch anything to change model.**

`--models-max 1` = **at most 1 model in VRAM at a time**. When a request
arrives for a different alias, the router kills the previous child (if
idle) and spawns a new one. Requests to the SAME alias reuse the same
child (KV context preserved as long as the process lives).

KV context of the child dies at: alias switch, router idle timeout,
router restart itself. Any long-running agentic session must keep this
in mind — plan for model reuse.

## Where things live

| cosa | path DGX |
|---|---|
| Entrypoint | `launchers/router.sh` |
| Config modelli | `config/models.ini` |
| Backup pre-router | `local/backups/pre-router-20260912_0058.zip` |
| Log router | `local/logs/router-8080.log` |
| PID router | `local/logs/router-8080.pid` |
| Dump dettagliato modelli | `local/scripts/diag/dump_router_models.py` |
| Lista rapida modelli | `local/scripts/diag/list_router_models.py` |
| Verifica post-restart | `local/scripts/diag/verify_router.py` |
| Diagnostica chi usa la GPU | `local/scripts/diag/who_uses.sh` |

## Standard procedure

### A. Status / discovery (NO switch, NO restart)

Lista tutti gli alias configurati + stato corrente di caricamento:

```bash
# dal DGX (ssh) — porta 8080 risponde sempre
curl -fsS http://127.0.0.1:8080/v1/models | python3 -m json.tool

# dump dettagliato con quant/ctx/KV/arch dal GGUF header
python3 /home/jagones/Programs/llama_cp/local/scripts/diag/dump_router_models.py

# compatto: alias + status
python3 /home/jagones/Programs/llama_cp/local/scripts/diag/list_router_models.py /tmp/models.json
```

To know **who is using the GPU right now** (not always the router — e.g.
ComfyUI, embedded OpenClaw sessions like skill_workshop):

```bash
ssh jagones@192.168.1.37
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader
bash /home/jagones/Programs/llama_cp/local/scripts/diag/who_uses.sh
```

Rule: **exactly ONE model resident in GPU memory**. The router parent (port
8080) holds no weights; it spawns at most one `llama-server` child
(`--models-max 1`). So `nvidia-smi` normally shows TWO llama-server PIDs
(parent ~170 MiB + child with the weights) and that is CORRECT. More than
one child means something is wrong — see §E.

### B. Switch model (NO manual command)

Switch is automatic on the client side. If the user says "switch to
nex-n25", you don't need to execute anything on DGX: just make sure the
next message goes to the provider with
`model: "local-dgx-router/nex-n25-mini-uncensored-q8"`.

If instead the user wants to **force VRAM release** (e.g. after a child
is stuck), you can kill only the child without touching the router:

```bash
ssh jagones@192.168.1.37 'pgrep -af "llama-server.*--alias"'
# → list of active children (each has --alias <name> and an ephemeral port).
# Example:
# 4721 llama-server ... --port 8081 --alias nex-n25-mini-uncensored-q8 ...
# kill 4721   # force model unload, router stays UP
```

Two ways to recognize a **child** (never the router):
- it carries `--alias <name>`
- its port is NOT 8080

WARNING: do NOT kill the process on port 8080 — that's the router itself,
not a child. For that see §D.

### C. Verify the router is healthy

```bash
# router reachable?
curl -fsS http://127.0.0.1:8080/health
# canonical way (READ-ONLY: lists aliases + status + VRAM, smokes only the
# already-loaded model, never forces a switch):
python3 /home/jagones/Programs/llama_cp/local/scripts/diag/verify_router.py
```

`verify_router.py`:
1. Lists every alias with load state and `architecture.input_modalities`
2. Prints the `nvidia-smi` VRAM footprint (expect router + 1 child = 2 rows)
3. Smokes a completion against the **already loaded** alias (or the alias
   passed as argv[1]) — it does NOT evict the current child
4. Reprints the final load state

### D. Restart router (to apply models.ini changes)

When you modify `config/models.ini` (new alias, changed ctx, different
KV type) the router **does NOT auto-reload** — you must restart it. Same
after a llama-server upgrade.

```bash
ssh jagones@192.168.1.37 'bash /home/jagones/Programs/llama_cp/launchers/router.sh'
```

The script:
1. `pkill -9 -f 'llama-server.*--port 8080'` — kills the router
2. `pkill -9 -f 'llama-server.*--alias '` — kills the model children
3. `sleep 2` — lets VRAM drain
4. Spawns new router in `nohup setsid`
5. Saves PID in `local/logs/router-8080.pid`
6. After 5s checks `kill -0 $PID` and dumps `/v1/models`

All in **one command**, idempotent. Final output = list of available
models + OK/FAIL.

**Step 2 is mandatory** (bug fixed 2026-10-24): the router spawns one
child `llama-server` per loaded alias on an **ephemeral port**. Killing
only `--port 8080` leaves the child alive holding the VRAM, and the next
model load fails with
`cudaMalloc failed: out of memory` /
`failed to fit params to free device memory: n_gpu_layers already set by user`.
Symptom: after a restart ALL aliases show `unloaded` and nothing is usable.

**Restart consequences**: all active agentic sessions lose KV context.
Plan accordingly (e.g. "reload the conversation" to the user, or postpone
restart to end of session).

### E. Failure handling

| symptom | probable cause | fix |
|---|---|---|
| after restart every alias is `unloaded`, log shows `cudaMalloc ... out of memory` | zombie child survived the kill (old script killed only `--port 8080`) | restart with §D (now kills `--alias` children too); if it persists `pkill -9 -f llama-server; sleep 3; router.sh` |
| `curl /v1/models` empty, log full of `slot not available` | previous child not terminated | wait 30s, router should reclaim; if not restart §D |
| `nvidia-smi` shows 2+ llama-server | router + child counted as 2 (normal), but 3+ means zombie | `pkill -9 -f llama-server; sleep 3; router.sh` |
| child dies immediately with OOM `cudaMalloc` | ctx too high for that model + mmproj | reduce `c=` in `models.ini` (see HANDOFF.md §11, known OOM on nex-n25 ctx=262144 + mmproj) or lower `n-gpu-layers` (nex uncensored uses 995) |
| `404 model not found` | alias doesn't exist in `models.ini` | add section, restart §D |
| Router won't restart after `pkill` | port 8080 still in TIME_WAIT | `sleep 30` then retry, or change port |
| Client (Hermes/OpenClaw) gets 502 | router in startup (sleep 5 of router.sh not enough for big models) | increase `sleep 5` in router.sh to `sleep 15` for large children |

### F. Free VRAM (kill EVERYTHING server-side)

Free all VRAM by killing both router and any child:

```bash
ssh jagones@192.168.1.37 'pkill -9 -f llama-server; sleep 3; nvidia-smi --query-gpu=memory.used --format=csv,noheader'
```

Then you can restart the router with §D when needed.

## OpenClaw/Hermes provider configuration

**Single provider** in `~/.openclaw/openclaw.json`:

```json
{
  "models": {
    "providers": {
      "local-dgx-router": {
        "baseUrl": "http://127.0.0.1:8080/v1",
        "apiKey": "no-key"
      }
    }
  }
}
```

Every alias in `config/models.ini` is automatically available as
`local-dgx-router/<alias>`. No per-model provider registration needed —
that's the whole point of the router.

Example per-model policy (in `models` map, not in `providers`):

```json
"local-dgx-router/nex-n25-mini-uncensored-q8": {
  "contextWindow": 262144,
  "maxTokens": 8192
}
```

When adding a new alias to `models.ini`:
1. Add the INI section
2. `bash launchers/router.sh` to restart
3. OPTIONAL: add the per-model policy entry in `openclaw.json` with
   `contextWindow` / `maxTokens` if OpenClaw/Hermes must know them

Hermes (if used): same pattern, baseUrl `http://<DGX_IP>:8080/v1`, same
single `local-dgx-router` provider name.

## Response Shape

Report COMPACT — exactly one of these forms:

- "Status OK: router :8080 UP, child attivo = `<alias>` su porta effimera
  N, KV qX/qY, n_ctx=XXX. 1 llama-server in GPU (X GiB). Modelli
  disponibili: A, B, C. OpenClaw ref: `local-dgx-router/<alias>`."
- "Switch automatico: prossima request con
  `model: 'local-dgx-router/<new-alias>'` triggererà il caricamento.
  KV context del child attuale (`<old-alias>`) verrà perso."
- "Restart eseguito: PID nuovo = N, log = path. `/v1/models` lista N
  modelli: ... . KV context di TUTTE le sessioni attive azzerato."
