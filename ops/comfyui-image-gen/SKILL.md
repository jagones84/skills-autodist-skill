---
name: comfyui-image-gen
description: Single uncensored image creation and processing skill for local ComfyUI. Use it for generation, upscaling, background removal, image-to-image modification, long-prompt Flux Unchained NSFW, and Qwen-Image AIO NSFW (txt2img + edit).
---

# ComfyUI Image Creation And Processing - Canonical Workflow


## Pre-Flight Reading Checklist (workspace rules)

Before running any ComfyUI task, you MUST have read all of the following, in this order:

1. `~/.openclaw/workspace/AGENTS.md` - the "Pre-Flight Documentation Reading" rule
   (mandatory) and Skills-First Rule.
2. `~/.openclaw/workspace/MEMORY.md` - long-term curated memory (main session only).
3. `~/.openclaw/workspace/TOOLS.md` - local notes (DGX Spark, paths, venv rule).
4. `~/.openclaw/workspace/skills/comfyui-image-gen/SKILL.md` (this file) - the
   canonical operating procedure.
5. `~/.openclaw/workspace/skills/comfyui-image-gen/FLUX_LONG_PROMPT_GUIDE.md` - prompt
   authoring rules for Flux.
6. `~/.openclaw/workspace/skills/comfyui-image-gen/README.md` - skill layout.
7. `Z:/ComfyUI/.agent/PROCEDURES.md` - generic ComfyUI workflow rules.
8. `Z:/ComfyUI/.agent/workflow_catalog.md` and `workflows/` - per-workflow details.
9. `Z:/ComfyUI/.agent/_SKILL_openclaw_sync.md` - changelog of this skill.
10. `~/Desktop/QUICK COMMANDS/` (Linux, case-sensitive, SPACE) - canonical launchers
    (`start_comfy.sh`, `start_openclaw_withbrows.sh`, `Varie.txt`).
11. `~/start_comfyui_optimized.sh` only as a fallback - it sources `venv/bin/activate`.

Do NOT skip steps. Do NOT read source code of `comfyui-mcp` instead of this SKILL.md.

> **LAST VERIFIED**: 2026-09-15 20:00 (Europe/Rome) - 14 ComfyUI graphs in `workflow_files/graphs/`;
> diffusers pipelines in `Repositories/diffusion-pipelines/`; launcher `run_wf.py` live; H3 su `:8189` (skill `comfyui-h3-video`)
>
> **STRUTTURA `workflow_files/` (riordino 2026-09-15)**: `graphs/` = i grafi `.json` (**DATI**, ex `comfyui/`);
> `runners/` = **CODICE**/launcher;
> `_vendor/` = terzi + template ufficiali; `ref/` = riferimenti; `_ARCHIVIO/` = **ARCHIVIO UNICO** (lineage
> + superato, ex `_ARCHIVIO/` + `BACKUPS/`). Il motore immagini diffusers e il suo entrypoint txt2img
> stanno in `Repositories/diffusion-pipelines/image/`.
> **NSFW un-censored models confirmed working**: `perfectdeliberate_v60` (SDXL), `fluxunchained_unet_fp8` (Flux), `Qwen-Rapid-AIO-NSFW-v23` (Qwen-Image)
> **Smartphone preview stack** (added 2026-08-22): preview su altri dispositivi: `share_images_http.sh` (LAN); il tunnel Cloudflare e' in standby.
> **Pose-preservation recipes** (added 2026-08-23): Recipe D (vanilla 2511 + multiple-angles LoRA), Recipe E (two-pass hybrid), Recipe F (DiffSynth ControlNet depth).
> **Validated workflows** (added 2026-08-23 23:10): see "Workflow Catalog — ComfyUI graphs" section. Use `run_wf.py <short_name>` as universal launcher.
> **MUST VERIFY before declaring success** (added 2026-08-27, lesson from Jagones disaster): a ComfyUI job that exits the queue is NOT a successful generation. See "Output Verification (mandatory)" section below.

## Output Verification (mandatory — added 2026-08-27)

**REGOLA ASSOLUTA**: dopo ogni `run_wf.py` o `generate_and_send.py`, PRIMA di dichiarare "fatto" o "test passato" all'utente, devi SEMPRE verificare l'esito reale con i 4 check seguenti. Tutti e 4 devono passare.

### I 4 check obbligatori

```bash
# 1. history[prompt_id] deve riportare status_str="success" (NON solo queue idle)
curl -s http://127.0.0.1:8188/history/<prompt_id> | python3 -c "
import json, sys
h = json.load(sys.stdin)
for pid, e in h.items():
    s = e.get('status', {}).get('status_str')
    c = e.get('status', {}).get('completed')
    print(f'prompt_id={pid} status_str={s!r} completed={c}')
    if s != 'success':
        print('FAIL: ComfyUI non ha confermato success')
"

# 2. Il file generato deve esistere
ls -la /home/jagones/ComfyUI/output/<nome_file>.png

# 3. mtime del file deve essere > start_time della generazione
stat -c '%y' /home/jagones/ComfyUI/output/<nome_file>.png

# 4. file size > 0 bytes
test -s /home/jagones/ComfyUI/output/<nome_file>.png && echo "OK size" || echo "FAIL: file vuoto"
```

### Anti-pattern vietati

| Vietato | Perché |
|---------|--------|
| Dichiarare "test passato" basandosi solo sul fatto che lo script ha stampato "Generation complete!" | Lo script può aver ricevuto un Broken pipe da ComfyUI e aver mentito |
| Dichiarare "fatto" solo perché `ready_to_send` è stato scritto | `ready_to_send` viene scritto anche se il file è vecchio |
| Fidarsi di "queue idle" come prova di success | Job falliti escono dalla queue |
| Proporre la foto all'utente prima di aver fatto i 4 check | Genera hallucination di conferma (caso Jagones 2026-08-27) |

### Cosa scrivere all'utente in caso di fallimento

Se uno dei 4 check fallisce:
- **NON** dire "fatto" o "test passato"
- **NON** proporre la foto
- **DÌ** chiaramente: "Generazione FALLITA. Status: <X>. Verifico cosa è successo."
- Esegui diagnostica (`ss -tlnp | grep 8188`, log ComfyUI, modello caricato)
- Proponi fix prima di riprovare

Vedi `OPENCLAW_CLI_GUIDE.md` sezione 14 per il pattern completo di diagnosi LLM vs infrastructure.

## Anti-Loop Rule: Stop After 3 Same-Target Failures (added 2026-08-27)

**REGOLA ASSOLUTA**: se esegui 3 o più `tool_use` (exec, edit, fetch, ecc.) con lo **stesso obiettivo** (es. "verificare dove sta la foto", "leggere lo status del job", "trovare il file X") e nessuno dei 3 arriva a una risposta conclusiva → **FERMATI e rispondi all'utente**, NON continuare a investigare.

### Perché questa regola esiste

Caso Jagones 2026-08-27 10:06-11:22: il modello ha fatto **12+ `exec` consecutivi** sullo stesso obiettivo ("capire dove sta la foto non arrivata"). Thinking block iniziava sempre con "User's question: 'e dove sta la foto...'". Il modello ha:
1. Chiamato `stat` sul file → non c'era
2. Chiamato `ls` sulla cartella output → non c'era
3. Chiamato `find` ovunque → niente
4. Chiamato `curl /queue` per vedere se c'era job in corso
5. Chiamato `grep` su log
6. ... altri 7 `exec` identici nel pattern

Risultato: 1h 16min di log spazzatura, ~40 messaggi parziali a Telegram (msg 15899-15938), 0 risposte utili all'utente.

### Pattern di riconoscimento

Se ti accorgi che il tuo ultimo `tool_use` ha **la stessa semantica** dei 2 precedenti (es. "controlla file X", "leggi log Y", "verifica status Z"), stai looppando. Fermati.

**Esempi di loop da riconoscere SUBITO**:
- 3 `exec stat/ls/find` per "cercare un file" senza mai dire all'utente "il file non c'è"
- 3 `curl` su endpoint ComfyUI diversi per "verificare se ComfyUI risponde"
- 3 `edit` con stesso `old_string` che falliscono con "Could not find edits[N]" → fermati, l'`old_string` non matcha
- 3 `fetch` su URL simili per "leggere la documentazione X"

### Cosa fare quando riconosci il loop

```text
STOP. Thinking check: ho già fatto 3+ tool_use sullo stesso obiettivo?
  ├─ SÌ → Rispondi all'utente con:
  │       - Cosa ho scoperto finora (fattuale, no speculazione)
  │       - Cosa NON sono riuscito a verificare e perché
  │       - Proposta di prossima azione concreta
  │       Esempio: "Non trovo il file `foto.png` né in /output né in /workspace.
  │                 ComfyUI sembra down (curl /history/b062e561 → ENOENT).
  │                 Posso riavviare ComfyUI?"
  │
  └─ NO → Procedi con il prossimo tool_use, ma se arriva un altro fallimento sullo stesso target, FERMATI.
```

### Anti-pattern vietati

| Vietato | Perché |
|---------|--------|
| `exec stat file.png` → fail → `exec ls /output` → fail → `exec find / -name file.png` → fail → `exec stat file.png` di nuovo | Loop investigativo infinito. Dopo il 2° fail, fermati e rispondi. |
| `edit "foo bar" → "foo baz"` → fail "Could not find edits[0]" → `edit "foo bar" → "foo baz"` di nuovo | Stesso `old_string` identico: se fallisce una volta, non matchera' una seconda. Rileggi il file e usa il testo esatto. |
| `curl /queue` → fail → `curl /queue` di nuovo entro 30s | ComfyUI non si ripara da solo in 30s. Indaga la causa root (modello caricato? OOM? KSampler broken?) |
| 5+ `exec` consecutivi senza produrre un `text` finale per l'utente | Sintomo classico di loop. Rispondi prima di fare il 6°. |

### Nota tecnica

OpenClaw 2026.7.1-2 **non ha** un parametro `max_tool_calls_per_turn` esposto. L'unica mitigazione è prompt engineering (questa regola). Se in futuro OpenClaw aggiungesse un parametro tipo `toolLoopCap` o `maxStepsPerTurn`, valutare di integrarlo qui.

Vedi anche `OPENCLAW_CLI_GUIDE.md` sezione 14.3 (pattern LLM: loop investigativo, hallucination di conferma, tentativo fix senza verifica).

## Workflow Catalog — ComfyUI graphs (PRIMARY ENTRY POINT)

All live-tested, known-good workflows live in a single folder. Use the universal launcher `run_wf.py` to run ANY of them with one consistent command:

```bash
# See all 14 workflows:
python3 ~/.openclaw/workspace/skills/comfyui-image-gen/scripts/run_wf.py list

# Launch any wf (the launcher auto-detects prompt node, image node, KSampler):
python3 ~/.openclaw/workspace/skills/comfyui-image-gen/scripts/run_wf.py <short_name> "<prompt>" 1024 1024 out.png
#   with source image:
python3 ~/.openclaw/workspace/skills/comfyui-image-gen/scripts/run_wf.py <short_name> --image /path/src.png "<prompt>" 1024 1024 out.png
#   with prompt file (for >1500 char NSFW):
python3 ~/.openclaw/workspace/skills/comfyui-image-gen/scripts/run_wf.py flux_long --file /path/prompt.txt 1024 1024 out.png
```

Wrapper:

```bash
~/.openclaw/workspace/skills/comfyui-image-gen/scripts/quick-wf.sh <short_name> "<prompt>" 1024 1024 out.png
```

### Routing Table (pick by intent)

| Intent | short_name | Source wf file | Typical time |
|---|---|---|---|
| Long explicit NSFW txt2img (>500 char prompt) | `flux_long` | `AIGEN_NSFW_FLUX_LONG_api.json` | 150-180s |
| NSFW img2img, faithful pose, Recipe H winner | `nsfw_community_h` | `img2img_nsfw_community_cfg1_d085_shift3_api.json` | 12-20s |
| NSFW img2img, full denoise, max transformation | `nsfw_l_d100` | `img2img_nsfw_lightning4_2511_d100_api.json` | 10-18s |
| NSFW img2img, light edit (denoise 0.55) | `nsfw_l_d055` | `img2img_nsfw_lightning4_2511_d055_api.json` | 8-15s |
| SFW img2img, Qwen AIO single-file | `sfw_aio_v11` | `img2img_sfwclad_aio_v11.json` | 10-15s |
| NSFW gfix variant cfg 2.0 denoise 0.6 | `nsfw_gfix_l10d60c2` | `_recovered_AIGEN_gfix_l10d60c2.json` | 8-15s |
| NSFW gfix variant cfg 2.5 denoise 0.6, long prompt | `nsfw_gfix2` | `_recovered_AIGEN_gfix2.json` | 8-15s |
| NSFW Lightning-4 full denoise (alt name) | `nsfw_l_d100_recovered` | `_recovered_AIGEN_LIGHTNING4_NSFW.json` | 10-18s |
| NSFW vanilla Qwen community 20 steps no LoRA | `nsfw_community_qw` | `_recovered_AIGEN_QW_COMMUNITY_NSFW.json` | 30-60s |
| SFW AIO Qwen edit, denoise 0.65 | `sfw_aio_recovered` | `_recovered_AIGEN_QWEN_SFW_AIO.json` | 10-15s |
| Legacy txt2img SDXL `perfectdeliberate_v60` | `txt2img_perfect_delib` | `txt2img_perfect_deliberate.json` | 30-60s |
| Resize to 512x512 lanczos | `util_resize` | `img2img_resize.json` | 2-3s |
| Remove background (LayerMask RemBgUltra) | `util_removebg` | `img2img_removebg.json` | 5-10s |
| Upscale 4x with `4x-UltraSharp.pth` | `util_upscale` | `img2img_upscale.json` | 8-15s |

### Per-workflow parameter sheet

| short_name | Model | LoRA | Sampler | CFG | Steps | Denoise | Notes |
|---|---|---|---|---|---|---|---|
| `flux_long` | `fluxunchained_unet_fp8` (fp8_e4m3fn) | SloppyToppy 0.7 + SidewaysDeepthroat 0.75 | euler / sgm_uniform | 1.0 | 28 | 1.0 | **Mandatory trigger prefix** below. Long prompt 1500-2000 chars. |
| `nsfw_community_h` | `qwen_image_edit_2511_fp8_e4m3fn` | Qwen-Image-Edit-2511-Lightning-4steps str 1.0 (model only) | euler / simple | 1.0 | 4 | 0.85 | **WINNER** (Recipe H). ModelSamplingAuraFlow shift=3 + CFGNorm strength=1 |
| `nsfw_l_d100` | `qwen_image_edit_2511_fp8mixed` | Qwen-Image-Edit-2511-Lightning-4steps str 1.0 (model+clip) | euler / simple | 1.0 | 4 | 1.0 | Full denoise. FluxKontextMultiReferenceLatentMethod (index_timestep_zero) |
| `nsfw_l_d055` | `qwen_image_edit_2511_fp8mixed` | Qwen-Image-Edit-2511-Lightning-4steps str 1.0 | euler / simple | 2.5 | 4 | 0.55 | Light edit, preserve composition |
| `sfw_aio_v11` | `Qwen-Rapid-AIO-SFW-v11` (single-file, LoRA baked) | (baked) | euler / simple | 1.0 | 4 | 0.50 | SFW. ImageScaleToTotalPixels 2.5MP. 1024x1024 latent. |
| `nsfw_gfix_l10d60c2` | `qwen_image_edit_2511_fp8mixed` | Lightning-4 str 1.0 | euler / simple | 2.0 | 4 | 0.6 | ReferenceLatent via FluxKontextMultiReferenceLatentMethod |
| `nsfw_gfix2` | `qwen_image_edit_2511_fp8mixed` | Lightning-4 str 1.0 | euler / simple | 2.5 | 4 | 0.6 | Same family, long prompt variant |
| `nsfw_l_d100_recovered` | `qwen_image_edit_2511_fp8mixed` | Lightning-4 str 1.0 | euler / simple | 1.0 | 4 | 1.0 | Twin of `nsfw_l_d100` (extracted from PNG) |
| `nsfw_community_qw` | `qwen_image_edit_2511_fp8mixed` | (none) | euler / simple | 2.5 | 20 | 1.0 | Vanilla community recipe, no Lightning, slow (20 steps) |
| `sfw_aio_recovered` | `Qwen-Rapid-AIO-SFW-v11` | (baked) | euler / simple | 1.0 | 4 | 0.65 | SFW AIO edit (PNG-extracted) |
| `txt2img_perfect_delib` | `perfectdeliberate_v60` | (none) | euler / normal | 8.0 | 20 | 1.0 | Legacy SDXL Danbooru-tag style. 1408x1048 latent. |
| `util_resize` | (none) | (none) | n/a | n/a | n/a | n/a | ImageScale lanczos to 512x512 |
| `util_removebg` | `LayerMask: RemBgUltra` | (none) | n/a | n/a | n/a | n/a | detail_range=8, black=0.01, white=0.99, process_detail=true |
| `util_upscale` | `4x-UltraSharp.pth` | (none) | n/a | n/a | n/a | n/a | ImageUpscaleWithModel, 4x |

### Mandatory trigger prefix for `flux_long`

Without this block at the start of the prompt, both LoRAs silently disengage and the output loses the desired anatomy/positioning:

```
slptp, ballsxdeep, deepthroat, tongue out, throatfuck, throat bulge, balls deep, slobbery, drooling, gagging,
```

### BLOOM detection (mandatory post-run check)

If the output is a flat green/olive monochrome mosaic, it is a BLOOM failure. Verify with PIL:

```python
from PIL import Image
import numpy as np
img = np.array(Image.open(out).convert("RGB"))
std = img.std()
mean = img.mean()
bloom = std / max(mean, 1)
colors = len({tuple(p) for p in img.reshape(-1, 3).tolist()})
# WIN conditions: std > 30, bloom > 0.30, colors > 10000
print(f"std={std:.1f}  bloom={bloom:.3f}  colors={colors}")
```

If any of `std < 30`, `bloom < 0.30`, or `colors < 10000`, the run is a **BLOOM failure**: do not send. Re-run with a different seed, lower denoise, or switch to `nsfw_community_h`.

### Where the workflows live (single source of truth)

- **ComfyUI graph workflows (JSON)** live in `/home/jagones/Repositories/comfyui-mcp/workflow_files/graphs/`.
- `run_wf.py` reads ONLY from that folder (no fallback to root).
- `flux_and_send.py` (legacy Flux long-prompt script) points at `/home/jagones/Repositories/comfyui-mcp/workflow_files/graphs/AIGEN_NSFW_FLUX_LONG_api.json`.
- **Video e audio NON vivono qui.** Vedi il riquadro *Video e audio — NON competono a questa skill* e la skill `comfyui-h3-video`. Questa skill copre solo immagini.

## Scope

This is the single image skill currently enabled for ComfyUI work.

Use it for:

- generating a new image from a prompt
- upscaling an existing image
- removing the background from an existing image
- modifying or restyling an existing image (perfectdeliberate SDXL OR Qwen-Image AIO NSFW)
- long descriptive NSFW generation with Flux Unchained (separate pipeline, see below)
- **Qwen-Image AIO NSFW** (txt2img + image-edit, fully un-censored, see dedicated section)

Do not invent a separate ad-hoc image workflow outside this skill unless you are explicitly debugging ComfyUI itself.

## One Allowed Path Per Job Type

Do not manually reconstruct the workflow with separate `curl`, `ls`, `cp`, and `message` steps unless you are explicitly debugging the skill itself.

For generation, normal use MUST go through exactly one command:

```bash
python3 /home/jagones/.openclaw/workspace/skills/comfyui-image-gen/scripts/generate_and_send.py "<prompt>" <width> <height> generated.png
```

Equivalent wrapper:

```bash
/home/jagones/.openclaw/workspace/skills/comfyui-image-gen/scripts/quick-gen.sh "<prompt>" <width> <height> generated.png
```

The script already does all of this:

- submit to ComfyUI
- wait for completion
- resolve the correct output for this run
- copy the image into `/home/jagones/.openclaw/workspace/`
- print a final `READY_TO_SEND: /absolute/path`

## Upscaling Existing Images

For upscaling, normal use MUST go through exactly one command:

```bash
python3 /home/jagones/.openclaw/workspace/skills/comfyui-image-gen/scripts/upscale_and_send.py \
  /absolute/source/image.png upscaled.png 4x-UltraSharp.pth
```

Equivalent wrapper:

```bash
/home/jagones/.openclaw/workspace/skills/comfyui-image-gen/scripts/quick-upscale.sh \
  /absolute/source/image.png upscaled.png 4x-UltraSharp.pth
```

The script already does all of this:

- upload the source image to ComfyUI correctly
- submit a known-good upscale workflow
- wait for completion
- resolve the correct output for this run
- copy the image into `/home/jagones/.openclaw/workspace/`
- print a final `READY_TO_SEND: /absolute/path`

Required tool behavior:

1. Run the canonical upscale script once.
2. Read the final `READY_TO_SEND:` line.
3. Call the `message` tool once with that workspace path.
4. Only after a successful send, reply with the confirmation text.

Important:

- `4x-UltraSharp.pth` is the current quality-first default.
- `RealESRGAN_x4plus.pth` is acceptable later if installed and a more conservative photo-style result is wanted.
- Never use `resize_image`, `get_image`, `mcporter`, or handwritten `/prompt` JSON for normal upscale requests.
- Never pass a workspace absolute path directly into a raw `LoadImage` node.

## Removing Backgrounds

For background removal, normal use MUST go through exactly one command:

```bash
python3 /home/jagones/.openclaw/workspace/skills/comfyui-image-gen/scripts/remove_bg_and_send.py \
  /absolute/source/image.png removed_bg.png
```

Equivalent wrapper:

```bash
/home/jagones/.openclaw/workspace/skills/comfyui-image-gen/scripts/quick-remove-bg.sh \
  /absolute/source/image.png removed_bg.png
```

The script already does all of this:

- upload the source image to ComfyUI correctly
- submit a known-good background removal workflow
- wait for completion
- resolve the correct output for this run
- copy the image into `/home/jagones/.openclaw/workspace/`
- print a final `READY_TO_SEND: /absolute/path`

Important:

- This path uses the installed `LayerMask: RemBgUltra` node from `ComfyUI_LayerStyle`.
- The `RMBG-1.4` model may need to exist locally before the first run is fast.
- Never use the old `remove_background_workflow.json` path unless you are explicitly debugging the MCP repo itself.

## Modifying Existing Images

For image-to-image modification, normal use MUST go through exactly one command:

```bash
python3 /home/jagones/.openclaw/workspace/skills/comfyui-image-gen/scripts/modify_and_send.py \
  /absolute/source/image.png "your edit prompt" modified.png 0.55
```

Equivalent wrapper:

```bash
/home/jagones/.openclaw/workspace/skills/comfyui-image-gen/scripts/quick-modify.sh \
  /absolute/source/image.png "your edit prompt" modified.png 0.55
```

The script already does all of this:

- upload the source image to ComfyUI correctly
- run a known-good uncensored img2img workflow based on `perfectdeliberate_v60.safetensors`
- wait for completion
- resolve the correct output for this run
- copy the image into `/home/jagones/.openclaw/workspace/`
- print a final `READY_TO_SEND: /absolute/path`

Important:

- Use lower denoise values like `0.25-0.45` when preserving the original image closely matters.
- Use medium denoise values like `0.5-0.7` for normal edits and restyles.
- Use higher denoise only when the user explicitly wants a strong transformation.

## Qwen-Image AIO NSFW (txt2img + image-edit, un-censored)

The vanilla Qwen-Image and Qwen-Image-Edit-2511 checkpoints have NSFW filters
baked-in (confirmed from upstream docs, wikiwiki.jp, CSDN, grokipedia - they
block nudity, explicit anatomy, and sexual content). The vanilla GGUF Q4_K_M
quantizations inherit these filters and produce sanitized outputs.

**The un-censored solution is `Qwen-Rapid-AIO-NSFW-v23.safetensors`** by Phr00t
on HuggingFace. This is a single 28.4GB checkpoint that has the NSFW un-censoring
+ accelerator + LoRA stack baked-in. No GGUF, no separate text encoder, no
manual LoRA wiring.

**Live verification 2026-08-22 23:12**: prompt "naked adult woman standing in
a modern bathroom shower..." produced a 1.2MB explicit output in 15s. The Read
tool itself rejected the file as "non-compliant content" - empirical proof
that the model is genuinely un-censored.

**Architecture** (one workflow, one node set):
- `CheckpointLoaderSimple` → loads AIO NSFW v23 (model + clip + vae in one go)
- `EmptyLatentImage` or `LoadImage` (for edit)
- `TextEncodeQwenImageEditPlus` → handles clip + prompt + vae + up to 3 reference images
- `KSampler` (euler_ancestral, scheduler=beta, steps=4-6, cfg=1.0, denoise=0.75 for edit / 1.0 for txt2img)
- `VAEDecode` + `SaveImage`

**Workflow files** (already wired in `comfyui-mcp/workflow_files/`):
- `default_workflow.json` - Qwen AIO NSFW txt2img (replaces vanilla Qwen Q4_K_M)
- `img2img_workflow.json` - Qwen AIO NSFW image-edit (denoise=0.75)

**Prompt rules for Qwen AIO**:
- Qwen text encoder handles natural prose well (unlike Danbooru-tag SDXL).
- 4-6 steps is enough - the AIO is a turbo/distilled variant.
- `cfg=1.0` is mandatory. Higher values cause artifacts.
- For edits, describe the target state ("make the image sunset-lit with warm
  orange tones") rather than the action ("add sunset").
- Up to 3 reference images can be passed to `TextEncodeQwenImageEditPlus.image1/2/3`.

**Path for Qwen NSFW jobs** (current canonical):
- The MCP `comfyui-mcp` server exposes these as the default `generate` and
  `image_edit` operations. Submit a normal generation/edit request and it
  will route to the AIO NSFW workflow.

Important:
- **Never switch back to vanilla Qwen-Image Q4_K_M** for NSFW - the output
  is sanitized. The AIO v23 is the only Qwen-family checkpoint on this
  machine that produces un-censored output.
- The 28.4GB checkpoint fits in the 124GB DGX VRAM with ~95GB headroom.
- Vanilla `TextEncodeQwenImageEdit` (without the `Plus` suffix) lacks
  reference-image support - always use the Plus variant.

## Flux Unchained NSFW (Long Prompt Pipeline)

For explicit NSFW generation that benefits from long descriptive prompts
(anatomy, position, fluids, lighting, camera angle), use the dedicated Flux
Unchained pipeline. It is **not** the same as `generate_and_send.py` - the
prompt format, the LoRA trigger block, and the long-prompt budget are
different.

For long, explicit, prose-style NSFW generation, normal use MUST go through exactly one command:

```bash
python3 /home/jagones/.openclaw/workspace/skills/comfyui-image-gen/scripts/flux_and_send.py \
  --prompt "<prompt with trigger prefix>" 1024 1024 output_name.png
```

Equivalent wrapper:

```bash
/home/jagones/.openclaw/workspace/skills/comfyui-image-gen/scripts/quick-flux.sh \
  --prompt "<prompt with trigger prefix>" 1024 1024 output_name.png
```

For very long prompts (>1500 chars) read from a text file:

```bash
python3 /home/jagones/.openclaw/workspace/skills/comfyui-image-gen/scripts/flux_and_send.py \
  --file /absolute/path/prompt.txt 1024 1024 output_name.png
```

The script already does all of this:

- free VRAM via ComfyUI `/free` before submission (Flux UNet ~12GB + LoRAs + T5-XXL FP8 ~9GB)
- load `/home/jagones/Repositories/comfyui-mcp/workflow_files/graphs/AIGEN_NSFW_FLUX_LONG_api.json`
- validate prompt length against the T5-XXL FP8 budget (warn >1500 chars, hard cap 2000)
- inject the prompt into node 7 (positive CLIPTextEncode)
- submit to ComfyUI via HTTP
- wait for completion (typical 150-180s for 1024x1024)
- resolve the output from `/history/<prompt_id>`
- copy the image into `/home/jagones/.openclaw/workspace/`
- print a final `READY_TO_SEND: /absolute/path`

**Mandatory trigger prefix** (LoRAs silently disengage without it):

```
slptp, ballsxdeep, deepthroat, tongue out, throatfuck, throat bulge, balls deep, slobbery, drooling, gagging,
```

The full prompt reference (structure, negative prompt, worked example, failure-mode table) is in `FLUX_LONG_PROMPT_GUIDE.md` next to this SKILL.md.

**Long prompt budget** (T5-XXL FP8 does NOT truncate - verified 2026-08-22):

| Metric | Soft limit | Hard limit |
|---|---|---|
| Characters | ~1500 | 2000 |
| Approx tokens | ~380 | ~600 |

Important:

- Always start the prompt with the trigger block above. Without it the LoRAs
  are inactive and the output looks like vanilla Flux.
- Do NOT pass comma-tag soup only - the Flux text encoder prefers natural
  prose after the trigger block.
- Default size `1024x1024`. The workflow overrides width/height in node 9
  (EmptyLatentImage) for any reasonable size.
- Default step count is 28 (set in the workflow). Override with `--steps N`.
- This pipeline is uncensored by design - the negative prompt is tuned to
  keep anatomy correct, not to remove explicit content.
- Do not use this path for SFW / casual generation - the default
  `generate_and_send.py` is faster and lighter.

## Video e audio — NON competono a questa skill

Questa skill copre **immagini** (generazione, upscale, background removal, modifica, workflow).
Tutto cio' che e' **video e audio** vive in:

- skill OpenClaw **`comfyui-h3-video`** (MiniMax-H3: blocco singolo, multi-shot, catena film);
- progetto `Z:\Repositories\diffusion-pipelines\` -> `video/README.md`,
  `video/README-longform.md`, `video/h3_turbo/README.md` (continuita' C0/C1/C2, action ladder,
  anti-spawn);
- ricetta del motore: `diffusion-pipelines\film\H3_RECIPE.md`.

Le sezioni che stavano qui (WAMU 20 s, `longform_wan555.py`, film di 10 minuti a 4 stage,
Wan2.2 I2V, `diffusion-pipelines/film/docs/RECIPE.md` flf2v, MiniMax-H3) documentavano script **non
presenti in questa skill** ed erano la causa di ~13 riferimenti a file inesistenti. Estratte
il 2026-09-19.

## Preview su dispositivi esterni (LAN) — il tunnel e' in standby

Per vedere un PNG generato su un altro dispositivo NON usare `file://` (vale solo sulla
macchina che ha il filesystem) ne' `http://<lan-ip>:8188` (ComfyUI ascolta su `127.0.0.1`).
Usa il server LAN:

| Script | Scopo |
|---|---|
| `share_images_http.sh` | Avvia `python3 -m http.server 8765` su `~/ComfyUI/output` (solo LAN). |
| `share_images_stop.sh` | Ferma il server via pidfile. |

```bash
bash /home/jagones/.openclaw/workspace/skills/comfyui-image-gen/scripts/share_images_http.sh
```

Stampa `LAN URL`: `http://192.168.1.38:8765/<filename>` — funziona da qualunque dispositivo
sulla stessa WiFi/LAN. Android 9+ blocca il cleartext HTTP sui domini pubblici (non su IP di
LAN). Su 4G/5G serve HTTPS: il **tunnel Cloudflare** (`quick-share.sh`,
`share_images_tunnel.sh`, `install_cloudflared.sh`, binario `bin/cloudflared` = 36 MB) e' stato
**estratto in standby** in `~/.openclaw/workspace/_standby/comfyui-image-gen/delivery/`
(motivo: trasporto generico, non generazione, e pubblicava `~/ComfyUI/output` su URL pubblico
senza autenticazione). Per riattivarlo: riporta i 3 script in `scripts/`, il binario in `bin/`
e reinstalla con `install_cloudflared.sh`.

## Showing Images Inline in Chat (PureShowWidget on smartphone)

When the user is on a smartphone via Trae Work, plain `https://...` URLs
in the chat text are NOT clickable and `Read`-loaded images are NOT shown
to them. To put an actual image inline in the chat so the user can see
it on the phone, use the `PureShowWidget` tool with a tiny HTML widget
that embeds the image as an `<img>` tag pointing at the LAN preview URL.

Pattern:

```html
<style>
  .card { background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 12px; }
  .card img { width: 100%; height: auto; display: block; background: #000; border-radius: 6px; }
  .title { color: #e6edf3; font: var(--weight-medium) var(--text-title) var(--font-sans); margin: 0 0 4px 0; }
  .sub   { color: #7d8590; font: var(--text-caption) var(--font-sans); margin: 0 0 6px 0; }
  .prompt{ color: #c9d1d9; font: var(--text-code) var(--font-mono); white-space: pre-wrap; margin: 0; }
</style>
<div data-dynamic-ui-widget data-template="<short-id>" class="card">
  <h2 class="title">Human-readable title</h2>
  <p class="sub">One-line summary: model, denoise, steps, size, time.</p>
  <pre class="prompt">Full prompt that generated the image, verbatim.</pre>
  <img src="http://<lan-ip>:8765/<filename>.png" alt="description">
</div>
```

Always include:
- the **title** (so the user knows what they are looking at),
- the **prompt verbatim** in `<pre>` (so the user can audit prompt
  adherence and reuse it),
- the **img** tag pointing at the LAN preview URL.

The widget renders in the Trae Work chat on both desktop and mobile,
including NSFW content (verified 2026-08-23 with Qwen AIO NSFW img2img).
Per la preview via telefono sulla stessa LAN basta `share_images_http.sh`. Su 4G/5G serve
il tunnel Cloudflare, in standby (vedi sezione "Preview su dispositivi esterni (LAN)"):
riattivalo perche' il browser del telefono possa scaricare la `<img>`.

## Prompt-Adherence Check (img2img only)

Read tool blocks NSFW PNGs ("non-compliant content"). To verify that an
NSFW img2img generation actually rendered the requested scene elements,
generate a **paired SFW twin**: same source image, same workflow, same
parameters, but the prompt is rewritten to remove only the NSFW tokens
(keep every visual element identical). Read the SFW twin and grade each
requested element by hand.

Implemented in `tests/flux_staging/test_nsfw_i2i_v2.py`. The script
produces both files and dumps a JSON result at `/tmp/i2i_v2_result.json`
with the prompts, the output filenames, and the element checklist.

Verified 2026-08-23 00:08 - 4/5 elements rendered correctly in the SFW
twin (golden marble, red wine, rose petals, candles). The "silk robe"
element was ignored by Qwen AIO NSFW, which still produced a
semi-undressed subject. This is consistent with the model's
un-censored behaviour, not a workflow bug.

**Caveat - "over-shoot" in the SFW twin (2026-08-23)**: when the SFW twin
is generated with the *same* NSFW model (Qwen-Rapid-AIO-NSFW-v23), the
SFW softener in the prompt (e.g. "silk robe", "wearing a dress") is
ignored and the model still pushes a semi-undressed subject. To get a
faithful adherence probe, run the SFW twin with a **vanilla
Qwen-Image-Edit-2509/2511** checkpoint or a GGUF Q4_K_M that respects
clothing, and keep `Qwen-Rapid-AIO-NSFW-v23` for the actual NSFW
generation. Both must run with the same `img2img_workflow.json` and
same denoise/steps for the comparison to be meaningful.

**Full caption + adherence widget pattern** (use when the user wants
the prompt verbatim AND the adherence check side-by-side):

```html
<style>
  .card { background: #1a1a20; border: 1px solid #2a2a32; border-radius: 10px; margin-bottom: 14px; overflow: hidden; }
  .head { padding: 8px 12px; background: #20202a; border-bottom: 1px solid #2a2a32; display: flex; justify-content: space-between; }
  .tag-nsfw { background: #5a1a1a; color: #ff8a7a; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 700; }
  .tag-sfw  { background: #1a3a2a; color: #8affaa; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 700; }
  .body { padding: 12px; }
  .body img { width: 100%; max-width: 720px; display: block; margin: 0 auto 10px; border-radius: 6px; background: #000; }
  pre.prompt { background: #14141a; border-left: 3px solid #c97a4a; padding: 10px; font: 11.5px ui-monospace, monospace; color: #c8c8d0; white-space: pre-wrap; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th, td { padding: 6px 8px; border-bottom: 1px solid #2a2a32; text-align: left; }
  .ok { color: #6ab04c; font-weight: 700; } .warn { color: #d6a93d; } .bad { color: #d6533d; }
</style>
<!-- A) NSFW card -->
<div class="card">
  <div class="head"><b>A) NSFW output</b><span class="tag-nsfw">NSFW</span></div>
  <div class="body">
    <img src="http://<lan-ip>:8765/<nsfw_filename>.png">
    <pre class="prompt"><nsfw_prompt_verbatim></pre>
  </div>
</div>
<!-- B) SFW twin card -->
<div class="card">
  <div class="head"><b>B) SFW twin (adherence probe)</b><span class="tag-sfw">SFW-CHECK</span></div>
  <div class="body">
    <img src="http://<lan-ip>:8765/<sfw_filename>.png">
    <pre class="prompt"><sfw_prompt_verbatim></pre>
  </div>
</div>
<!-- C) Adherence table -->
<div class="card">
  <div class="head"><b>C) Element-by-element adherence</b></div>
  <div class="body">
    <table>
      <thead><tr><th>Requested</th><th>Rendered</th><th>Verdict</th></tr></thead>
      <tbody>
        <tr><td>...</td><td>...</td><td class="ok">PASS</td></tr>
        ...
      </tbody>
    </table>
  </div>
</div>
```

This is the canonical "show me the image + the prompt + did the model
actually do what I asked" output. Use it for every NSFW img2img test
where the user asks "is it correct?" or "where is the adherence check?".

### img2img Recipe Cards (live-verified 2026-08-23)

These are the **known-good starting points** for any img2img test on
this DGX. Pick one, do not re-derive from scratch.

**A. Source-preserving (preserves pose, body, camera) - preferred default**
- Model: `Qwen-Rapid-AIO-NSFW-v23.safetensors` (28.4GB, Phr00t)
- Denoise: **0.45 - 0.55** (NEVER 0.65+ unless you want to re-pose)
- Steps: 10
- Sampler/sched: `euler_ancestral` / `beta`
- Prompt must explicitly include: `maintain the same pose, same camera
  angle, same body posture from the source image` - this is the lever
  that stops the model from re-posing the subject.
- Failure mode if 0.65: model treats the prompt as a fresh txt2img and
  re-positions the subject freely (see `AIGEN_QWEN_NSFW_I2I_00003_`).

**WARNING (2026-08-23, AIO NSFW v23 tilt)**:
AIO NSFW v23 + low denoise (0.50 or 0.55) + ANY prompt = **CATASTROPHIC
FAIL**. The model goes into internal conflict (LoRA NSFW baked-in wants
to render a naked body, the prompt wants to preserve the source pose,
the low denoise forces it to follow the source too closely) and the
output becomes an abstract green/white diagonal pattern with no human
subject. Verified 3 times:
- `AIGEN_QWEN_NSFW_I2I_00005_.png` (denoise 0.50, verbose prompt) - FAIL
- `AIGEN_QWEN_NSFW_I2I_00006_.png` (denoise 0.50, verbose SFW) - FAIL
- `AIGEN_QWEN_NSFW_I2I_00007_.png` (denoise 0.55, simplified prompt) - FAIL
- `AIGEN_QWEN_NSFW_I2I_00008_.png` (denoise 0.55, simplified SFW) - FAIL

**HARD RULE**: `Qwen-Rapid-AIO-NSFW-v23` works for img2img ONLY at
denoise 0.65+. Below 0.65 it is unusable. For source-preserving edits
you MUST use vanilla `Qwen-Image-Edit-2509/2511` FP8 (Recipe C) or
ControlNet OpenPose (Recipe B). Recipe A is therefore not safe with
AIO NSFW for source-preserving edits.

**B. Pose-locked (when denoise MUST be high for scene change)**
- Model: vanilla `Qwen-Image-Edit-2509/2511` FP8 (NOT AIO) + LoRA
  `qwen_image_union_diffsynth_lora.safetensors` (Comfy-Org) with an
  OpenPose preprocessing of the source image.
- Strength 1.0 = pose locked. 0.7 = guided, small bits can change.
  0.3 = hint, composition drifts.
- Source: `Comfy-Org/Qwen-Image-DiffSynth-ControlNets` (canny, depth,
  inpaint) or `qwen_image_union_diffsynth_lora` for pose/lineart/etc.
- This is the *only* way to keep the subject's exact pose while
  changing the scene heavily.

**C. SFW adherence probe (for testing what an NSFW generation would
have rendered, without triggering the over-shoot)**
- Model: vanilla `Qwen-Image-Edit-2509/2511` FP8 (NOT AIO NSFW).
  AIO NSFW ignores soft-clothes ("silk robe") and still pushes
  semi-nude, which makes the probe useless.
- Same denoise / steps / sampler as the NSFW run.
- Same prompt structure, only the NSFW tokens are removed (replace
  "nude / wet body" with "wearing a silk robe" or similar).
- Read tool will accept the SFW output. Grade it element by element
  and infer what the NSFW version likely did.

**D. Vanilla Qwen-Edit-2511 + multiple-angles LoRA (the working source-preserving recipe, 2026-08-23)**
- Model: `qwen_image_edit_2511_fp8_e4m3fn.safetensors` (xms991 mirror, ~20GB)
  OR `qwen_image_edit_2511_bf16.safetensors` (Comfy-Org, ~40GB).
  The 2511 base is the *only* one that respects `qwen-image-edit-2511-multiple-angles-lora`.
  The 2509 base does NOT support this LoRA.
- LoRA stack (apply in this order, each at `LoraLoaderModelOnly` with `strength_model=1.0`):
  1. `Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors` (str 1.0, 850MB) → 4-step sampling
  2. `qwen-image-edit-2511-multiple-angles-lora.safetensors` (str 0.5-0.8, 295MB) → identity lock for pose/angle
- Other nodes required (ComfyUI native, no custom nodes):
  - `UNETLoader` → qwen_image_edit_2511_fp8_e4m3fn
  - `CLIPLoader` → `qwen_2.5_vl_7b_fp8_scaled.safetensors`, type=`qwen_image`
  - `VAELoader` → `qwen_image_vae.safetensors`
  - `ModelSamplingAuraFlow` → shift=3.11 (Qwen-Image default)
  - `CFGNorm` → strength=1.0
  - `FluxKontextMultiReferenceLatentMethod` → method=`index_timestep_zero` (this is what makes joint text+image conditioning work; without it the image is mostly ignored)
  - `ImageScaleToTotalPixels` → megapixels=2.5, method=lanczos
  - `TextEncodeQwenImageEditPlus` → joint encode text + image
  - `KSampler` → steps=4 (Lightning), cfg=1.0, sampler=`euler`, scheduler=`simple`, denoise=0.50
- Denoise sweet spot for source-preserving: **0.40-0.55**. Below 0.40 the model
  does nothing visible. Above 0.60 the pose starts drifting. At 0.65+ it
  re-poses freely (same as AIO).
- Multiple-angles LoRA trigger phrases: plain language like "keep the same
  pose, keep the same camera angle" — no Chinese triggers required, the
  LoRA was trained on English captions. Per the runcomfy.com / morphic.com
  docs, the LoRA also responds to "rotate the camera 90°", "top-down view",
  "switch to wide-angle" etc. when you actually want a re-pose.
- Verified element-by-element result (2026-08-23, run in `test_nsfw_i2i_vanilla.py`):
  6/6 elements rendered correctly in the SFW twin (pose preserved, marble,
  wine, petals, candles, silk robe).

**E. Two-pass hybrid (when you need both pose preservation AND NSFW content)**
This is the right answer when neither AIO NSFW at low denoise (Recipe A,
broken) nor vanilla 2511 SFW (Recipe D, no NSFW) is enough.
- **Pass 1 (NSFW un-censor, 2026-08-23)**: `Qwen-Rapid-AIO-NSFW-v23` at
  denoise 0.75-0.85, steps 6, on the original source. Pose WILL change but
  the NSFW content + scene elements (marmo, vino, petali, candele) are
  rendered correctly. Produces the NSFW intermediate.
- **Pass 2 (pose lock, SFW)**: vanilla `Qwen-Image-Edit-2511` FP8 +
  multiple-angles LoRA at denoise 0.30-0.40, prompt "keep the same pose
  and same camera angle as the image, just refine the body proportions
  to match the source". The vanilla model's strength is joint conditioning
  (it re-uses the NSFW content from pass 1 because the NSFW intermediate
  goes into `TextEncodeQwenImageEditPlus.image1`), but it LOCKS the pose
  with the multiple-angles LoRA. The output keeps the NSFW content of
  pass 1 AND the pose of the source.
- Caveat: the joint conditioning means vanilla Qwen 2511 will, in pass 2,
  refuse to render *new* explicit content beyond what pass 1 produced. The
  pass-1 image already has the nudity baked in pixel-by-pixel, so this
  is not a problem — the pose lock just happens on top.
- This pattern is a TODO (2026-08-23, not yet run live). Test once the
  2511 base is downloaded.

**F. DiffSynth ControlNet (when you need absolute structural lock, e.g.
outfit swap on a moving subject)**
- Model: `qwen_image_edit_2511_fp8_e4m3fn` + the three official Comfy-Org
  control patches in `ComfyUI/models/model_patches/`:
  - `qwen_image_depth_diffsynth_controlnet.safetensors` (depth — locks pose + camera)
  - `qwen_image_canny_diffsynth_controlnet.safetensors` (canny — locks outlines)
  - `qwen_image_inpaint_diffsynth_controlnet.safetensors` (inpaint — locks a masked area)
- Native node: search "qwen" in ComfyUI node menu → `Qwen-Image DiffSynth ControlNets`
  → drop in a `Model Patcher Loader` and pick depth / canny / inpaint.
- Strength semantics (per aistudynow.com):
  - **1.0** = structure is locked. Pose, framing, axes all stay. Only
    style / lighting / texture change.
  - **0.7** = guided. Big shapes match, small details (e.g. background
    houses) can transform.
  - **0.3** = hint. Composition feels similar but drifts a lot.
- For pure pose preservation: depth, strength 1.0, processor=`Depth v2`.
- This path is the *only* one that fully decouples pose from content.
  When you must re-style the subject (e.g. change outfit) AND keep the
  exact same body position, this is the right tool. Recipe D (multiple
  angles LoRA) is faster and lighter, Recipe F is heavier but more rigid.

## Qwen LoRA Specialistiche (Recipe D + LoRA esterne, 2026-08-23 17:00)

**Naming convention WF (FIX 2026-08-23 17:00)**: tutti i WF in `comfyui-mcp/workflow_files/` usano nomi self-esplicativi `img2img_<azione>_<modello>[_param].json` o `txt2img_<modello>.json`. La funzione si legge dal nome (es. `img2img_upscale.json` = upscale, `img2img_resize.json` = resize, `img2img_removebg.json` = remove background, `txt2img_perfect_deliberate.json` = legacy txt2img SDXL).

**Vietato**: nomi tipo `qwen_<funzione>_api.json` o `img2img_qwen_<azione>_<modello>_<denoise>_api.json` (troppo generici, "qwen" ripetuto, "_api" inutile).

### 6c.1 — `img2img_sfwclad_qwen2511_hrp10.json` (Recipe D + HRP_10 LoRA) ❌ FAIL v1 → `_ARCHIVIO/v1_lora_silenti/`

Hyper-Realistic Portrait LoRA (prithivMLmods, 225MB, scaricata da HuggingFace).

**Path ORIGINALE**: `comfyui-mcp/workflow_files/img2img_sfwclad_qwen2511_hrp10.json` → ora in `_ARCHIVIO/v1_lora_silenti/`

**Modelli richiesti**:
- Checkpoint: `qwen_image_edit_2511_fp8_e4m3fn.safetensors` (20GB, 3 file)
- CLIP: `qwen_2.5_vl_7b_fp8_scaled.safetensors`
- VAE: `qwen_image_vae.safetensors`
- LoRA: `models/loras/hyper_realistic_portrait/HRP_10.safetensors` (225MB)
- LoRA Lightning 4-steps: `Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors` (850MB)
- Multi-Angles LoRA: **DISABLED** (str 0.0) in questo WF

**Parametri v1**:
- Denoise: 0.50 · Steps: 4 (Lightning) · CFG: 1.0 · HRP_10 strength: 1.0
- Trigger: `hyper-realistic portrait`

**❌ FAIL**: MAE=4.0/255 vs Unblur_10, MAE=3.7 vs Multi-Angles, PSNR=30-32dB → le 3 immagini sono praticamente identiche. **Causa**: Lightning 4-step + LoRA esterne (str 1.0) = conflitto, la LoRA Lightning comprime 50 step in 4 e i suoi pesi dominano, le altre LoRA vengono minimizzate.

### 6c.2 — `img2img_sfwclad_qwen2511_unblur10.json` (Recipe D + Unblur_10 LoRA) ❌ FAIL v1 → `_ARCHIVIO/v1_lora_silenti/`

Unblur-Upscale LoRA (prithivMLmods, 225MB, 138⭐, scaricata da HuggingFace).

**Path ORIGINALE**: `comfyui-mcp/workflow_files/img2img_sfwclad_qwen2511_unblur10.json` → ora in `_ARCHIVIO/v1_lora_silenti/`

**Parametri v1**:
- Denoise: 0.50 · Steps: 4 (Lightning) · CFG: 1.0 · Unblur_10 strength: 1.0
- Trigger: `unblur and upscale`

**❌ FAIL**: stesso motivo sopra (LoRA silenti, MAE=4.0/4.3 vs altre).

### 6c.3 — `img2img_sfwclad_qwen2511_multiangle.json` (Recipe D vanilla + Multi-Angles LoRA) ❌ FAIL v1 → `_ARCHIVIO/v1_lora_silenti/`

Multi-Angles LoRA (Fonedo, 281MB, 96 posizioni camera, preserva posa/angolo/proporzioni).

**Path ORIGINALE**: `comfyui-mcp/workflow_files/img2img_sfwclad_qwen2511_multiangle.json` → ora in `_ARCHIVIO/v1_lora_silenti/`

**Parametri v1**:
- Denoise: 0.50 · Steps: 4 (Lightning) · CFG: 1.0 · Multi-Angles strength: 0.6
- Trigger: `preserve the exact pose, camera angle, and subject proportions from the source image`

**❌ FAIL**: stesso motivo sopra (LoRA silenti, MAE=3.7/4.3 vs altre). Il Multi-Angles str 0.6 dovrebbe essere la più visibile delle 3, ma la differenza vs le altre è comunque sotto la soglia.

### ⚠️ 6c.4 — FIX proposto (Test 13/14/15 in arrivo)

**Causa root**: Lightning 4-step (str 1.0) + LoRA esterne (str 1.0) = conflitto di pesi LoRA. La Lightning comprime 50 step in 4 e i suoi pesi dominano il sampling, le altre LoRA vengono scalate a zero.

**Fix candidato** (Opzione B):
- **Rimuovere Lightning LoRA** dal pipeline
- Steps: **20** (no Lightning)
- Sampler/sched: `euler` / `simple`
- Denoise: 0.50
- CFG: 1.0
- LoRA esterna str: **1.0** (sola LoRA attiva)

**Workaround Opzione A** (se Lightning è necessario per velocità):
- Lightning str: **0.5** (non 1.0)
- LoRA esterna str: **1.2**
- Steps: **8** (Lightning + extra)

**Verifica pre-PASS obbligatoria**: per ogni test, scaricare gli N output e calcolare MAE/PSNR via PIL+numpy. Soglia: MAE > 5/255 tra LoRA diverse = LoRA hanno effetto, altrimenti FAIL di nuovo.

**Comando verifica** (template):
```bash
python3 -c "
from PIL import Image; import numpy as np, os
files = {'a':'/path/a.png', 'b':'/path/b.png', 'c':'/path/c.png'}
imgs = {k: np.array(Image.open(p).convert('RGB')) for k,p in files.items()}
for la,lb in [('a','b'),('a','c'),('b','c')]:
    d = np.abs(imgs[la].astype(int)-imgs[lb].astype(int))
    print(f'{la} vs {lb}: MAE={d.mean():.2f}  PSNR={20*np.log10(255/np.sqrt((d**2).mean())):.2f}dB')
"

## 7. PRE-PASS VERIFICATION PROTOCOL (MANDATORY — added 2026-08-23 17:35)

**PRINCIPIO**: non si dichiara MAI PASS su un test senza aver completato TUTTI gli step di questa checklist. Bug documentato: i Test 10/11/12 sono stati dichiarati PASS basandosi solo su verifica config/workflow, ma la verifica pixel-level (PIL+numpy MAE/PSNR) ha rivelato che le 3 immagini erano praticamente identiche → FAIL.

**Quando applicare**: OGNI test che produca un output immagine confrontabile con un altro (recipe-vs-recipe, LoRA-vs-LoRA, param-vs-param, source-vs-output). NON applicare a singolo output one-shot dove non c'è "confronto" (es. un singolo upscale).

### 7.1 Checklist obbligatoria (7 step, TUTTI obbligatori)

```
□ Step 1: VERIFICA CONFIG (minimo, NON sufficiente)
   - Workflow JSON caricato correttamente
   - Parametri (denoise, CFG, steps, LoRA str) corretti
   - Trigger phrase presente nel prompt
   - Tutti i modelli referenziati esistono su Spark

□ Step 2: VERIFICA BINARIA
   - File output esiste, dimensione > 1MB
   - SHA256 registrato
   - HTTP 200 dal preview server LAN (per il widget)
   - MTime registrato

□ Step 3: VERIFICA PIXEL-LEVEL OGGETTIVA (NUOVA, OBBLIGATORIA)
   - Comando: scaricare output via scp in output_preview/
   - Lanciare verify_diff.py con PIL+numpy
   - Registrare: MAE medio, PSNR, pixel_diversi(%), max_diff, std
   - Se confronto multi-LoRA/multi-param: soglia MAE > 5/255 = LoRA hanno effetto
   - Se MAE < 5 e LoRA dovrebbero differire → FAIL

□ Step 4: SELF-REVIEW VISIVO
   - TENTATIVO Read tool sull'output (può essere bloccato dal filtro)
   - Se bloccato (atteso per source NSFW + Qwen 2511): OK, procedi
   - Includi sempre nel report: "Read tool blocked" o "visual: PASS" con dettagli

□ Step 5: SAMPLE WIDGET ALL'UTENTE (SEMPRE)
   - Mostrare SEMPRE l'output via PureShowWidget inline (anche se Read OK)
   - L'utente deve poter giudicare visivamente
   - Includere almeno 1 widget per test

□ Step 6: VERIFICA SE OUTPUT RISPETTA PROMPT
   - Conta gli elementi chiave del prompt presenti nell'output
   - Se prompt ha 5 elementi e output ne rispetta 3/5 → nota "3/5 element"
   - Se elemento critico mancante (es. "cream silk blouse" non presente) → FAIL

□ Step 7: VERDETTO FINALE + USER ACK
   - Solo se tutti i 6 step precedenti PASS → verdict = PASS
   - Se uno qualsiasi step FAIL → verdict = FAIL con motivazione
   - Mostrare verdict all'utente e CHIEDERE conferma esplicita
   - Solo DOPO ack utente → spostare in /home/jagones/Repositories/comfyui-mcp/workflow_files/graphs/ e marcare come validato
```

### 7.2 Script template di verifica (da copiare in `tests/flux_staging/<nome_test>/verify.py`)

```python
"""Verify pixel-level per un test. Da lanciare DOPO il test, PRIMA del verdict PASS.
Usage: python3 verify.py
Exit code 0 = PASS pixel-level, 1 = FAIL.
"""
from PIL import Image
import numpy as np
import sys
from pathlib import Path

# CONFIG: lista output da confrontare (per LoRA test, lista multi-LoRA)
OUTPUTS = {
    "test_a": "/path/to/AIGEN_<recipe>_<variante_a>_00001_.png",
    "test_b": "/path/to/AIGEN_<recipe>_<variante_b>_00001_.png",
    "test_c": "/path/to/AIGEN_<recipe>_<variante_c>_00001_.png",
}
# Soglie
MAE_THRESHOLD = 5.0       # > 5 = OK, < 5 = LoRA silenti
PSNR_THRESHOLD = 35.0     # > 35 dB = identiche, < 35 = distinte

def main():
    imgs = {k: np.array(Image.open(p).convert("RGB")) for k, p in OUTPUTS.items()}
    fail = False
    for la, lb in [(la, lb) for la in OUTPUTS for lb in OUTPUTS if la < lb]:
        diff = np.abs(imgs[la].astype(int) - imgs[lb].astype(int))
        mae = diff.mean()
        mse = (diff ** 2).mean()
        psnr = 20 * np.log10(255.0 / np.sqrt(mse)) if mse > 0 else float("inf")
        pct = (diff.sum(axis=2) > 5).mean() * 100
        verdict = "OK" if mae > MAE_THRESHOLD else "FAIL (LoRA silenti)"
        print(f"  {la:10s} vs {lb:10s}: MAE={mae:6.2f}  PSNR={psnr:5.2f}dB  diff%={pct:5.2f}%  -> {verdict}")
        if mae < MAE_THRESHOLD:
            fail = True
    print()
    if fail:
        print("VERDICT: FAIL pixel-level (LoRA silenti o config errata)")
        sys.exit(1)
    else:
        print("VERDICT: PASS pixel-level (LoRA hanno effetto distinguibile)")
        sys.exit(0)

if __name__ == "__main__":
    main()
```

### 7.3 Anti-pattern vietati (causa del bug 2026-08-23 17:35)

- ❌ **Dichiarare PASS basandosi solo su config/workflow** (es. "nodi corretti, parametri corretti, output generato 2.6MB, timing OK") → è la causa del bug dei Test 10/11/12
- ❌ **Considerare timing + size output come prova di PASS** → se 3 LoRA diverse danno tutte ~5min e ~2.5MB, è SINTOMO che sono identiche (non prova di PASS)
- ❌ **Verificare solo se il file esiste** (size > 0, 200 OK) → banale
- ❌ **Mostrare il widget senza riportare metriche oggettive** → l'utente deve poter verificare i numeri, non solo fidarsi del visual
- ❌ **Verdetto PASS prima del sample widget + ack utente**

### 7.4 Pattern obbligatorio (causa del fix)

- ✅ **Sempre** SHA256 + size + MTime di ogni output
- ✅ **Sempre** MAE/PSNR/pixel_diversi calcolati via PIL+numpy
- ✅ **Sempre** mappa di diff amplificata 4x se ci sono confronti
- ✅ **Sempre** widget con sample output (anche se Read tool lo blocca)
- ✅ **Sempre** element-by-element grading del prompt (n/N elementi rispettati)
- ✅ **Sempre** chiedere ack utente PRIMA di marcare /home/jagones/Repositories/comfyui-mcp/workflow_files/graphs/

## Test Report Format (Canonical Output For Every Test)

**This is the mandatory output shape for EVERY test result** that the
user asks to be shown. Confirmed working pattern (2026-08-23 user
approval: "piu o meno come ora bravissimo! Questo e il modo").

A test report MUST contain all of these blocks, in this order, as a
single `PureShowWidget` call (or, if the test has no images, as a
markdown block in chat):

1. **Title + one-line sub** — what was tested, model/denoise/steps/size/time.
2. **Self-review block** — the assistant MUST inspect the output
   itself (read every image with the `Read` tool, look at the SFW twin
   if NSFW, examine dimensions, sizes, etc.) BEFORE showing the result
   to the user. No blind "I generated X" claims. If `Read` is blocked
   by NSFW, the assistant uses a SFW twin to verify and grades each
   element by hand. The block states "Assistant self-review: N/M
   elements verified" with a per-element table.
3. **Results table** — pass/fail per element, color-coded (green/yellow/red).
4. **Images inline** — `<img>` tags pointing at the LAN preview URL (`http://<lan-ip>:8765/`).
5. **Caption for every image** — prompt verbatim in `<pre>`, params in sub.
6. **Diagnosi / verdict** — if anything failed, the assistant states
   what failed, why, and the fix proposed. No silent "yeah it works".
7. **Preview server state** — the assistant reminds to run
   `share_images_stop.sh` when the test session is done.

**Self-review protocol (mandatory)**:

```
for each test:
  1. run the workflow via ComfyUI API
  2. read the output file with the Read tool
  3. if Read rejects NSFW: run SFW twin (same params, no NSFW tokens)
     and grade the SFW twin element-by-element
  4. if Read succeeds: grade the actual output element-by-element
  5. only then show the result to the user, with the grading visible
```

**What "self-review" means in practice** (concrete checklist for
img2img NSFW):
- every requested visual element is actually rendered (marmo, vino,
  petali, candele, abbigliamento, posa)
- the output dimensions match what the workflow specifies
- the output file size is reasonable (>500KB usually = real content)
- the prompt is not truncated (T5-XXL has 256+ token headroom for Flux,
  Qwen AIO has its own tokenization)
- the denoise is consistent with the visual change vs the source

**Anti-patterns (forbidden)**:
- "I generated the image, here it is" without grading
- only showing the image without the prompt
- skipping the SFW twin on NSFW
- not stating the failure / not proposing a fix
- not stopping the preview server when done

**Template** (use the inline `PureShowWidget` form, copy from the
sections "Showing Images Inline in Chat" and "Full caption + adherence
widget pattern" above and combine: header card + A card + B card +
C card with table + verdict card).

## Verified 2026-08-22 (live tests on DGX Spark)

| Job | Script | Result |
|---|---|---|
| txt2img SFW (apple) | generate_and_send.py | OK 30s - perfectdeliberate_v60 |
| upscale 4x (apple) | upscale_and_send.py | OK 20s - 4x-UltraSharp.pth |
| img2img modify (apple) | modify_and_send.py | OK - denoise 0.55 |
| **NSFW TEST SUITE 5/5** | see tests/run_nsfw_suite.py | **PASS** 4min 35s total |
| - TEST 1: SDXL NSFW anime (Danbooru tags) | generate_and_send.py | OK 45s - 768x1024 perfectdeliberate_v60 |
| - TEST 2: Upscale 4x NSFW | upscale_and_send.py | OK 20s - 3072x4096 |
| - TEST 3: Modify NSFW (cambio outfit) | modify_and_send.py | OK 35s - denoise 0.5 |
| - TEST 4: Remove bg NSFW | remove_bg_and_send.py | OK 10s - RGBA con alpha |
| - TEST 5: Flux Unchained NSFW (long prompt + LoRA) | AIGEN_NSFW_FLUX_LONG_test.py / flux_and_send.py | OK 170s - 1024x1024 fluxunchained_unet_fp8 + 2 LoRA |
| **QWEN AIO NSFW** (default_workflow + img2img_workflow) | comfyui-mcp direct | **OK 91s + 147s** - Qwen-Rapid-AIO-NSFW-v23 (28.4GB) |
| - Qwen AIO NSFW txt2img SFW | default_workflow.json | OK 91s - 1024x1024 - masterpiece prompt |
| - Qwen AIO NSFW img2img SFW | img2img_workflow.json | OK 147s - 1024x1024 - denoise 0.75 |
| - Qwen AIO NSFW txt2img EXPLICIT (shower scene) | test_nsfw_aio.py | OK 15s - 1.2MB - **Read tool rejected file as non-compliant (proof of un-censoring)** |

**Runner NSFW test suite**: `/home/jagones/ComfyUI/tests/run_nsfw_suite.py`
Riesegue tutti i 5 test in sequenza con monitoraggio coda ComfyUI. Log: `~/.openclaw/workspace/test_nsfw_suite.log`

## Alternative Checkpoints (already installed on DGX)

The skill defaults to perfectdeliberate_v60.safetensors. All NSFW-ready, no extra download needed:

| Checkpoint | Style | Use for |
|---|---|---|
| perfectdeliberate_v60.safetensors | Anime/illustration, Danbooru tags | Default. Best for anime NSFW |
| iniverseMixSFWNSFW_realXLV1.safetensors | Realistic, NSFW | Real persons NSFW |
| xenogasmNSFWSemiReal_v5.safetensors | Semi-real, NSFW | Hybrid realistic |
| prefectiousXLNSFW_v10.safetensors | Anime NSFW | Pony/Illustrious hybrid |
| novaAnimeXL_ilV150.safetensors | Anime | Anime SFW/light NSFW |
| perfectionAmateurILXL_33.safetensors | Amateur realistic | Amateur scenes |
| illustrij_v20.safetensors | Illustrious style | Plain Danbooru tags |
| omnigenxlNSFWSFW_v10.safetensors | General NSFW/SFW | Versatile |
| ultrarealFineTune_v1.safetensors | Hyper-realistic | Photography style |
| z_image_bf16.safetensors | Z-Image Turbo | New arch, very long prompts |
| fluxunchained_unet_fp8.safetensors | Flux Unchained NSFW (FP8) | Long explicit prompts - use `flux_and_send.py` |

**Flux Unchained is a separate pipeline** - use the dedicated `flux_and_send.py`
script and `AIGEN_NSFW_FLUX_LONG_api.json` workflow. See the "Flux Unchained
NSFW (Long Prompt Pipeline)" section above for the mandatory trigger prefix
and long-prompt budget.

## Non-Negotiable Rules

- Never send media directly from `/home/jagones/ComfyUI/output/`.
- Only send the path returned by `READY_TO_SEND:`.
- Never hardcode a Telegram `chat_id`.
- Never announce "ecco l'immagine" before the `message` tool returns success.
- If `message` fails, do not retry the same bad path again.
- If no reliable active target is available, return the workspace file path instead of guessing.

## Prompt Writing Rules (checkpoint-conformant)

The default checkpoint (`perfectdeliberate_v60.safetensors`) is a Danbooru-tag-style model. It follows short comma-separated tag lists well and ignores long narrative prose. Before submitting ANY generation or modification request:

1. If the user gave a narrative sentence or paragraph, rewrite it into a compact tag list before calling the script. Do not pass raw narrative prose to these checkpoints.
2. Tag-list format rules:
   - Short phrases separated by commas; no full sentences, no connectors like "while", "who", "that".
   - Order matters: subject/pose first, then action detail, then environment, then lighting/style at the end.
   - Keep it under ~35 tags / ~400 characters. More dilutes attention instead of adding fidelity.
   - Include exactly one explicit quality anchor near the front, e.g. `masterpiece, best quality`, plus one style anchor at the end, e.g. `photorealistic` or `film still`.
   - For explicit scenes name the act literally in tags (`deep throat job`, `face close-up`, `tongue visible`, `saliva dripping`) - never imply it with narrative context.
   - Add 2-4 negative anchors only if supported by the workflow's negative prompt field (e.g. `blurry, lowres, extra limbs, watermark`).
3. Preserve the user's intent exactly when compressing: every concrete element they asked for must survive as a tag. Drop adjectives that carry no visual content (`very`, `incredible`, `amazing`).
4. If the user explicitly provides a ready-made tag list, use it as-is without rewriting.

Example rewrite:
- User prose: "a cinematic scene where she kneels and takes him fully into her mouth while he pulls her hair"
- Submitted tags: `1girl, solo face focus, kneeling, deep throat job, man standing over her, hand pulling hair back, tongue visible, saliva dripping, bedroom, night, city lights bokeh background, red lamp light, photorealistic, film still, masterpiece, best quality`

**Flux Unchained is the exception** to the tag-list rule. It uses long
descriptive prose (~1500 chars) starting with a 7-tag LoRA trigger block.
See `FLUX_LONG_PROMPT_GUIDE.md` for the full reference.

## Default Behavior

- Default checkpoint: `perfectdeliberate_v60.safetensors`
- Default size: `768x1024` unless the user asks otherwise
- Rewrite prompts per Prompt Writing Rules before submission; never pass narrative prose to the checkpoint
- Prefer small dimensions only when the user explicitly asks for speed
- Treat this as an uncensored local image skill unless the user explicitly asks for a safer style

## Required Execution Pattern

1. Run the canonical script once for the requested job type.
2. Read the final `READY_TO_SEND:` line.
3. Call the `message` tool once with that workspace path.
4. Only after a successful send, reply with the confirmation text.

Example:

```bash
python3 /home/jagones/.openclaw/workspace/skills/comfyui-image-gen/scripts/generate_and_send.py \
  "two roosters fighting in a dramatic battle scene, feathers flying, intense combat pose, detailed digital art" \
  512 384 generated.png
```

Expected tail output:

```text
SOURCE_IMAGE: /home/jagones/ComfyUI/output/rooster_fight_small_00001_.png
WORKSPACE_IMAGE: /home/jagones/.openclaw/workspace/generated.png
READY_TO_SEND: /home/jagones/.openclaw/workspace/generated.png
```

Then send:

- `action: "send"`
- `media: "/home/jagones/.openclaw/workspace/generated.png"`
- use the active inbound runtime target when needed by the environment

Upscale example:

```bash
python3 /home/jagones/.openclaw/workspace/skills/comfyui-image-gen/scripts/upscale_and_send.py \
  /home/jagones/.openclaw/workspace/generated.png upscaled.png 4x-UltraSharp.pth
```

Remove background example:

```bash
python3 /home/jagones/.openclaw/workspace/skills/comfyui-image-gen/scripts/remove_bg_and_send.py \
  /home/jagones/.openclaw/workspace/generated.png removed_bg.png
```

Modify image example:

```bash
python3 /home/jagones/.openclaw/workspace/skills/comfyui-image-gen/scripts/modify_and_send.py \
  /home/jagones/.openclaw/workspace/generated.png "turn this into a darker cinematic version" modified.png 0.45
```

Flux Unchained long-prompt example:

```bash
python3 /home/jagones/.openclaw/workspace/skills/comfyui-image-gen/scripts/flux_and_send.py \
  --file /home/jagones/.openclaw/workspace/my_long_prompt.txt 1024 1024 out.png
```

The long prompt file should start with the trigger prefix
`slptp, ballsxdeep, deepthroat, tongue out, throatfuck, throat bulge, balls deep, slobbery, drooling, gagging,`
followed by descriptive prose. Keep total length under 2000 chars.

## Maintenance & Sync Map

This skill touches four locations that MUST stay in lockstep. Use the table below to know which file to edit for any change.

| Location | Role | What lives here | Edit when... |
|---|---|---|---|
| `~/.openclaw/workspace/skills/comfyui-image-gen/SKILL.md` | **Canonical AI-facing manual** (this file, 1115+ lines) | Routing table, parameter sheet, BLOOM detection, trigger prefix, all 14 wf documented | New wf added, model changed, trigger prefix changed, BLOOM thresholds changed, launcher behavior changed |
| `/home/jagones/Repositories/comfyui-mcp/workflow_files/graphs/*.json` | **Workflow files** (14 .json) | The actual ComfyUI graph definitions (UNETLoader, KSampler, LoRA, etc.) | Model swap, sampler change, denoise tuning, new recipe, LoRA wiring change |
| `/home/jagones/Repositories/comfyui-mcp/workflow_files/graphs/` mirror at Windows `Z:\Repositories\comfyui-mcp\workflow_files\/home/jagones/Repositories/comfyui-mcp/workflow_files/graphs\` | **Win+Linux mirror** | Identical SHA256 to the Linux folder | Any .json change in `/home/jagones/Repositories/comfyui-mcp/workflow_files/graphs/` (sync both) |
| `~/.openclaw/workspace/skills/comfyui-image-gen/scripts/` | **Canonical scripts** (Python + bash) | `run_wf.py` (universal launcher), `flux_and_send.py` (legacy Flux), `generate_and_send.py`, `upscale_and_send.py`, `remove_bg_and_send.py`, `modify_and_send.py`, `quick-*.sh` wrappers | Launcher logic change, new script, parameter override flag, wrapper rename |
| `/home/jagones/Repositories/comfyui-mcp/workflow_files/runners/` | **Local copies of launchers** + Windows-side manual runners | Copy of `run_wf.py` + `quick-wf.sh` + ad-hoc `launch_<wf>.py` test scripts | Mirror new launchers from `~/.openclaw/.../scripts/` to Windows; new local runner for one-off tests |
| `Z:\Repositories\comfyui-mcp\workflow_files\README.md` | **Project-side structure doc** | Folder layout, wf→runner mapping, manual SSH example | Folder renamed, runner added/removed, wf added/removed |
| `Z:\ComfyUI\.agent\_SKILL_openclaw_sync.md` | **Session log of SKILL changes** | Append-only chronological list of "what changed in SKILL.md and when" | Every time SKILL.md is updated |
| `c:\Users\giova\.trae\memory\projects\<project>\project_memory.md` | **Cross-session rules** (auto-loaded) | Hard constraints, conventions, lessons learned, short_name list | New hard rule, new short_name, new winner, broken pattern to remember |

> **NOTA 2026-09-13 (fonte unica skill)**: l'import Hermes `~/.hermes/skills/openclaw-imports/<name>` è ora un **SYMLINK** a `~/.openclaw/workspace/skills/<name>`. Si edita SOLO la skill OpenClaw: le modifiche si propagano da sole a Hermes (che scopre via `os.walk(followlinks=True)`). NON ricreare copie: la vecchia procedura manuale `folder-sync` è deprecata.

### Update cadence

- **Adding a new validated wf** (canonical change):
  1. Drop the .json in `/home/jagones/Repositories/comfyui-mcp/workflow_files/graphs/` (Linux), then `scp` to Windows mirror. Verify SHA256.
  2. Add a `short_name` and file to the `WF_MAP` dict in `run_wf.py` (and the local copy in `runners/run_wf.py`).
  3. Add a row to the **Routing Table** and the **Parameter Sheet** in this SKILL.md.
  4. Append a one-line note to `_SKILL_openclaw_sync.md` with date + change.
  5. Add the `short_name` and description to `project_memory.md` Engineering Conventions.

- **Modifying an existing wf** (denoise, sampler, LoRA strength):
  1. Edit the .json in `/home/jagones/Repositories/comfyui-mcp/workflow_files/graphs/`, then `scp` to Windows.
  2. Update the matching row in the **Parameter Sheet** in this SKILL.md.
  3. Append a one-line note to `_SKILL_openclaw_sync.md` (date + which wf + which knob).

- **Adding a new LoRA / model checkpoint**:
  1. Drop file under `~/ComfyUI/models/{loras,checkpoints,diffusion_models,...}/` on the Spark.
  2. Update the **Parameter Sheet** row(s) that reference the new LoRA/model.
  3. Update `project_memory.md` Lessons Learned (model name + size + use case).

- **Changing the BLOOM detection threshold** (std / bloom / colors):
  1. Edit the **BLOOM detection** section in this SKILL.md.
  2. Edit the same numeric threshold in `project_memory.md` Hard Constraints.
  3. Append a note to `_SKILL_openclaw_sync.md`.

- **Renaming a `short_name`**:
  1. Edit `WF_MAP` in `run_wf.py` (Linux `~/.openclaw/.../scripts/run_wf.py` AND `runners/run_wf.py`).
  2. Update every mention in this SKILL.md (routing table, parameter sheet, examples).
  3. Update `project_memory.md` Engineering Conventions.
  4. Grep the whole project for the old name: `grep -r "old_short_name" .`

- **Adding a new launcher flag** to `run_wf.py`:
  1. Edit `run_wf.py` (Linux AND `runners/run_wf.py` mirror).
  2. Add an example to this SKILL.md under the "run_wf.py" section.
  3. Append a note to `_SKILL_openclaw_sync.md`.

### How to sync Windows ↔ Linux

```bash
# Push a new/edited wf from Windows to Spark:
scp Z:\Repositories\comfyui-mcp\workflow_files\/home/jagones/Repositories/comfyui-mcp/workflow_files/graphs\<file>.json jagones@192.168.1.38:/home/jagones/Repositories/comfyui-mcp/workflow_files/graphs/<file>.json

# Pull a new wf from Spark to Windows (when the Spark produced it):
scp jagones@192.168.1.38:/home/jagones/Repositories/comfyui-mcp/workflow_files/graphs/<file>.json Z:\Repositories\comfyui-mcp\workflow_files\/home/jagones/Repositories/comfyui-mcp/workflow_files/graphs\<file>.json

# Verify mirror integrity (one-liner, computes SHA256 of both sides for every .json):
diff <(ssh jagones@192.168.1.38 "cd /home/jagones/Repositories/comfyui-mcp/workflow_files/graphs && sha256sum *.json" | awk '{print $1, $2}') \
     <(cd Z:\Repositories\comfyui-mcp\workflow_files\/home/jagones/Repositories/comfyui-mcp/workflow_files/graphs && sha256sum *.json | awk '{print $1, $2}') \
  && echo "MIRROR OK" || echo "MIRROR MISMATCH"

# Mirror the launcher script:
scp Z:\Repositories\comfyui-mcp\workflow_files\runners\run_wf.py jagones@192.168.1.38:/home/jagones/.openclaw/workspace/skills/comfyui-image-gen/scripts/run_wf.py
scp Z:\Repositories\comfyui-mcp\workflow_files\runners\quick-wf.sh jagones@192.168.1.38:/home/jagones/.openclaw/workspace/skills/comfyui-image-gen/scripts/quick-wf.sh

# Push SKILL.md update to Spark:
scp Z:\ComfyUI\.agent\SKILL_openclaw_v2.md jagones@192.168.1.38:/home/jagones/.openclaw/workspace/skills/comfyui-image-gen/SKILL.md
```

### What NEVER to put in `/home/jagones/Repositories/comfyui-mcp/workflow_files/graphs/`

- **No `.py` files** - the MCP `comfyui-mcp` server (`workflow-loader.ts:39`) filters with `file.endsWith('.json')` and silently ignores everything else.
- **No broken JSON** - `JSON.parse` failure on a `.json` in the folder causes the MCP server to return HTTP 500 for the whole skill.
- **No duplicate filenames with different content** - keep one canonical file per logical wf, recover old versions to `_ARCHIVIO/`.

## run_wf.py replaces ad-hoc launcher scripts

Before 2026-08-23 23:10, each validated workflow required its own launcher (e.g. `launch_AIGEN_NSFW_FLUX_LONG.py`, manual `curl /prompt` calls, etc). This is now obsolete.

**The single universal launcher is `run_wf.py`** in the canonical scripts folder. It:
- reads ONLY from `/home/jagones/Repositories/comfyui-mcp/workflow_files/graphs/`
- auto-detects the prompt node (`CLIPTextEncode.text` or `TextEncodeQwenImageEditPlus.prompt`)
- auto-detects the source image node (`LoadImage`)
- auto-detects the KSampler and applies `--seed/--steps/--cfg/--denoise` overrides
- handles the Flux long negative-prompt node (the second `CLIPTextEncode` in the wf)
- uploads the source image automatically when `--image` is passed
- prints `READY_TO_SEND: /absolute/path` for the `message` tool

For Flux long-prompt specifically, the legacy `flux_and_send.py` script is still maintained for backward compatibility (it has a more chatty log and prompt-budget warnings). The wf path inside it has been redirected to `/home/jagones/Repositories/comfyui-mcp/workflow_files/graphs/AIGEN_NSFW_FLUX_LONG_api.json`. New code MUST use `run_wf.py flux_long ...` instead.

For generation via the Qwen AIO NSFW model (the original `default_workflow.json` / `img2img_workflow.json`), the MCP `comfyui-mcp` server still routes those operations. `run_wf.py` is for the explicit-per-file validated set.

## Downloadable Expansions

These are good next workflow categories for later expansion, but they are not yet part of the canonical path unless explicitly added and tested:

- inpainting for local masked fixes
- outpainting for canvas extension
- segmentation workflows for clothes, fashion items, or generic objects
- relighting and subject/background compositing
- canny/depth/pose guided image transformations
- face or detail restoration pipelines
- color grading and post-processing chains
- heavyweight Qwen image-edit workflows only after they are proven stable on this machine

## Failure Handling

- If the script fails before `READY_TO_SEND:`, report the generation failure honestly.
- If the upscale script fails before `READY_TO_SEND:`, report the upscale failure honestly.
- If the background removal script fails before `READY_TO_SEND:`, report the background removal failure honestly.
- If the modify script fails before `READY_TO_SEND:`, report the modification failure honestly.
- If the Flux Unchained script fails before `READY_TO_SEND:`, report the Flux generation failure honestly. Most common cause: prompt without the trigger block (LoRAs silent). Second most common: another model still loaded in VRAM.
- Do not revive removed experimental wrappers or heavy edit workflows during normal use.
- If the `message` tool fails with a path outside allowed directories, that means the wrong file path was used. Fix the path; do not repeat the same call.
- If ComfyUI is slow, wait inside the script path instead of spreading the work across many separate LLM turns.

## Video e audio (estratto)

Le sezioni "Video lungo e coerente" e "MiniMax-H3 (open weights)" che stavano qui
documentavano script di **altri motori** (`diffusion-pipelines`, FLF2V, Wan2.2, MiniMax-H3)
non presenti in questa skill. Estratte il 2026-09-19: vedi il riquadro **Video e audio — NON
competono a questa skill** sopra, la skill `comfyui-h3-video` e `diffusion-pipelines/film/`.

