#!/usr/bin/env python3
"""E2E smoke: call OpenRouter models with a reasoning effort param on the wire.

Reads OPENROUTER_API_KEY from the running gateway process environ.
NEVER prints, logs, or persists the key. No OpenClaw sessions touched.

Usage: python3 smoke_openrouter_models.py <model_id> [model_id ...]
       (no args = auto-pick the 3 cheapest reasoning:true configured models)
"""
import json
import subprocess
import sys
import urllib.error
import urllib.request

CONFIG = "/home/jagones/.openclaw/openclaw.json"
SERVICE = "openclaw-gateway.service"
API = "https://openrouter.ai/api/v1/chat/completions"


def get_gateway_key() -> str:
    """Read the OpenRouter key from the gateway process env (never logged)."""
    r = subprocess.run(
        ["systemctl", "--user", "show", SERVICE, "-p", "MainPID"],
        capture_output=True, text=True, timeout=20,
    )
    pid = int(r.stdout.strip().split("=")[1])
    with open(f"/proc/{pid}/environ", "rb") as fh:
        env = fh.read().decode("utf-8", "ignore")
    for chunk in env.split("\x00"):
        if chunk.startswith("OPENROUTER_API_KEY="):
            return chunk.split("=", 1)[1]
    raise SystemExit("OPENROUTER_API_KEY not found in gateway env")


def pick_default_models() -> list[str]:
    """Choose the 3 cheapest reasoning:true openrouter models from config."""
    with open(CONFIG, "r", encoding="utf-8") as fh:
        cfg = json.load(fh)
    models = [
        (m.get("cost", {}).get("output", 999.0), m["id"])
        for m in cfg.get("models", {}).get("providers", {}).get("openrouter", {}).get("models", [])
        if isinstance(m, dict) and m.get("reasoning") is True
    ]
    models.sort()
    return [mid for _, mid in models[:3]]


def call(key: str, model: str, with_reasoning: bool = True) -> bool:
    """POST one chat completion; report reasoning-field acceptance."""
    body: dict = {
        "model": model,
        "messages": [{"role": "user", "content": "Rispondi solo: OK"}],
        "max_tokens": 200,
    }
    if with_reasoning:
        body["reasoning"] = {"effort": "medium"}
    req = urllib.request.Request(
        API,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "openclaw-catalog-smoke/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.load(resp)
        msg = data.get("choices", [{}])[0].get("message", {})
        rfield = "reasoning" if msg.get("reasoning") else ("-none-" if "reasoning" not in msg else "empty")
        content = (msg.get("content") or "").strip()[:60]
        usage = data.get("usage", {})
        print(f"[PASS] {model} | reasoning_field={rfield} | content={content!r} | tokens={usage.get('completion_tokens')}")
        return True
    except urllib.error.HTTPError as e:
        print(f"[FAIL] {model} | HTTP {e.code} | {e.read(300).decode('utf-8', 'ignore')}")
        return False
    except Exception as e:  # noqa: BLE001 - report any transport failure
        print(f"[FAIL] {model} | {e}")
        return False


def main() -> int:
    """Run the smoke battery."""
    models = sys.argv[1:] or pick_default_models()
    print(f"smoke targets: {models}")
    key = get_gateway_key()
    ok = all(call(key, m) for m in models)
    print("\nSMOKE:", "ALL PASS" if ok else "SOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
