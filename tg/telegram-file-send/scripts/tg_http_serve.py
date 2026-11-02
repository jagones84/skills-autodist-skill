#!/usr/bin/env python3
"""telegram-file-send: HTTP server background per Caso B (file > 50 MB).

Lancia `python3 -m http.server` bound a 0.0.0.0 su una porta configurabile,
con PID file in /tmp e log su file. Supporta start in background e stop pulito.

Uso:
  tg_http_serve.py --port 8000 --root /home/jagones/video --background
  tg_http_serve.py status
  tg_http_serve.py stop
"""
from __future__ import annotations

import argparse
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path


# ----------------------------------------------------------------------
# Costanti
# ----------------------------------------------------------------------
PID_DIR = Path("/tmp")
PID_FILE = PID_DIR / "tg_http_serve.pid"
LOG_FILE = PID_DIR / "tg_http_serve.log"


def _check_port_free(port: int) -> bool:
    """True se la porta locale e libera."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def _read_pid() -> int | None:
    if not PID_FILE.exists():
        return None
    try:
        return int(PID_FILE.read_text().strip())
    except (ValueError, OSError):
        return None


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


# ----------------------------------------------------------------------
# sub-comandi
# ----------------------------------------------------------------------
def cmd_start(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print(f"ERRORE: {root} non e' una directory.", file=sys.stderr)
        return 5

    # Se un altro server e' ancora vivo, non ne lanciamo un secondo.
    existing = _read_pid()
    if existing and _pid_alive(existing):
        print(f"ERRORE: server gia' attivo (pid {existing}). Usa 'stop' prima.", file=sys.stderr)
        return 6

    if not _check_port_free(args.port):
        print(f"ERRORE: porta {args.port} occupata.", file=sys.stderr)
        return 7

    # Scrivi PID file con un fork cosi' il processo child eredita il PID giusto.
    if not args.background:
        print(
            f"[serve] avvio http.server 0.0.0.0:{args.port} root={root}\n"
            f"[serve] premi Ctrl-C per fermare.",
            file=sys.stderr,
        )
        try:
            subprocess.run(
                [sys.executable, "-u", "-m", "http.server", str(args.port), "--bind", "0.0.0.0"],
                cwd=str(root),
                check=True,
            )
        except KeyboardInterrupt:
            print("\n[serve] interrotto.", file=sys.stderr)
            return 0
        return 0

    # Background mode: nohup-like con log su file
    LOG_FILE.touch(exist_ok=True)
    log_fd = open(LOG_FILE, "ab", buffering=0)
    proc = subprocess.Popen(
        [sys.executable, "-u", "-m", "http.server", str(args.port), "--bind", "0.0.0.0"],
        cwd=str(root),
        stdout=log_fd,
        stderr=log_fd,
        stdin=subprocess.DEVNULL,
        preexec_fn=os.setpgrp,    # nuovo pgid cosi' il parent puo' terminare i figli
    )
    PID_FILE.write_text(str(proc.pid))
    print(f"[serve] avviato pid={proc.pid} port={args.port} root={root}")
    print(f"[serve] log={LOG_FILE}  pidfile={PID_FILE}")

    # Aspetta 1 secondo e verifica che sia effettivamente vivo
    time.sleep(1.0)
    if not _pid_alive(proc.pid):
        print(f"ERRORE: processo {proc.pid} e' morto subito. Vedi {LOG_FILE}.", file=sys.stderr)
        PID_FILE.unlink(missing_ok=True)
        return 8

    print(f"[serve] OK. Sulla LAN prova: http://<lan-ip>:{args.port}/")
    print(f"[serve] Tailscale: http://<tailscale-ip>:{args.port}/")
    return 0


def cmd_stop(args: argparse.Namespace) -> int:
    pid = _read_pid()
    if not pid:
        print("[stop] nessun pid file, niente da fare.")
        return 0
    if not _pid_alive(pid):
        print(f"[stop] pid {pid} non e' vivo. Pulisco pid file.")
        PID_FILE.unlink(missing_ok=True)
        return 0

    # Termina il process group (preexec_fn=setpgrp) per pulire anche eventuali figli
    try:
        os.killpg(pid, signal.SIGTERM)
    except OSError as e:
        print(f"[stop] SIGTERM fallita per {pid}: {e}. Provo SIGKILL.", file=sys.stderr)
        try:
            os.killpg(pid, signal.SIGKILL)
        except OSError:
            pass

    # Aspetta che muoia
    for _ in range(20):
        if not _pid_alive(pid):
            break
        time.sleep(0.1)
    else:
        print(f"[stop] WARNING: pid {pid} ancora vivo dopo SIGTERM.", file=sys.stderr)

    PID_FILE.unlink(missing_ok=True)
    print(f"[stop] fermato pid={pid}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    pid = _read_pid()
    if not pid:
        print("[status] nessun pid file.")
        return 1
    if _pid_alive(pid):
        print(f"[status] ATTIVO pid={pid}  log={LOG_FILE}")
        return 0
    print(f"[status] pid file presente ma processo {pid} non e' vivo.")
    PID_FILE.unlink(missing_ok=True)
    return 1


# ----------------------------------------------------------------------
# argparse
# ----------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="tg_http_serve",
                                description="HTTP server background per Caso B.")
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("start", help="avvia http.server in background (o foreground)")
    ps.add_argument("--port", type=int, default=8000, help="porta (default 8000)")
    ps.add_argument("--root", required=True, help="directory di root del server")
    ps.add_argument("--background", action="store_true",
                    help="lancia in background con PID/log file (default: foreground)")
    ps.set_defaults(func=cmd_start)

    pt = sub.add_parser("stop", help="ferma il server in background")
    pt.set_defaults(func=cmd_stop)

    pq = sub.add_parser("status", help="mostra se il server e' attivo")
    pq.set_defaults(func=cmd_status)

    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
