# Flux Unchained NSFW - Long Prompt Reference

This is the canonical reference for writing long explicit prompts for the
Flux Unchained (FastFlux Unchained FP8) pipeline on this machine.

> **LANGUAGE RULE (HARD)**: ALL prompts submitted to ANY workflow (Flux, Qwen, SDXL, edits, inpaints) MUST be written in **English**. Never translate an Italian user request into an Italian prompt — translate it into English prose or tag lists. Language mixing degrades encoder alignment and was observed to produce ambiguous anatomy in live tests (2026-08-24).

## What you can fit in one prompt

The T5-XXL FP8 text encoder does **not** truncate normal text. Empirically
verified (2026-08-22):

| Metric | Soft limit | Hard limit |
|---|---|---|
| Characters | ~1500 | 2000 |
| Approx tokens | ~380 | ~600 |
| Generation time (1024x1024) | ~150s | ~180s |

The skill `flux_and_send.py` warns over 1500 chars and hard-trims at 2000.
For longer content, split into multiple jobs with the same seed and different
focus areas, or generate at higher resolution with a tighter prompt.

## Required tag prefix (LoRA triggers)

The default workflow applies two LoRAs to the Flux UNet:

- `SloppyToppy_flux.safetensors`  strength 0.70
- `SidewaysDeepthroat_flux.safetensors`  strength 0.75

You MUST start the prompt with the explicit trigger tags, or the LoRAs
silently disengage and the anatomy falls back to Flux defaults.

Canonical trigger block (always at the very front of the prompt):

```
slptp, ballsxdeep, deepthroat, tongue out, throatfuck, throat bulge, balls deep, slobbery, drooling, gagging,
```

You can repeat trigger words mid-prompt for emphasis (e.g. `deepthroat,
throatfuck, throat bulge` near the end) - the model treats it as positive
reinforcement.

## Prompt body structure

After the trigger prefix, write natural descriptive prose. The Flux
text encoder prefers flowing language over comma-tag soup. The optimal order:

1. **Trigger block** (above) - non-negotiable, 7-12 tags
2. **Subject**: 1-2 sentences describing the main figure(s) with concrete
   visual details (age, hair, skin, body type, expression, clothing state)
3. **Action / pose**: what is happening, position, contact points, visible
   anatomy. Be explicit - this is uncensored.
4. **Camera / framing**: pov, angle, focal length, distance
5. **Lighting / environment**: setting, light source, mood
6. **Quality anchors** at the very end:
   `photorealistic, masterpiece, best quality, hyper-detailed, 8k uhd`

## Negative prompt

The default negative is tuned for the LoRAs and the explicit content.
Do NOT remove these tokens - they prevent the standard Flux failure modes:

```
low quality, blurry, deformed, cartoon, anime, illustration, watermark, text,
ugly, disfigured, bad anatomy, extra fingers, extra limbs, fused fingers,
too many fingers, long neck, clothed, dress, shirt, turned away, looking
away, side view, from behind, censored, mosaic, blur censor, black bar,
penis not visible, penis covered, hidden, soft, fade, low detail
```

Override with `--negative "..."` only if you have a specific reason (e.g.
you want clothed, or a different camera angle).

## Worked example (1474 chars, approved 2026-08-22)

```
slptp, ballsxdeep, deepthroat, tongue out, throatfuck, throat bulge, balls deep, slobbery, drooling, gagging,
a raw photorealistic close-up photograph of a beautiful naked 25 year old
Caucasian woman with long black hair, kneeling on a dark hardwood floor in
front of a standing fully naked muscular Black man with a very large thick
visible penis and visible testicles, she is facing him directly looking up
at him, his penis is fully visible and completely deep inside her mouth
reaching her throat, throat bulge clearly visible on her neck, her mouth is
open wide stretched around the base of his cock, her lips are wrapped around
the shaft, her tongue is out and visible, her face is completely covered in
saliva and drool dripping from her lips and chin down onto her bare chest
and bare breasts, his right hand gripping the back of her head pulling her
forward, she is gagging and choking, his balls are deep pressing against
her chin, BBC interracial scene, intimate pov camera angle slightly behind
her shoulder showing her face in profile and his penis fully visible,
professional studio lighting, sharp focus on her face his penis and his
balls, 8k uhd, hyperrealistic skin detail, masterpiece photography,
deepthroat, throatfuck, throat bulge, balls deep, 25-years-old, nsfw,
explicit, naked, BBC, dark skin, hyper-detailed anatomy, photorealistic,
masterpiece, best quality, slobber, spit dripping, mouth stretched, penis
fully visible, testicles visible, precum
```

This prompt was validated as the new `AIGEN_NSFW_FLUX_LONG` workflow.

## Common failure modes and fixes

| Symptom | Cause | Fix |
|---|---|---|
| Image looks vanilla / no act visible | LoRA triggers missing | Verify the 7-tag trigger block is at the very start |
| Penis cropped, hidden or implied | Negative prompt too aggressive | Remove `penis not visible, penis covered, hidden` for that run |
| Subject turned away / side view | Negative prompt forbidding frontal | Remove `turned away, side view, from behind` |
| Stiff pose, both figures upright | LoRA strength too low | Use the default workflow strengths (0.70 / 0.75) |
| Washed out colors, no contrast | Lighting description missing | Add explicit light source: `studio lighting, single key light, rim light` |
| Clothed or partial clothing | Negative prompt was removed | Restore the default negative block |
