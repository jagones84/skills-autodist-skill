---
name: comfyui-h3-video
description: >-
  Local MiniMax-H3 open-weights video engine (affiancated ComfyUI on :8189) for
  multi-shot clips, real continuity and NATIVE audio. Use for text-to-video,
  first/last-frame, reference-to-video (identity lock) and multishot/continuation.
---

# comfyui-h3-video - MiniMax-H3 (open weights) su DGX Spark

Motore video **alternativo a Wan2.2**: gira su un **ComfyUI affiancato e pinnato** (`~/ComfyUI-H3`, `v0.35.2`),
porta **8189** (la `:8188` con la 0.13.0 resta per immagini/foley e **NON si tocca**). Da' **audio nativo**
(no foley separato), **multi-shot in una passata** (`AddGuide`) e **continuita'** (`continuation`).

## Regola d'uso (quale motore)
| Serve | Motore |
|---|---|
| Racordo / multi-shot / audio nativo / identity lock | **H3** (questa skill) |
| Atti espliciti con LoRA per-atto (blowjob/doggystyle/...) | **FLF2V** (Wan2.2, altra pipeline) |

## Pre-flight (obbligatorio, in ordine)
1. `~/.openclaw/workspace/AGENTS.md`, `MEMORY.md`, `TOOLS.md`.
2. **`diffusion-pipelines/film/docs/H3_RECIPE.md`** - fonte tecnica (preset, ricette, errori noti,
   licenza). **§12** = continuita' di moto/audio, camera score, anti-spawn, trappole.
   Per i film lunghi: `diffusion-pipelines/video/h3_turbo/` (catena verificata) e
   `diffusion-pipelines/film/docs/ACTION-GRAMMAR.md` (varieta' d'azione).
3. `diffusion-pipelines/film/h3/H3_MODELS.lock.json` - pesi pinnati (repo+revisione+sha256).
4. questa SKILL.

## Gate (sempre, prima di generare)
```bash
bash scripts/h3-doctor.sh        # DEVE dire "0 FAIL, 0 WARN"
```

## Comandi canonici (un solo wrapper per caso)

### 1. Un blocco - `h3-run.sh` (-> runners/h3_run.py)
```bash
bash scripts/h3-run.sh --mode t2v --prompt-file prompt.txt --seconds 5
bash scripts/h3-run.sh --mode flf2v --start K0.png --end K1.png --prompt-file p.txt --seconds 5
bash scripts/h3-run.sh --mode r2v --ref K0.png --ref K1.png --prompt-file p.txt --seconds 5
bash scripts/h3-run.sh --mode multishot --ref K0.png --guide K0.png@0 --guide K1.png@5 --prompt-file p.txt --seconds 12
```
Modi: `t2v` | `flf2v` | `r2v` (identity lock, <=9 img) | `multishot` (ancore `--guide IMG@SEC`).
Opzioni: `--preset`, `--seconds` (snap `17n+5`), `--width/--height` (default 1344x768), `--steps`, `--seed`,
`--lora ALIAS`, `--audio-guide WAV@SEC`, `--check-nodes`, `--dry-run`, `--save-graph`.

### 2. Catena multi-blocco - `h3-chain.sh` (-> runners/h3_chain.py)
```bash
bash scripts/h3-chain.sh --spec h3_chain.json          # multishot / continuation
bash scripts/h3-chain.sh --spec h3_chain.json --only 2 # rigenera solo il blocco 2
```
Spec di esempio: `diffusion-pipelines/film/examples/h3_chain.example.json`.

### 3. Prompt in formato IR (obbligatorio per la qualita')
```bash
python3 /home/jagones/Repositories/diffusion-pipelines/film/h3/h3_prompt_ir.py --spec film_spec.json --shot 3 --lang en
```
In locale NON esiste il conditioner hosted di MiniMax: scrivere il prompt nel formato IR ufficiale
(`integrated_multimodal_description: ... overall_soundscape: ... non_diegetic_music: ...`), 350-500 parole,
con `[Shot N] At MM:SS.mmm` per i multi-shot.

## Produzione LUNGA (film / corto 1-10 min) - cosa DEVI produrre

> **Per un film nuovo parti da "Film lunghi v2: MULTI-SHOT" (sotto), NON da questa sezione:**
> gli artefatti elencati qui sono quelli della **catena `h3-chain` a inquadratura unica**, che
> resta valida per una singola scena continua ma produce film monotoni se usata per tutto il
> film. La struttura di cartelle e l'**eco degli input** valgono per entrambi i metodi.

Per una clip lunga NON basta un blocco: **prepara una cartella di produzione** con questi artefatti.
La skill non li indovina: **li devi creare tu**. Modello H3 pronto: `outputs/20260915_film_h3_cyberpunk/`.

### Prima di tutto: SCEGLI IL MOTORE (due strade, COPIONI diversi)
| motore | copione (dati) | runner / lancio | quando usarlo |
|---|---|---|---|
| **H3** (questa skill) | `H3_CHAIN.json` | `runners/h3_chain.py` (`run_film.sh`) | continuita' reale + **audio nativo** + multi-shot in una passata |
| **Wan2.2 film** (longform) | `script/film_spec.json` | `diffusion-pipelines/video/longform_wan555.py` + stage | **atti con LoRA per-atto**, keyframe di stato, foley/voci separati |
| **Wan2.2 FLF2V** (catena) | `film/examples/keyframes_chain.example.json` | `runners/flf2v_chain.py --spec` (ComfyUI `:8188`) | coppie keyframe start/end |

Se scegli **Wan2.2 film**, NON usare `h3-film-new.sh`: scaffolda con
`bash /home/jagones/Repositories/diffusion-pipelines/film/new_film.sh <nome>` e adatta `script/film_spec.json`.
I suoi artefatti: `build_manifest.py` (copione -> `manifest.json` + shotlist + timeline voci),
`stage1_keyframes.sh` / `stage2_shots.sh` / `stage3_voices.sh` / `stage4_mix.sh`, `overnight_run.sh`,
output `mix/FILM_FINAL.mp4`. Motore/venv: `diffusion-pipelines/video/`, venv `/home/jagones/wan555/venv`.
Vedi `film/README.md` e `film/docs/RECIPE.md`.

> **Regola di scelta**: H3 per raccordo/multi-shot/audio/identita'; **FLF2V + LoRA per-atto per gli atti espliciti**
> (H3 non ha LoRA per-atto). I due motori si possono anche **mescolare** blocco per blocco (H3 per il raccordo, FLF2V per l'atto).

---

### Se usi H3: gli artefatti che DEVI produrre

| artefatto | file | ruolo |
|---|---|---|
| **COPIONE** (dati) | `H3_CHAIN.json` | blocchi (`multishot`/`continuation`), `seconds`, `refs`, preset, seed, `prompt_ir` |
| **SCRIPT di lancio** | `run_film.sh` | `check` / `run` / `resume` / `watch` / `status` / `only N` |
| **ISTRUZIONI** | `PLAN.md` | struttura, stime, come si lancia |
| **PROMPT IR** | `prompts/` | un testo per blocco (350-500 parole) |
| **LOG** | `logs/` | grafi+meta per blocco (li crea `h3_chain.py`) |
| **ECO INPUT** | `inputs/` | copia dei prompt + copione usati (vedi "ECO DEGLI INPUT") |
| **ECO SCRIPT** | `scripts/` | copia degli script di lancio usati |

Procedura (in ordine):
1. **Scaffold**: `bash scripts/h3-film-new.sh <nome> [nblocchi] [secs] [img_partenza]`
   -> crea `outputs/<data>_film_h3_<nome>/` con copione+run+PLAN+prompts.
2. **Scrivi il copione** `H3_CHAIN.json`: blocchi da 8-14 s; il **primo** `mode: r2v` con `refs=[img]`
   (identity lock), **tutti gli altri** `mode: continuation` (ultimo frame + audio del precedente).
   Atti espliciti: `lora: nsfw_sexytime` + `sampler/scheduler: euler/beta`.
3. **Scrivi i prompt IR** (350-500 parole) e validali: `h3_prompt_ir.py --spec H3_CHAIN.json --all --check`.
4. **`bash run_film.sh check`** (no GPU) -> poi **`resume`** (GPU, `--skip-existing`). `watch` delega a `scripts/h3-watch.sh`; `status` legge lo stato locale senza toccare la GPU.
5. **Verifica** il montato: frame count (`ffprobe -count_packets`), stream audio, QA visiva.
6. **Consegna** `FILM_H3.mp4` (o `READY_TO_SEND:` via `h3-quick.sh` se è una clip singola).

Regola d'oro: **10 min = 600 s; 600/6 ≈ 100 blocchi** sulla Spark (`fasth3-distill` default). Se scegli 12 s/blocco scendi a ~50 blocchi ma alzi molto il rischio memoria. Non esiste "un video da 10 minuti in un colpo":
si fa a blocchi con continuita', si monta, si verifica. Ogni blocco e' resumable.

## Riproducibilita': l'ECO DEGLI INPUT negli outputs (OBBLIGATORIO)

Le fonti vive stanno in `film_specs/<titolo>/`; la **copia usata** va nella cartella degli output,
cosi' una produzione si spiega da sola e resta la prova di cosa l'ha generata. Un film senza eco
degli input non e' consegnabile.

| Dove | Cosa |
|---|---|
| `film_specs/<titolo>/` (fonte VIVA, in git) | `blockNN.txt` (prompt), `film.json` (copione: atti/cast/seed), `gen_*.sh`, `launch_*.sh` |
| `outputs/film_<titolo>/inputs/` | **copia** dei prompt + `film.json` usati |
| `outputs/film_<titolo>/scripts/` | **copia** degli script usati per lanciare |
| `outputs/film_<titolo>/logs/` | `gen.log` + report di verifica |
| `outputs/film_<titolo>/README.md` | manifest: cosa e' cosa, config, regola dei seed |
| `outputs/film_<titolo>/blockNN.{mp4,graph.json,scene.json}` | clip + grafo API esatto + manifest |

Regola: **niente script "usa-e-getta" fuori dagli outputs**. Se hai lanciato con uno script, quello
script va in `outputs/<produzione>/scripts/` (copia) *e* nella fonte viva. Gli script di
migrazione/patch una-tantum restano invece nel `trash/` della repo giusta.

## Memoria / anti-OOM (DGX Spark) - IMPORTANTE
Sulla Spark gira **`earlyoom`**: appena la memoria cala, lancia l'OOM-killer e ammazza processi. Lezione 2026-09-16
(un run `int8` 12 s/blocco e' morto dopo 2 blocchi). Contromisure, in ordine:

- **Preset per la memoria** (dal piu' leggero): `fasth3-distill` ~35 GB (4 step) > `nvfp4-fast` ~48 > `int8` ~76 > `parity-bf16` ~110. Sotto earlyoom **parti da `fasth3-distill`**.
- **Blocchi corti**: la memoria di decode scala col numero di frame -> **6 s/blocco** (149 fr) invece di 12 s (294 fr). 10 min = **100 blocchi**.
- **`oom_score_adj`**: i processi in background ereditano 1000 = primi bersagli, ma **NON puoi
  abbassare il tuo** da utente normale (`EPERM`: serve `CAP_SYS_RESOURCE`, misurato 2026-09-20).
  Gli script che fanno `echo -500 > /proc/self/oom_score_adj 2>/dev/null || true` falliscono in
  silenzio. Difese reali: **blocchi corti**, cache a pressione di RAM di ComfyUI, RAM liberata
  prima del run, e un supervisore che **riavvia il server** se `:8189` smette di rispondere.
- **Un motore per volta**: `bash scripts/h3-free-vram.sh --kill` ferma `llama-server`
  (~38 GB) e `:8188` (liberano ~15 GB); senza, `int8` (~76 GB) non entra nei 121 GB unificati.
- **Watchdog**: `bash scripts/h3-watch.sh <cartella_film>` -> se la catena muore e il film non e' completo, riprende da sola (resume).

Regola pratica 10 min: **`fasth3-distill` + 6 s/blocco -> ~4-5 h**, memoria stabile (~28 GB liberi).

## Preset (default `int8`)
| preset | DiT / encoder | GB | nota |
|---|---|---|---|
| `int8` (**default**) | pruned int8_convrot + qwen3vl int8 | ~76 | raccomandato Comfy-Org, tutto presente |
| `fasth3-distill` | int8 DiT + qwen3vl nvfp4 + LoRA FastH3 4-step | ~35 | distillazione terza parte, piu' veloce |
| `nvfp4-fast` | pruned nvfp4 + nvfp4 enc | ~48 | 4-bit |
| `parity-bf16` / `-lite` | bf16 | 110 / 144 | parita' con lo Space; **NON scaricato** (~tutta la RAM) |
| `fp8-fallback` | pruned fp8_scaled | ~81 | per GPU senza int8_convrot |

## Parametri di registrazione (invarianti)
- **Nessun CFG/negative** (`BasicGuider`): guidance-distilled.
- Default ufficiale: `res_multistep` / `simple`. **LoRA AfterMidnight NSFW -> forza `euler`/`beta`** (audio altrimenti rotto).
- `length` = `17n+5` (snap automatico da `--seconds`); canvas nativo 1344x768, 24 fps.
- **VAE audio DEVE restare fp32** (`minimax_h3_audio_vae_fp32.safetensors`).
- `--ref-image-size match` (veloce) | `max` (fedelta' identita', <=2048 lato corto).

## Output & consegna
- Output: `/home/jagones/ComfyUI/output/H3_*` (+ grafo `.json` con `--save-graph`).
- `scripts/h3-quick.sh ...` copia il risultato nel workspace e stampa `READY_TO_SEND: /abs/path`.
- **Mai** mandare file da `ComfyUI/output/`: solo il path di `READY_TO_SEND:`.

## Trappole note (imparate a spese nostre)
| Sintomo | Causa | Fix |
|---|---|---|
| `LoadImage: Custom validation failed` | il server H3 legge un'altra `input/` | `run_h3.sh` passa `--input-directory /home/jagones/ComfyUI/input` (dal 2026-09-15) |
| `Value not in list` su CLIPLoader | preset `parity-bf16` non scaricato | usare `--preset int8` (default) |
| `length` rifiutata | non e' `17n+5` | usare `--seconds` (snap automatico) |
| audio assente/rotto | VAE audio non fp32, o LoRA NSFW con sampler sbagliato | VAE fp32 + `euler`/`beta` |
| memoria insufficiente | due ComfyUI accesi insieme | spegnere `:8188` e `llama-server` per H3 |
| processo ucciso di notte / run muore a meta' (OOM) | `earlyoom` sulla Spark; il server H3 e' il processo piu' grosso = bersaglio n.1 | blocchi **6 s**; **liberare RAM** (`pkill -f llama-server`, `:8188` spento); supervisore con **riavvio del server** + resume. `oom_score_adj=-500` non e' praticabile da utente normale (`EPERM`) |
| run lungo riparte da ZERO dopo un crash | `--skip-existing` non implementato (ora si') | `run_film.sh resume` / `h3_chain.py --skip-existing` |

## Licenza
*MiniMax H3 Community License*: territorio applicabile **esclude EU/UK/Corea/USA** (vedi H3_RECIPE.md par.9).

## Riferimenti
- Ricetta: `diffusion-pipelines/film/docs/H3_RECIPE.md`
- Runner canonici: `comfyui-mcp/workflow_files/runners/h3_run.py`, `h3_chain.py`
- **Schema dei path** (skill -> ogni singolo path, Linux + Windows): `PATHS.md`
- Template ufficiali: `templates/` (copie di `_vendor/ComfyUI-templates/video_minimax_h3_*.json`)
- Doctor/install/fetch: `diffusion-pipelines/film/h3/{install_h3_comfy.sh,h3_doctor.sh,fetch_h3_models.sh,H3_MODELS.lock.json}`


## Film lunghi v2: MULTI-SHOT — il metodo ufficiale (VERIFICATO 2026-09-20)

> **Default per un film nuovo.** La catena `h3_turbo` (sezione sotto) resta valida ma e' il metodo a
> *inquadratura unica*: raccordi perfetti, film monotoni. Per un film VERO si usa questo.

**Principio**: non "una scena = una inquadratura"; si genera un **blocco da 4 shot con tagli
dichiarati nel prompt**, e si montano i blocchi.

| Parametro | Valore verificato |
|---|---|
| blocco | 12,25 s = **294 frame** (`17n+5`), **4 shot** (taglio ogni ~3 s) |
| comando | `h3_run.py --mode t2v --prompt-file blockNN.txt --length 294 --width 960 --height 544 --steps 6 --seed S --lora larry --out <out>.mp4` |
| prompt | formato ufficiale MiniMax: `[Shot 1] ...` (senza timestamp), poi `[Shot N] At MM:SS.mmm, ...` |
| dialogo | `<Subject N> (Sx)` + `<d>[English] ...</d>` — il modello PARLA (trascritto con Whisper) |
| concat | blocchi uniformi -> `ffmpeg -f concat -safe 0 -i list.txt -c copy` (niente trim, niente buco) |
| costo | **~505 s/blocco** su GB10 (`int8` + `larry` 6 step, 960x544) |
| 10 min | **49 blocchi x 4 shot = 196 shot**, ~6,2 h reali |

**Cosa e' stato misurato** (`video/h3_turbo/outputs/film_noir_full/noir_full.mp4`, 10:00.28,
44 blocchi consecutivi): **193 tagli reali** rilevati (`scene>0.25`) su 196 dichiarati;
**0/48 click audio** ai giunti fra blocchi; `C1 acc/vel` **OK su tutti i 48 giunti**; ~44 battute
di dialogo trascritte da Whisper in ordine narrativo. Ai giunti **fra blocchi** C0 basso e C2 alto
sono **ATTESI**: sono cambi di scena voluti (e' un montaggio, non un difetto).

**Trappole nuove**
- **NON riavviare il server H3 fra i blocchi**: il primo run paga il load, poi il ritmo resta
  ~67 s/step. Riavviarlo lo ripaga (misurato: 33 s/it subito dopo il load, non meglio).
- **Il tetto dei "12 s per blocco" del metodo `h3_turbo` NON vale qui**: 294 frame x 44 blocchi
  con `int8` sono girati con RAM stabile (`avail` 10-11 GB). Il vincolo e' la RAM *totale col
  modello caricato*, non i frame del singolo blocco.
- Il formato `[Shot N] At MM:SS.mmm` va **dichiarato nel prompt**: senza i timestamp i tagli non
  arrivano ai tempi voluti.
- Ogni blocco e' indipendente (stesso prompt style, seed diversi): si puo' **rifare un solo
  blocco** senza toccare gli altri. Mettere sempre il seed nel nome del lancio.

## Film lunghi: la catena VERIFICATA (`video/h3_turbo`) - continuita' C0/C1/C2

Per un film a scene concatenate NON usare `h3-chain.sh`: la catena verificata e' in
`diffusion-pipelines/video/h3_turbo/` (submodule git). Regole e trappole complete:
`film/docs/H3_RECIPE.md` **§12**. Varieta' d'azione: `diffusion-pipelines/film/docs/ACTION-GRAMMAR.md`.

| Cosa | Comando (Python: `/home/jagones/wan555/venv/bin/python3`) |
|---|---|
| shot list (camera score + action ladder) | `gen_film_spec.py --scenes N --seed0 S --title T --out film_specs/T.json` |
| dry-run, nessuna GPU | `make_film.py film_specs/T.json --dry-run` |
| run (idempotente, riusa le scene presenti) | `make_film.py film_specs/T.json` |
| + ricetta ricostruibile (`*.recipe.tar.gz`) | `make_film.py film_specs/T.json --bundle` |
| verifica C0/C1/C2/audio | `verify_junctions.py outputs/film_T/T.mp4 --frames <length-trim per scena>` |

Server richiesto: `bash /home/jagones/ComfyUI-H3/run_h3.sh` (ComfyUI-H3 `:8189`, acceso).

### Scala: tante scene piccole (anti-OOM)

La catena `h3_turbo` genera **una scena per volta**: la memoria di decode dipende solo dai frame
della singola scena (`17n+5`), NON dal totale. Quindi **N grande e' sicuro**, a patto che le scene
restino corte.

- **Lunghezza scena**: ~5-6,5 s (124 fr la prima; 158 fr le successive, di cui 22 di guida
  tagliati in montaggio -> 136 fr resi). NON allungare la scena per "fare meno blocchi": la
  memoria cresce col numero di frame (6 s = 149 fr ~28 GB liberi; 12 s = 294 fr = rischio OOM).
- **Un motore per volta**: `bash scripts/h3-free-vram.sh --kill` (ferma `llama-server` e `:8188`).
- **Reprendibile**: `make_film.py` e' idempotente (riusa le scene gia' presenti); dopo un crash
  rilanci lo stesso comando e riprende. `h3_supervise.py` / `scripts/h3-watch.sh` riavviano da soli.
- **RAM misurata** (`int8` + 106 scene, 2026-09-20): memoria **unificata** 121 GB, `used`
  113-117 GB, `avail` **7,8-11 GB** stabile (margine ~3x sul trigger di `earlyoom`, 2%).
  `oom_score_adj=-500` **non e' praticabile** da utente normale (`EPERM`): valgono blocchi
  corti + cache a pressione di RAM + supervisore che riavvia il **server**.
- **Misura prima di credere**: `make_film.py <spec> --dry-run` (no GPU) -> frame, numero scene, stime.

### Comandi operativi — un solo wrapper per caso (`scripts/h3-film.sh`)

```bash
bash scripts/h3-film.sh new    <titolo> <scene> [durata]   # spec + dry-run (nessuna GPU)
bash scripts/h3-film.sh run    <titolo>                    # libera RAM + server + run + supervisore
bash scripts/h3-film.sh status <titolo>                    # avanzamento
bash scripts/h3-film.sh verify <titolo>                    # C0/C1/C2 + audio sui giunti
bash scripts/h3-film.sh stop   <titolo>                    # ferma runner e supervisore
```

`h3-film.sh` incapsula l'intera catena: `gen_film_spec.py` -> `make_film.py --dry-run` ->
`make_film.py --bundle` -> `h3_supervise.py` (auto-resume **e riavvio del server** se `:8189`
muore). Prima del run libera la RAM con `scripts/h3-free-vram.sh --kill`.

Esempio 10 minuti: `bash scripts/h3-film.sh new mio_film 106 5.0` poi `... run mio_film`.

### Le 5 regole che decidono il risultato
1. **DUE tipi di taglio, da NON confondere (la regola che sblocca i film belli).**
   - **Taglio DENTRO una generazione = FORMATO UFFICIALE, e si DEVE usare.** Il multi-shot
     (`[Shot N] At MM:SS.mmm`) fa cambiare inquadratura, luogo e personaggio *dentro una sola
     passata*: il modello lo prevede, l'audio resta continuo (0 click misurati) e il film smette
     di essere monotono. **E' il default per un film nuovo** -> sez. "Film lunghi v2: MULTI-SHOT".
   - **Cambio di inquadratura FRA due generazioni = DISCONTINUITA'.** Concatenando due blocchi, il
     giunto e' un taglio non dichiarato: misurato, PSNR 8-12 dB contro p1 interno ~10 dB e `vel`
     al giunto 9-20x l'interno. **Fra blocchi** la varieta' viene dal MOVIMENTO DI CAMERA (camera
     score: una move continua, scala di campo che evolve di 1 step), non dal cambio di inquadratura.
2. **Si ancora una CODA MULTI-FRAME con la sua audio** (`--guide-clip`, K = 5/22/39 frame), non
   1 frame. Un frame vincola la posizione (C0) ma non la velocita' (C1): al taglio il moto puo'
   invertirsi o fermarsi (misurato: `vel` al giunto 0,25-0,49x l'interno).
3. **`--trim` vale ESATTAMENTE K**, mai `length - base`: lo snap `17n+5` aggiunge frame di
   contenuto vero e tagliarli apre un buco nella timeline.
4. **Azioni diverse per CLASSE** (13 classi A-M, >=3 slot di variazione, curva d'intensita' con
   contrasto). Senza l'action ladder il film e' "cammina + gira la testa" per 10 minuti.
5. **Anti-spawn.** L'oggetto nuovo appare perche' il CONTESTO lo invita (prior di affordance) e
   perche' la camera rivela spazio non definito. Contromisure nel prompt: inventario CHIUSO con
   cardinalita' ("one woman, one scooter"), l'oggetto DENTRO la frase dell'azione, clausola in
   positivo ("nothing enters or leaves, no new objects appear"), niente sostantivi-affordance
   ("crowds", "traffic" chiamano persone e auto). **Il negative prompt NON e' una difesa:**
   agisce in ritardo e "disegna per poi cancellare" (ECCV 2024).

### Criteri di accettazione (non dichiarare "fatto" senza questi)
| Livello | Metrica | Deve stare |
|---|---|---|
| **C0** contenuto | PSNR al giunto | sopra il **p1** interno |
| **C1** moto | `acc/vel` al giunto | sotto il **p99.9** interno |
| **C2** jerk | `jerk/acc` al giunto | sotto il **p99.9** interno |
| audio | salto `|x[n]-x[n-1]|` al giunto | sotto il p99.9 interno, **0 click** |

Flag emessi: `[cambio di contenuto: possibile TAGLIO o OGGETTO NUOVO]` quando `vel` al giunto e'
>3x la mediana interna; `[moto quasi fermo al taglio]` quando e' <0,35x.

### Trappole
- Il filtro `concat` di ffmpeg sbaglia di **1 frame con 3+ segmenti** (riconcilia durate audio/video
  non multiple intere del frame audio: 32000/24 = 1333,33 campioni). Trim **per clip** + `-c copy`.
- Le metriche C1/C2 vanno **normalizzate** (`acc/vel`, `jerk/acc`): senza, ogni taglio viene letto
  come rottura di moto.
- C0 va giudicato contro il **p1 interno**, non contro la media: con una camera in movimento la
  varianza interna e' alta e un giunto puo' finire sotto la media per caso.
- Un run "completo" si misura sul **numero di clip**, non sull'esistenza del file film.
- La cache di ComfyUI maschera i test di determinismo: serve `POST /free` prima del run.
