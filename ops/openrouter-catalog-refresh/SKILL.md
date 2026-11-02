---
name: "openrouter-catalog-refresh"
description: "Refreshes the OpenRouter model catalog in openclaw.json: detects dead/404 model IDs against the live OpenRouter API, adds best quality/cost replacements with accurate contextWindow/maxTokens from top_provider, sets reasoning:true so thinking models receive reasoning.effort. Invoke when the user asks to update/refresh OpenRouter models, add or replace a model, fix 'model not found' 404s, or fix missing reasoning/thinking effort. Triggers: 'aggiorna modelli openrouter', 'refresh models', 'catalogo modelli', 'add model', 'sostituisci modello', 'modello morto', '404 model', 'reasoning effort', 'thinking model', 'modello locale mangia VRAM'."
---

# OpenRouter Catalog Refresh (openclaw.json)

Refresh the OpenRouter provider catalog: snapshot the live API catalog,
curate the model roster (quality per cost), apply with backup + atomic
write, verify, smoke-test. Field-proven pipeline (2026-09-01 intervention).

## Pipeline (run IN ORDER, no skipping)

```dot
digraph pipeline {
  rankdir=LR;
  fetch [label="1. fetch snapshot"];
  curate [label="2. curate catalog.json"];
  apply [label="3. apply (backup+atomic)"];
  verify [label="4. verify"];
  smoke [label="5. smoke E2E"];
  fetch -> curate -> apply -> verify -> smoke;
}
```

### 1. Snapshot (READ-ONLY)
```bash
python3 <skill_dir>/scripts/fetch_openrouter_catalog.py
```
Writes snapshot JSON to `~/.openclaw/outputs/<ts>_openrouter-catalog/` and
prints: DEAD (configured but absent from live catalog = 404 guaranteed),
configured details, value candidates. NEVER edit config from memory: always
start from the snapshot.

### 2. Curate
Write `catalog.json` (next to the snapshot) with schema:
```json
{
  "models": [
    {"id": "vendor/model", "name": "Human name", "reasoning": true,
     "input": ["text"], "cost": {"input": 0.03, "output": 0.13,
     "cacheRead": 0.006, "cacheWrite": 0},
     "contextWindow": 1000000, "maxTokens": 65536}
  ],
  "premium_pins": {"openrouter/vendor/id": {"reasoning": {"effort": "high"}}}
}
```
Curation criteria (from the 2026-09-01 field pass):
- Prices in $/M tokens from snapshot (`pricing.prompt/completion * 1e6`).
- Prefer reasoning models with `reasoning` in `supported_parameters`.
- ctx >= 128k for agent work; value sweet spot: output <= $1/M when possible.
- `contextWindow` = `top_provider.context_length` (NOT bare context_length).
- `maxTokens` = min(top_provider.max_completion_tokens, 65536) unless the
  model's own cap is lower (gemma4/nemotron-super = 16384, qwen3-next-80b = 32768).
- `reasoning: true` IFF `supported_parameters` includes "reasoning".
- Skip `:free`/`:beta`/`:batch`/`:nitro`/`:online` variants and x-ai/* for
  thinking (OpenClaw drops thinking for x-ai by design: proxy reasoning
  unsupported), security classifiers (llama-guard), tiny ctx (<128k).
- KEEP the compaction model and the coordinator/subagent primaries WORKING:
  if a primary or `compaction.model` id is removed, replace it in the same run.

### 3. Apply
```bash
python3 <skill_dir>/scripts/apply_model_catalog.py <path>/catalog.json
```
Does: backup `openclaw.json.bak-modelcatalog-<ts>` -> replace
`models.providers.openrouter.models` -> rebuild `agents.defaults.models`
openrouter refs (stale removed, premium_pins re-added) -> rebuild
`modelPolicy.allow` openrouter part -> atomic write + re-parse -> asserts.
Idempotent. Rollback = `cp` backup over config + restart gateway.

### 4. Restart + verify
Config changes to the catalog need a gateway restart (hot reload does NOT
rebuild provider catalogs). BEFORE restarting, check no UI update is running
(`update.status` in journal / ask user): a restart during "Aggiorna Gateway"
causes transient `managed-service-handoff-cancelled`.
```bash
systemctl --user restart openclaw-gateway.service
python3 <skill_dir>/scripts/verify_model_catalog.py --snapshot <snapshot.json>
```
Verify demands: all models have contextWindow/maxTokens, allow-list synced,
service active, health 200, no ERROR/CONFIG lines in journal, snapshot ids
all present.

### 5. Smoke E2E (real wire test)
```bash
python3 <skill_dir>/scripts/smoke_openrouter_models.py <model_id1> <model_id2>
```
Reads `OPENROUTER_API_KEY` from the gateway process environ. NEVER print,
log, or write the key anywhere. Tests chat completions WITH
`reasoning: {"effort": "medium"}` to prove the effort param is accepted.

## Golden Rules (violations caused real incidents)

1. `reasoning: true` is the GATE: without it OpenClaw deletes
   `payload.reasoning`/`reasoning_effort` from every request
   (`supportsReasoningControls` in dist). thinkingDefault alone does NOTHING.
2. With the flag set, OpenClaw auto-builds `reasoning: {effort: <thinkingLevel>}`
   (off->none, max/ultra->xhigh, others pass through). Do NOT add
   `chat_template_kwargs` hacks on OpenRouter models: use empty pins only
   for premium effort override.
3. Missing contextWindow/maxTokens falls back to weak defaults (200k/8192)
   -> premature compaction and truncation errors.
4. Model IDs die often: always verify against the LIVE catalog (fetch step),
   never trust remembered IDs.
5. Never inline-edit openclaw.json by hand: scripts do backup + atomic write.
6. API key: env of gateway PID only; never echoed.
7. Two-strike rule: if apply+restart fails twice, STOP, rollback from
   backup, re-read the snapshot.

## Files
- `scripts/fetch_openrouter_catalog.py` - snapshot + dead detection + candidates
- `scripts/apply_model_catalog.py` - safe applier (backup/atomic/allow-sync)
- `scripts/verify_model_catalog.py` - post-apply verification battery
- `scripts/smoke_openrouter_models.py` - wire test with reasoning effort
