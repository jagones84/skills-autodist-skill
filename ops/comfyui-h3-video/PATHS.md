# comfyui-h3-video - SCHEMA DEI PATH (dove sta tutto)

**Entry point = questa skill.** Da qui si arriva a ogni pezzo della pipeline MiniMax-H3.
Due viste della STESSA cartella (share SMB):

- **Linux (canonica, dove girano gli agenti):** `/home/jagones/...`
- **Windows (per umani):** `Z:\...` = `\\192.168.1.37\HOME\...`  (quindi `Z:\` = `/home/jagones/`)

## 0. Percorso minimo (dalla skill al risultato)
1. **Gate**: `bash <skill>/scripts/h3-doctor.sh`  -> deve dire `0 FAIL, 0 WARN`
2. **Genera**: un blocco -> `bash <skill>/scripts/h3-run.sh --mode t2v --prompt-file p.txt --seconds 5`
   catena -> `bash <skill>/scripts/h3-chain.sh --spec <film>/h3_chain.example.json --dry-run`
3. **Consegna**: `<skill>/scripts/h3-quick.sh ...` -> stampa `READY_TO_SEND: <file>`

---

## 1. SKILL (entry point)  - root: `~/.openclaw/workspace/skills/comfyui-h3-video/`

| file | Linux | Windows (Z:) |
|---|---|---|
| procedura | `~/.openclaw/workspace/skills/comfyui-h3-video/SKILL.md` | `Z:\.openclaw\workspace\skills\comfyui-h3-video\SKILL.md` |
| system-prompt agente | `.../PROMPT.md` | `...\PROMPT.md` |
| layout | `.../README.md` | `...\README.md` |
| **questo schema** | `.../PATHS.md` | `...\PATHS.md` |
| gate | `.../scripts/h3-doctor.sh` | `...\scripts\h3-doctor.sh` |
| run 1 blocco | `.../scripts/h3-run.sh` | `...\scripts\h3-run.sh` |
| catena | `.../scripts/h3-chain.sh` | `...\scripts\h3-chain.sh` |
| server start/stop | `.../scripts/h3-server.sh` | `...\scripts\h3-server.sh` |
| run+consegna | `.../scripts/h3-quick.sh` | `...\scripts\h3-quick.sh` |
| template (copia) | `.../templates/video_minimax_h3_*.json` | `...\templates\video_minimax_h3_*.json` |
| puntatori | `.../reference/README.md` | `...\reference\README.md` |

## 2. CODICE (motori)  - `~/Repositories/comfyui-mcp/workflow_files/runners/`

| cosa | Linux |
|---|---|
| motore 1 blocco | `/home/jagones/Repositories/comfyui-mcp/workflow_files/runners/h3_run.py` |
| catena | `.../runners/h3_chain.py` |
| foley (video->audio) | `.../runners/vid2vid_mmaudio_foley.py` |
| confronto Wan2.2 | `.../runners/flf2v_run.py`, `flf2v_chain.py` |

## 3. TEMPLATE UFFICIALI  - `~/Repositories/comfyui-mcp/workflow_files/_vendor/ComfyUI-templates/`
`video_minimax_h3_t2v.json` · `..._i2v.json` · `..._r2v.json` · `..._multiframe_reference.json`

## 4. PESI  - `~/ComfyUI/models/`

| cosa | path |
|---|---|
| DiT int8 | `models/diffusion_models/minimax_h3_{fl2va,ref2va}_pruned_int8_convrot.safetensors` |
| text encoder | `models/text_encoders/qwen3vl_32b_minimax_h3_int8_convrot.safetensors` |
| VAE video/audio (audio **fp32**) | `models/vae/minimax_h3_{video_vae_fp16,audio_vae_fp32}.safetensors` |
| LoRA turbo / ref2v / FastH3 / NSFW | `models/loras/minimax_h3_*`, `fasth3_*`, `AfterMidnight_*` |
| lock (repo+rev+sha256) | `~/Repositories/diffusion-pipelines/film/h3/H3_MODELS.lock.json` |

## 5. INSTALL / DOCTOR / FETCH  - `~/Repositories/diffusion-pipelines/film/h3/`
`install_h3_comfy.sh` · `h3_doctor.sh` · `fetch_h3_models.sh` · `H3_MODELS.lock.json`

## 6. RICETTA / PROMPT / SPEC  - `~/Repositories/diffusion-pipelines/film/`
`H3_RECIPE.md` · `h3_prompt_ir.py` · `h3_chain.example.json`

## 7. SERVER (ComfyUI affiancato `:8189`)  - `~/ComfyUI-H3/`
`run_h3.sh` · `main.py` · `extra_model_paths.yaml` (pesi condivisi) · `.h3-pin` (v0.35.2) · `server.log`

## 8. ROUTING (la "lista dei WF")

| cosa | path |
|---|---|
| mappa di `workflow_files/` | `~/Repositories/comfyui-mcp/workflow_files/README.md` |
| routing dei grafi (:8188) + H3 | `~/Repositories/comfyui-mcp/workflow_files/graphs/README.md` |

## 9. OUTPUT e CARTELLE DI PRODUZIONE

| cosa | path |
|---|---|
| output grezzi del server H3 | `~/ComfyUI/output/H3_*`, `~/ComfyUI/output/MULTISHOT_*` |
| **produzione multi-shot (default)** | `diffusion-pipelines/video/h3_turbo/outputs/film_<titolo>/` |
| .. fonti VIVE (in git) | `diffusion-pipelines/video/h3_turbo/film_specs/<titolo>/` |
| .. prompt usati (**eco**) | `<produzione>/inputs/` |
| .. script usati (**eco**) | `<produzione>/scripts/` |
| .. log + verifiche | `<produzione>/logs/` |
| .. manifest della produzione | `<produzione>/README.md` |
| vecchia catena (Wan2.2 longform) | `~/ComfyUI/outputs/YYYYMMDD_film_<nome>/` |
| copie per Windows | `C:\Users\giova\Downloads\H3_test\` |

Layout di una produzione multi-shot (verificato, `film_noir_full`):
```
film_specs/<titolo>/          blockNN.txt  film.json  gen_<titolo>.sh  launch_<titolo>.sh  gen.log
outputs/film_<titolo>/        blockNN.mp4 + blockNN.graph.json (grafo API) + README.md
                              inputs/ (eco prompt+copione)  scripts/ (eco launcher)  logs/  sheet/
```

## 10. DOC DI BORDO
`~/ComfyUI/.agent/README.md` (par. 2b) · `~/ComfyUI/.agent/HANDOFF.md` (blocco H3 in cima)

## 11. ARCHIVIO / BACKUP
Target archivio storico: `~/Repositories/comfyui-mcp/workflow_files/_ARCHIVIO/` (quando presente/riattivato). I `.bak` locali della skill restano accanto ai file finche' il routing non e' collaudato.

---

## Layout di riferimento (2026-09-15)

`workflow_files/` (= `Z:\Repositories\comfyui-mcp\workflow_files\`)
```
workflow_files/
  README.md                mappa + catalogo motori video
  graphs/                  DATI: 14 grafi .json (API :8188) + README
  runners/                 CODICE: launcher + foley + _dead/
    run_wf.py quick-wf.sh  flf2v_run.py flf2v_chain.py  h3_run.py h3_chain.py
    launch_AIGEN_NSFW_FLUX_LONG.py launch_upscale_x2.py
    vid2vid_mmaudio_foley.py  concat_wan22_generic.sh  convert_ui_to_api_v3.py
  _vendor/                 terzi + ComfyUI-templates (video_minimax_h3_*.json)
  ref/                     riferimenti (Seko, Remix, default)
```

`diffusion-pipelines/image/` (motore immagini diffusers)
```
  img2img_qwen_image_diffusers.py     motore canonico (T2I + I2I)
  txt2img_qwen_image_diffusers.py     entrypoint txt2img (delega al motore)
  _caption_local.py  README.md
```

## Note di stato (2026-09-15)
- **Preset `int8` = default e completo**; `fasth3-distill` completo; `nvfp4-fast` manca `ref2va_pruned_nvfp4`; `parity-bf16/-lite` non scaricati.
- **Licenza** MiniMax H3 Community: territorio applicabile esclude EU/UK/Corea/USA.

