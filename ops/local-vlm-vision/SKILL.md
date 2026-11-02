---
name: local-vlm-vision
description: "Caption/describe a local image with Qwen3-VL-4B."
---

# Local VLM Image Captioning on DGX

## When to use

`vision_analyze` fails with a 404 ("No endpoints found that support image input") when the active chat provider
(OpenCode Free / OpenRouter free tiers, light local models) serves no image-capable endpoint. When you still need to
*see* a local image — authoring motion prompts for an i2v chain, verifying a generation actually rendered the
requested elements, checking dims/state — run the **local Qwen3-VL-4B** instead. Weights are already on the DGX;
zero download, ComfyUI stays OFF.

## Canonical invocation

The reusable script ships with this skill — **use it in preference to any hand-typed variant**:

```bash
/home/jagones/ComfyUI/venv/bin/python \
  /home/jagones/Repositories/skills-autodist-skill/ops/local-vlm-vision/scripts/caption_local.py <image.png>
```

(or `skill_view(name='local-vlm-vision', file_path='scripts/caption_local.py')` to re-read it). It hardcodes the correct weights path, the explicit `Qwen3VLForConditionalGeneration` class, and `sdpa`; pass a second arg only for a non-default weights dir.

Prints the caption between `CAPTION_START` / `CAPTION_END` markers. Ask it for a **dense cinematic caption
(80-120 words)** — subject + action + location + implied motion + key elements — which drops straight into the
motion-first prompt structure of the i2v WAMU chain (`--prompts "A1|||A2|||..."`).

## Environment facts (verified, do not re-derive)

- **venv that works: `/home/jagones/ComfyUI/venv/bin/python`** — transformers 5.1.0 + torchvision + torch, all matched.
  - Any other venv bites: `wan555/venv` has transformers 5.17 but **no torchvision** (Qwen3VLVideoProcessor crashes with
    ImportError); the system python3 has neither.
- **Weights: `/home/jagones/ComfyUI/models/LLM/Qwen-VL/Qwen3-VL-4B-Instruct`**. Verify `ls` before running.
- **`flash_attn` is NOT installed** anywhere — must use `attn_implementation="sdpa"`. flash_attention_2 raises ImportError.

## Pitfalls (each cost a debug cycle)

- **Use the explicit class `Qwen3VLForConditionalGeneration`, NOT `AutoModelForCausalLM`.** In transformers 5.1.0
  (ComfyUI venv) Qwen3VL is registered as a processor/config but NOT in the AutoModelForCausalLM registry — it raises
  `Unrecognized configuration class Qwen3VLConfig for AutoModelForCausalLM`. The wan555 venv's 5.17 does register it,
  but that venv lacks torchvision, so you cannot rely on Auto* there either.
- **Check `torch.cuda.is_available()` / VRAM headroom first** with the SAME venv you will run. A 130 GB free DGX pool
  is plenty for the 4B model, but verify free VRAM before loading to avoid an OOM during a long video job.
- **Filter the log noise**: the run emits heavy `torch/_pytree`, `_library/triton.py: failed to resolve...`, and a large
  `Loading weights:` progress bar to stderr. Grep from `loading <weights path>` through the caption markers; the
  caption line is what matters.
- **Pipe-read the exit code correctly**: `python ... | tail -N` returns tail's status, masking a crash. On failure,
  re-run without the pipe (output is auto-saved to a file) to see the real traceback.
- **Load per-run and let the process exit**: the model is ~7 GB in VRAM; each call is a one-shot process that frees
  VRAM on exit. Do NOT keep it resident across a long video chain — run it once for the caption, then start the video
  pipeline with a clean VRAM pool.

## Workflow tie-in (i2v prompt authoring)

1. Caption the source image with the local VLM (above).
2. Turn the caption into N action prompts, each segment = one motion verb (present progressive) + one camera move +
   one end-state anchor, plus a persistence anchor (`stays fully visible in frame throughout`).
3. Feed as `--prompts "A1|||A2|||...|||AN"` to the WAMU i2v chain. 20 s / 4 actions = `--chain-segs 4 --duration 5.0`.

The video/audio end-to-end recipe (PNG -> multi-action i2v .mp4 -> MMAudio foley) lives in the protected
`openclaw-imports/comfyui-image-gen` skill; this skill covers the standalone VLM-as-eyes ingredient that those chains
depend on when the chat model is vision-blind.
