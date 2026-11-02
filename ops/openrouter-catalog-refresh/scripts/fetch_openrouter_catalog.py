#!/usr/bin/env python3
"""Fetch the live OpenRouter catalog and snapshot it against the configured roster.

READ-ONLY: never touches openclaw.json. Writes snapshot JSON to
~/.openclaw/outputs/<ts>_openrouter-catalog/openrouter-snapshot.json and
prints: DEAD (configured but gone = 404 guaranteed), configured details,
value candidates (quality/cost shortlist).

Usage: python3 fetch_openrouter_catalog.py [--config /path/openclaw.json]
"""
import argparse
import datetime
import json
import os
import sys
import urllib.request

API = "https://openrouter.ai/api/v1/models"
DEFAULT_CONFIG = "/home/jagones/.openclaw/openclaw.json"
OUT_ROOT = "/home/jagones/.openclaw/outputs"

FAMILY_RE = (
    "deepseek/", "qwen/", "moonshotai/", "z-ai/", "minimax/", "x-ai/",
    "google/gemini", "openai/gpt-oss", "openai/gpt-5", "meta-llama/llama-4",
    "mistralai/mistral", "mistralai/devstral", "nvidia/nemotron",
    "thinkingmachines/", "microsoft/phi", "tngtech/", "cognitivecomputations/",
    "arcee-ai/", "liquid/", "ai21/", "amazon/", "anthropic/claude",
    "openai/gpt-4", "featherless/", "eva-ai/", "thedrummer/",
)
VARIANT_TAGS = (":free", ":extended", ":beta", ":nitro", ":floor", ":online", ":thinking", ":batch")
OUT_MAX = 3.0
CTX_MIN = 128000


def per_musd(raw: object) -> float | None:
    """Convert a per-token price to $/M tokens."""
    try:
        return float(raw) * 1_000_000
    except (TypeError, ValueError):
        return None


def fmt_price(p: float | None) -> str:
    """Compact price rendering for the report table."""
    if p is None:
        return "?"
    if p == 0:
        return "0"
    if p < 0.01:
        return f"{p:.4f}"
    return f"{p:.3f}".rstrip("0").rstrip(".")


def fetch_catalog() -> list[dict]:
    """GET the live OpenRouter model catalog."""
    req = urllib.request.Request(API, headers={"User-Agent": "openclaw-catalog-refresh/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp).get("data", [])


def summarize(m: dict) -> dict:
    """Extract the fields needed for curation decisions."""
    tp = m.get("top_provider") or {}
    sp = m.get("supported_parameters") or []
    return {
        "id": m.get("id"),
        "name": m.get("name"),
        "context_length": m.get("context_length"),
        "top_ctx": tp.get("context_length"),
        "max_completion_tokens": tp.get("max_completion_tokens"),
        "input_per_musd": per_musd((m.get("pricing") or {}).get("prompt")),
        "output_per_musd": per_musd((m.get("pricing") or {}).get("completion")),
        "cache_read_per_musd": per_musd((m.get("pricing") or {}).get("input_cache_read")),
        "supports_reasoning": "reasoning" in sp,
        "supported_parameters": sp,
        "input_modalities": (m.get("architecture") or {}).get("input_modalities", []),
    }


def main() -> int:
    """Run the snapshot pipeline: fetch, report, write snapshot JSON."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=DEFAULT_CONFIG)
    args = ap.parse_args()

    with open(args.config, "r", encoding="utf-8") as fh:
        cfg = json.load(fh)
    configured = [
        x.get("id")
        for x in cfg.get("models", {}).get("providers", {}).get("openrouter", {}).get("models", [])
        if isinstance(x, dict)
    ]

    models = fetch_catalog()
    by_id = {m.get("id"): m for m in models}

    dead = [mid for mid in configured if mid not in by_id]
    print(f"TOTAL_MODELS={len(models)} CONFIGURED={len(configured)}")

    print("\n=== A) CONFIGURED IDS (live data) ===")
    for mid in configured:
        m = by_id.get(mid)
        if m is None:
            print(f"{mid} | DEAD_NOT_IN_CATALOG")
            continue
        s = summarize(m)
        print(
            f"{mid} | ctx={s['context_length']} top_ctx={s['top_ctx']} "
            f"max_out={s['max_completion_tokens']} | in={fmt_price(s['input_per_musd'])} "
            f"out={fmt_price(s['output_per_musd'])} | reasoning={s['supports_reasoning']}"
        )

    print("\n=== B) DEAD (configured, absent from live catalog) ===")
    print("\n".join(dead) if dead else "(none)")

    print("\n=== C) VALUE CANDIDATES (not configured, out<=3$/M, ctx>=128k) ===")
    cand = []
    for m in models:
        mid = m.get("id", "")
        if mid in configured or not any(mid.startswith(f) for f in FAMILY_RE):
            continue
        if any(t in mid for t in VARIANT_TAGS):
            continue
        s = summarize(m)
        if s["output_per_musd"] is None or s["output_per_musd"] > OUT_MAX:
            continue
        if (s["top_ctx"] or 0) < CTX_MIN:
            continue
        cand.append((s["output_per_musd"], -s["top_ctx"], mid, s))
    cand.sort()
    for _, _, mid, s in cand:
        print(
            f"{mid} | ctx={s['context_length']} top_ctx={s['top_ctx']} "
            f"max_out={s['max_completion_tokens']} | in={fmt_price(s['input_per_musd'])} "
            f"out={fmt_price(s['output_per_musd'])} | reasoning={s['supports_reasoning']} "
            f"| mod={','.join(s['input_modalities'])}"
        )

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(OUT_ROOT, f"{ts}_openrouter-catalog")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "openrouter-snapshot.json")
    snapshot = {
        "generated_at": ts,
        "total": len(models),
        "configured": configured,
        "dead": dead,
        "models": {m.get("id"): summarize(m) for m in models if m.get("id")},
    }
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, indent=1, ensure_ascii=False)
    print(f"\nSNAPSHOT_WRITTEN={out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
