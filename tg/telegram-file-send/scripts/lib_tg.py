#!/usr/bin/env python3
"""telegram-file-send: helper condivisi.

NON usare direttamente. Importato da tg_send.py e tg_http_serve.py.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Optional


# ----------------------------------------------------------------------
# Identita (source of truth)
# ----------------------------------------------------------------------
DEFAULT_CHAT_ID = 407582054           # Giovanni, "jagones"
DEFAULT_BOT_NAME = "@Jagones_Bot"     # Raffaella (OpenClaw coordinator)
TG_API_BASE = "https://api.telegram.org"
LIMIT_BOT_API_BYTES = 50 * 1024 * 1024     # 50 MB hard cap cloud API
LIMIT_USER_CLIENT_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB user client


# ----------------------------------------------------------------------
# Token loader: ~/.openclaw/gateway.systemd.env (DGX) o env var
# ----------------------------------------------------------------------
GATEWAY_ENV = Path("/home/jagones/.openclaw/gateway.systemd.env")
# Fallback per Windows PC: il bot token non sta qui, ma l'utente
# puo' passarlo via --token o TG_BOT_TOKEN env var.
WIN_FALLBACK_TOKEN_FILE = Path(
    "C:/Users/giova/.openclaw/gateway.systemd.env"  # ipotesi speculativa
)


def load_bot_token(explicit: Optional[str] = None) -> str:
    """Carica il bot token.

    Priorita':
      1. argomento `explicit`
      2. env var TG_BOT_TOKEN
      3. ~/.openclaw/gateway.systemd.env (key TELEGRAM_BOT_TOKEN)
      4. C:/Users/giova/.openclaw/gateway.systemd.env (Windows fallback)

    Mai stampare il token in chiaro. Mascherare nei log.
    """
    if explicit:
        return explicit.strip()

    env_tok = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if env_tok:
        return env_tok

    for path in (GATEWAY_ENV, WIN_FALLBACK_TOKEN_FILE):
        if not path.exists():
            continue
        try:
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                m = re.match(r'(?:export\s+)?([A-Z_][A-Z0-9_]*)=["\']?([^"\']*)["\']?', line)
                if m and m.group(1) == "TELEGRAM_BOT_TOKEN":
                    tok = m.group(2).strip()
                    if tok:
                        return tok
        except Exception as e:
            print(f"[lib_tg] warning: cannot read {path}: {e}", file=sys.stderr)

    raise SystemExit(
        "ERRORE: TELEGRAM_BOT_TOKEN non trovato. "
        "Setta la env var o metti TELEGRAM_BOT_TOKEN=... in "
        "~/.openclaw/gateway.systemd.env"
    )


def mask_token(token: str) -> str:
    """Ritorna token mascherato per log: 1234...XYZ."""
    if not token or len(token) < 10:
        return "<invalid>"
    return f"{token[:6]}...{token[-4:]}"


# ----------------------------------------------------------------------
# Telegram API call helpers
# ----------------------------------------------------------------------
def api_call(
    token: str,
    method: str,
    *,
    json_body: Optional[dict] = None,
    timeout: int = 60,
) -> dict:
    """Chiama un metodo Bot API e ritorna il dict JSON della risposta.

    Solleva SystemExit se `ok=false` nella risposta.
    """
    try:
        import requests  # type: ignore
    except ImportError:
        print("ERRORE: manca il modulo `requests`. Installa con `pip install requests`.", file=sys.stderr)
        sys.exit(2)

    url = f"{TG_API_BASE}/bot{token}/{method}"
    resp = requests.post(url, json=json_body, timeout=timeout)
    try:
        data = resp.json()
    except Exception:
        print(f"ERRORE: risposta non-JSON da {method}: HTTP {resp.status_code}", file=sys.stderr)
        print(resp.text[:500], file=sys.stderr)
        sys.exit(3)
    if not data.get("ok"):
        desc = data.get("description", "?")
        print(f"ERRORE Telegram {method}: {desc}", file=sys.stderr)
        print(f"  full response: {json.dumps(data)[:400]}", file=sys.stderr)
        sys.exit(4)
    return data


def api_upload_document(
    token: str,
    chat_id: int | str,
    file_path: Path,
    *,
    caption: Optional[str] = None,
    timeout: int = 600,
) -> dict:
    """Upload di un file via sendDocument (multipart). Ritorna la risposta."""
    try:
        import requests  # type: ignore
    except ImportError:
        print("ERRORE: manca il modulo `requests`.", file=sys.stderr)
        sys.exit(2)

    if not file_path.exists():
        print(f"ERRORE: file non trovato: {file_path}", file=sys.stderr)
        sys.exit(5)

    size = file_path.stat().st_size
    if size > LIMIT_BOT_API_BYTES:
        mb = size / 1024 / 1024
        print(
            f"ERRORE: file {file_path.name} = {mb:.1f} MB > 50 MB limite Bot API.\n"
            f"  Usa 'tg_send.py link' (HTTP server) oppure Pyrogram per file > 50 MB.\n"
            f"  Vedi SKILL.md sezione 'Strategia di selezione automatica'.",
            file=sys.stderr,
        )
        sys.exit(6)

    url = f"{TG_API_BASE}/bot{token}/sendDocument"
    with file_path.open("rb") as f:
        files = {"document": (file_path.name, f)}
        data = {"chat_id": str(chat_id)}
        if caption:
            data["caption"] = caption[:1024]   # Telegram caption hard limit
        resp = requests.post(url, data=data, files=files, timeout=timeout)
    try:
        j = resp.json()
    except Exception:
        print(f"ERRORE: risposta non-JSON: HTTP {resp.status_code}", file=sys.stderr)
        print(resp.text[:500], file=sys.stderr)
        sys.exit(3)
    if not j.get("ok"):
        desc = j.get("description", "?")
        print(f"ERRORE Telegram sendDocument: {desc}", file=sys.stderr)
        print(f"  hint: se dice 'Request Entity Too Large', il file e' > 50 MB.", file=sys.stderr)
        sys.exit(4)
    return j


# ----------------------------------------------------------------------
# Misc
# ----------------------------------------------------------------------
def fmt_size(n: int) -> str:
    """Formatta size in bytes come stringa human-readable."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024
    return f"{n:.1f} PB"


def main_smoke() -> int:
    """Smoke test: verifica solo il caricamento del token."""
    try:
        tok = load_bot_token()
        print(f"OK: token caricato ({mask_token(tok)})")
        return 0
    except SystemExit:
        return 1


if __name__ == "__main__":
    sys.exit(main_smoke())
