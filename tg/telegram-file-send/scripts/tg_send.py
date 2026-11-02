#!/usr/bin/env python3
"""telegram-file-send: CLI principale.

Sub-comandi:
  send   - invia un file < 50 MB come allegato (sendDocument)
  link   - invia un link HTTP per un file > 50 MB (HTTP server + sendMessage)
  text   - invia solo testo (utile per ping/test)

Esempi:
  tg_send.py send --file ./report.pdf --caption "ecco il report"
  tg_send.py text --text "ping"
  tg_send.py link --file-relative bigfile.mp4 --root /home/jagones/video
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lib_tg import (
    DEFAULT_CHAT_ID,
    DEFAULT_BOT_NAME,
    api_call,
    api_upload_document,
    fmt_size,
    load_bot_token,
    mask_token,
)


# ----------------------------------------------------------------------
# sub-comando: send (allegato < 50MB)
# ----------------------------------------------------------------------
def cmd_send(args: argparse.Namespace) -> int:
    token = load_bot_token(args.token)
    file_path = Path(args.file).expanduser().resolve()

    if not file_path.is_file():
        print(f"ERRORE: {file_path} non e' un file regolare.", file=sys.stderr)
        return 5

    size = file_path.stat().st_size
    print(f"[send] file={file_path}  size={fmt_size(size)}  bot={DEFAULT_BOT_NAME}  chat={args.chat}")
    print(f"[send] token={mask_token(token)}")

    result = api_upload_document(
        token,
        chat_id=args.chat,
        file_path=file_path,
        caption=args.caption,
    )

    msg = result["result"]
    doc = msg.get("document", {})
    print(f"OK: message_id={msg['message_id']}  file_id={doc.get('file_id', '?')}  "
          f"file_name={doc.get('file_name', file_path.name)}")
    return 0


# ----------------------------------------------------------------------
# sub-comando: link (per file > 50MB via HTTP server)
# ----------------------------------------------------------------------
def cmd_link(args: argparse.Namespace) -> int:
    token = load_bot_token(args.token)

    # URL da costruire:
    #   se --tailscale-ip e' passato, costruisco entrambi gli URL
    #   altrimenti solo quello fornito.
    rel = args.file_relative.lstrip("/")
    url_paths = []
    if args.lan_ip:
        url_paths.append(f"http://{args.lan_ip}:{args.port}/{rel}")
    if args.tailscale_ip:
        url_paths.append(f"http://{args.tailscale_ip}:{args.port}/{rel}")
    if not url_paths:
        print("ERRORE: serve almeno --lan-ip o --tailscale-ip.", file=sys.stderr)
        return 5

    lines = [args.text_prefix or "Download pronto.", ""]
    for u in url_paths:
        lines.append(f"- {u}")
    text = "\n".join(lines)

    print(f"[link] invio a chat {args.chat}, {len(url_paths)} URL")
    result = api_call(
        token,
        "sendMessage",
        json_body={
            "chat_id": args.chat,
            "text": text,
            "disable_web_page_preview": True,
        },
    )
    print(f"OK: message_id={result['result']['message_id']}")
    return 0


# ----------------------------------------------------------------------
# sub-comando: text (solo testo)
# ----------------------------------------------------------------------
def cmd_text(args: argparse.Namespace) -> int:
    token = load_bot_token(args.token)
    print(f"[text] invio a chat {args.chat}: {args.text!r}")
    result = api_call(
        token,
        "sendMessage",
        json_body={"chat_id": args.chat, "text": args.text},
    )
    print(f"OK: message_id={result['result']['message_id']}")
    return 0


# ----------------------------------------------------------------------
# argparse
# ----------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tg_send",
        description="Invia file o testo al telefono via Telegram Bot API.",
    )
    p.add_argument("--chat", type=int, default=DEFAULT_CHAT_ID,
                   help=f"chat_id destinatario (default: {DEFAULT_CHAT_ID})")
    p.add_argument("--token", default=None,
                   help="bot token (default: auto-load da ~/.openclaw/gateway.systemd.env)")

    sub = p.add_subparsers(dest="cmd", required=True)

    # send
    ps = sub.add_parser("send", help="invia un file < 50 MB come allegato")
    ps.add_argument("--file", required=True, help="path del file da inviare")
    ps.add_argument("--caption", default=None, help="caption sotto l'allegato (max 1024 char)")
    ps.set_defaults(func=cmd_send)

    # link
    pl = sub.add_parser("link", help="invia link HTTP (per file > 50 MB)")
    pl.add_argument("--file-relative", required=True,
                    help="path relativo del file dalla root del server (es: video/out.mp4)")
    pl.add_argument("--port", type=int, default=8000, help="porta del server (default 8000)")
    pl.add_argument("--lan-ip", default=None, help="IP LAN del server (es: 192.168.1.11)")
    pl.add_argument("--tailscale-ip", default=None,
                    help="IP Tailscale del server (es: 100.76.251.9)")
    pl.add_argument("--text-prefix", default=None, help="testo prima degli URL")
    pl.set_defaults(func=cmd_link)

    # text
    pt = sub.add_parser("text", help="invia solo testo (ping/test)")
    pt.add_argument("--text", required=True, help="testo del messaggio")
    pt.set_defaults(func=cmd_text)

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\ninterrotto.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
