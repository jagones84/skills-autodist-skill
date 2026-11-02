#!/usr/bin/env python3
"""Post-apply verification battery for the OpenRouter catalog.

Checks (config): field completeness, modelPolicy.allow sync, premium pins.
Checks (system): service active, health 200, no ERROR/CONFIG journal lines.
Optional: --snapshot path -> every configured id must exist in the snapshot
(dead-id check against the fetch step).

Usage: python3 verify_model_catalog.py [--snapshot <snapshot.json>] [--config /path/openclaw.json]
"""
import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request

SERVICE = "openclaw-gateway.service"
HEALTH_URLS = ("http://127.0.0.1:18789/health", "http://127.0.0.1:18789/healthz")

ok = True


def flag(cond: bool, label: str, extra: str = "") -> None:
    """Print a PASS/FAIL line and track the global result."""
    global ok
    if not cond:
        ok = False
    print(f"[{'PASS' if cond else 'FAIL'}] {label}{(' | ' + extra) if extra else ''}")


def check_config(cfg: dict, snapshot: dict | None) -> None:
    """Config-level invariants."""
    models = cfg.get("models", {}).get("providers", {}).get("openrouter", {}).get("models", [])
    ids = [m.get("id") for m in models]
    no_ctx = [i for m, i in zip(models, ids) if not m.get("contextWindow")]
    no_max = [i for m, i in zip(models, ids) if not m.get("maxTokens")]
    no_reason_field = [i for m, i in zip(models, ids) if not isinstance(m.get("reasoning"), bool)]
    flag(len(models) > 0, f"openrouter models present ({len(models)})")
    flag(not no_ctx, "all models have contextWindow", ",".join(no_ctx))
    flag(not no_max, "all models have maxTokens", ",".join(no_max))
    flag(not no_reason_field, "all models declare reasoning true/false", ",".join(no_reason_field))

    ad = cfg.get("agents", {}).get("defaults", {})
    allow = ad.get("modelPolicy", {}).get("allow", [])
    or_allow = {r for r in allow if isinstance(r, str) and r.startswith("openrouter/")}
    flag(or_allow == {f"openrouter/{i}" for i in ids}, "modelPolicy.allow synced with models")

    for ref, entry in ad.get("models", {}).items():
        if not isinstance(ref, str) or not ref.startswith("openrouter/"):
            continue
        mid = ref[len("openrouter/"):]
        if mid not in ids:
            flag(False, f"agents.defaults.models stale ref: {ref}")
        elif isinstance(entry, dict):
            eff = entry.get("params", {}).get("reasoning", {}).get("effort")
            print(f"[INFO] pin {ref}: effort={eff if eff else '(session default)'}")

    if snapshot:
        live = set(snapshot.get("models", {}))
        dead = [i for i in ids if i not in live]
        flag(not dead, "configured ids all present in snapshot (no 404s)", ",".join(dead))


def check_system() -> None:
    """Service, health endpoint, and journal error scan."""
    r = subprocess.run(["systemctl", "--user", "is-active", SERVICE], capture_output=True, text=True, timeout=20)
    flag(r.stdout.strip() == "active", f"service active (got: {r.stdout.strip()})")

    j = subprocess.run(
        ["journalctl", "--user", "-u", SERVICE, "-n", "150", "--no-pager"],
        capture_output=True, text=True, timeout=30,
    )
    err = [l for l in j.stdout.splitlines() if "[ERROR]" in l or "config validation" in l.lower()]
    flag(not err, "no ERROR/config-validation lines in last 150 journal lines", " | ".join(err[-2:]))

    health = None
    for url in HEALTH_URLS:
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                health = (url, resp.status, resp.read(120).decode("utf-8", "ignore"))
                break
        except (urllib.error.URLError, TimeoutError, OSError):
            continue
    flag(health is not None, "health endpoint reachable", health[2][:60] if health else "unreachable")


def main() -> int:
    """Run all checks and exit 0/1."""
    global ok
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", default=None)
    ap.add_argument("--config", default="/home/jagones/.openclaw/openclaw.json")
    args = ap.parse_args()

    with open(args.config, "r", encoding="utf-8") as fh:
        cfg = json.load(fh)
    snapshot = None
    if args.snapshot:
        with open(args.snapshot, "r", encoding="utf-8") as fh:
            snapshot = json.load(fh)

    check_config(cfg, snapshot)
    check_system()
    print("\nRESULT:", "ALL PASS" if ok else "SOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
