---
name: local-llm-model-fit
description: Use when choosing a local GGUF model fit for this DGX.
---

# Local LLM model fit (llmfit on the DGX)

`llmfit` is a prebuilt Rust CLI (`~/.local/bin/llmfit`, repo `~/Repositories/llmfit`) that detects the host's hardware and scores every model in its embedded catalog for fit and throughput, so you can pick which local GGUF actually runs well here instead of guessing. It is the co-selector layer UNDER the agent framework: Hermes/OpenClaw orchestrate dialogue, llmfit tells you what model the box can run.

## When to use
- Choosing the next local model / deciding whether a candidate GGUF fits this machine.
- Comparing two models (fit, quant, VRAM/RAM, est. tok/s) before a change.
- Confirming what the DGX can actually run locally (vs cloud models like openrouter).

## The DGX reality (this host)
- Hardware llmfit detects: NVIDIA GB10, unified memory ~121 GB (shared VRAM=RAM), total RAM ~121 GB, CUDA, ~20 cores.
- With 121 GB unified, virtually ANY small/mid model fits; llmfit marks the catalog entries `Perfect` at `Q8_0`.
- Note the distinction: cloud models (openrouter, e.g. deepseek-v4-flash) are NOT local — llmfit sizes only local GGUF weights.

## Commands that work
```
llmfit system                      # hardware report: GPU, RAM, CPU, backend
llmfit --json recommend            # top models for this hardware as JSON
llmfit fit --perfect -n 5          # classic table, top N perfect-fit models
llmfit info <model>                # detailed info on one model
llmfit diff <a> <b>                # side-by-side comparison
llmfit update                      # refresh the embedded HF catalog
```

## Pitfalls
- **Global flags go BEFORE the subcommand.** `--json`, `--max-context`, `--ram`, `--memory` are global: `llmfit --json recommend` works, `llmfit recommend --json` (and any flag after the subcommand) fails with `unexpected argument`. When a flag is rejected, move it in front of the command word.
- **`recommend --json` prints pure JSON; `system`/`fit` print text.** Pipe `--json` output to `python3 -c` with `json.load(sys.stdin)` for the top-N, or it may be mangled by a non-JSON header. Keep the subset extraction in one script so the catalog count and per-model rows (name, fit_label, best_quant, memory_required_gb, estimated_tps) come out clean.
- **The embedded catalog is SMALL.** The README claims 33 models but `recommend` shows only a handful (e.g. 5). Models you actually run (qwen3.6-35b, deepseek-v4-flash GGUF) are usually NOT in it. For a real candidate, run `llmfit update` to refresh the HF catalog or point it at the specific GGUF repo; do not assume an absent model means it won't fit.
- **Reading = safe; changing = coordinate.** Running `system`/`recommend` is read-only on hardware and safe anytime (a user "ok a tutto se non pericoloso" covers it). Downloading/launching models (`download`, `run`) or changing the local model stack is a state change — confirm with the human before acting, and co-ordinate with the peer bot that owns the local model stack (technical domain) before switching anything.
