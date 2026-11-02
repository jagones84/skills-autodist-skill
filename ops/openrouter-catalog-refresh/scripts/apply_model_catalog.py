#!/usr/bin/env python3
"""Apply a curated OpenRouter model catalog to openclaw.json (safe applier).

Does: backup -> replace models.providers.openrouter.models -> rebuild
agents.defaults.models openrouter refs (stale removed, premium_pins added)
-> rebuild modelPolicy.allow openrouter part -> atomic write + re-parse.

Catalog JSON schema:
{
  "models": [ {"id", "name", "reasoning", "input": [...],
               "cost": {"input", "output", "cacheRead", "cacheWrite"},
               "contextWindow", "maxTokens"} ],
  "premium_pins": { "openrouter/<id>": {"reasoning": {"effort": "high"}} }
}

Usage: python3 apply_model_catalog.py <catalog.json> [--config /path/openclaw.json]
Rollback: cp <config>.bak-modelcatalog-<ts> <config> && systemctl --user restart openclaw-gateway
"""
import argparse
import json
import os
import shutil
import sys
import time

PREFIX = "openrouter/"
REQUIRED_FIELDS = ("id", "name", "reasoning", "input", "cost", "contextWindow", "maxTokens")
COST_FIELDS = ("input", "output", "cacheRead", "cacheWrite")


def fail(msg: str) -> None:
    """Print an error and exit non-zero."""
    print(f"[ERROR] {msg}")
    raise SystemExit(1)


def time_stamp() -> str:
    """Timestamp used for backup suffixes."""
    return time.strftime("%Y%m%d-%H%M%S")


def validate_catalog(catalog: dict) -> tuple[list[dict], dict]:
    """Validate the curated catalog structure; return (models, pins)."""
    models = catalog.get("models")
    if not isinstance(models, list) or not models:
        fail("catalog.models must be a non-empty list")
    pins = catalog.get("premium_pins", {})
    if not isinstance(pins, dict):
        fail("catalog.premium_pins must be an object")

    ids: list[str] = []
    for m in models:
        missing = [f for f in REQUIRED_FIELDS if f not in m]
        if missing:
            fail(f"model {m.get('id', '?')} missing fields: {missing}")
        if not isinstance(m["cost"], dict) or any(c not in m["cost"] for c in COST_FIELDS):
            fail(f"model {m['id']} cost must contain {COST_FIELDS}")
        if m["id"] in ids:
            fail(f"duplicate id: {m['id']}")
        ids.append(m["id"])
    for ref, params in pins.items():
        if not ref.startswith(PREFIX):
            fail(f"premium pin ref must start with {PREFIX}: {ref}")
        if ref[len(PREFIX):] not in ids:
            fail(f"premium pin target not in models: {ref}")
        if not isinstance(params, dict):
            fail(f"premium pin params must be an object: {ref}")
    return models, pins


def collect_openrouter_primaries(cfg: dict) -> dict:
    """Map config location -> openrouter primary model refs (for breakage warnings)."""
    out: dict[str, str] = {}
    defaults_primary = cfg.get("agents", {}).get("defaults", {}).get("model", {}).get("primary")
    if isinstance(defaults_primary, str) and defaults_primary.startswith(PREFIX):
        out["agents.defaults.model.primary"] = defaults_primary
    for aid, entry in cfg.get("agents", {}).get("entries", {}).items():
        p = entry.get("model", {}).get("primary") if isinstance(entry, dict) else None
        if isinstance(p, str) and p.startswith(PREFIX):
            out[f"agents.entries.{aid}.model.primary"] = p
    comp = cfg.get("agents", {}).get("defaults", {}).get("compaction", {}).get("model")
    if isinstance(comp, str) and comp.startswith(PREFIX):
        out["agents.defaults.compaction.model"] = comp
    return out


def main() -> int:
    """Apply the curated catalog with full safety rails."""
    ap = argparse.ArgumentParser()
    ap.add_argument("catalog_path")
    ap.add_argument("--config", default="/home/jagones/.openclaw/openclaw.json")
    args = ap.parse_args()

    with open(args.config, "r", encoding="utf-8") as fh:
        cfg = json.load(fh)
    with open(args.catalog_path, "r", encoding="utf-8") as fh:
        catalog = json.load(fh)
    models, pins = validate_catalog(catalog)

    orp = cfg.get("models", {}).get("providers", {}).get("openrouter")
    if not isinstance(orp, dict) or not isinstance(orp.get("models"), list):
        fail("models.providers.openrouter.models missing in config")
    ad = cfg.get("agents", {}).get("defaults", {})
    ad_models = ad.get("models")
    allow = ad.get("modelPolicy", {}).get("allow")
    if not isinstance(ad_models, dict) or not isinstance(allow, list):
        fail("agents.defaults.models / modelPolicy.allow missing in config")

    bak = f"{args.config}.bak-modelcatalog-{time_stamp()}"
    shutil.copy2(args.config, bak)
    print(f"[INFO] backup written: {bak}")

    new_ids = [m["id"] for m in models]
    orp["models"] = json.loads(json.dumps(models))

    removed = [k for k in ad_models if k.startswith(PREFIX)]
    for k in removed:
        del ad_models[k]
    for ref, params in pins.items():
        ad_models[ref] = {"params": json.loads(json.dumps(params))}

    kept = [r for r in allow if not r.startswith(PREFIX)]
    ad["modelPolicy"]["allow"] = kept + [f"{PREFIX}{mid}" for mid in new_ids]

    ok = True
    for r in ad["modelPolicy"]["allow"]:
        if r.startswith(PREFIX) and r[len(PREFIX):] not in new_ids:
            print(f"[ERROR] policy ref without model entry: {r}")
            ok = False
    for mid in new_ids:
        if f"{PREFIX}{mid}" not in ad["modelPolicy"]["allow"]:
            print(f"[ERROR] model entry without policy ref: {mid}")
            ok = False
    for v in ad_models.values():
        if not isinstance(v, dict):
            ok = False

    new_refs = {f"{PREFIX}{i}" for i in new_ids}
    for where, ref in collect_openrouter_primaries(cfg).items():
        if ref not in new_refs:
            print(f"[ERROR] existing primary/compaction at {where} -> {ref} not in new catalog: replace it in this run")
            ok = False

    tmp = f"{args.config}.tmp-modelcatalog"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    with open(tmp, "r", encoding="utf-8") as fh:
        json.load(fh)
    os.replace(tmp, args.config)
    print(f"[INFO] config written atomically: {args.config}")

    print(f"[INFO] openrouter models: {len(new_ids)} (thinking={sum(1 for m in models if m.get('reasoning'))})")
    print(f"[INFO] removed stale agents.defaults.models refs: {len(removed)}")
    print(f"[INFO] premium pins: {len(pins)}")
    print(f"[INFO] modelPolicy.allow total: {len(ad['modelPolicy']['allow'])}")
    if not ok:
        print("[INFO] rollback: cp <backup> over config + restart gateway")
        fail("post-assertions failed")
    print("[INFO] DONE")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        import traceback

        traceback.print_exc()
        sys.exit(2)
