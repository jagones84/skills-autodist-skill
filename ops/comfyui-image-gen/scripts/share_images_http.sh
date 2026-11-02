#!/bin/bash
# share_images_http.sh - start a LAN-bound HTTP image server for previewing output PNGs.
#
# Usage:
#   share_images_http.sh                # default port 8765, output dir
#   share_images_http.sh 9000           # custom port
#   share_images_http.sh 9000 /path/to/dir
#
# Output: prints the LAN URL(s) to open from any device on the same network.
# Stops with Ctrl-C or by running share_images_stop.sh.

set -e

PORT="${1:-8765}"
DIR="${2:-/home/jagones/ComfyUI/output}"
LOG=/tmp/imgserver.log
PIDFILE=/tmp/imgserver.pid

# Stop any previous instance
if [ -f "$PIDFILE" ]; then
  OLDPID=$(cat "$PIDFILE" 2>/dev/null || true)
  if [ -n "$OLDPID" ] && kill -0 "$OLDPID" 2>/dev/null; then
    kill "$OLDPID" 2>/dev/null || true
    sleep 1
  fi
  rm -f "$PIDFILE"
fi

# Find LAN IP (best guess)
LAN_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || true)
[ -z "$LAN_IP" ] && LAN_IP=$(ip -4 addr show 2>/dev/null | awk '/inet / && $2 !~ /^127/ {print $2; exit}' | cut -d/ -f1)

# Start server in background
nohup python3 -m http.server "$PORT" --bind 0.0.0.0 --directory "$DIR" > "$LOG" 2>&1 < /dev/null &
echo $! > "$PIDFILE"
disown
sleep 1

# Sanity check
if ! kill -0 "$(cat $PIDFILE)" 2>/dev/null; then
  echo "ERROR: server failed to start, see $LOG" >&2
  cat "$LOG" >&2
  exit 1
fi

echo "==============================================="
echo "  HTTP image server started"
echo "  PID:       $(cat $PIDFILE)"
echo "  Port:      $PORT"
echo "  Dir:       $DIR"
echo "  Log:       $LOG"
echo "  LAN URL:   http://$LAN_IP:$PORT/"
echo "==============================================="
echo ""
echo "Open from a phone on the same WiFi:"
echo "  http://$LAN_IP:$PORT/AIGEN_QWEN_NSFW_T2I_00001_.png"
echo ""
echo "Stop with: share_images_stop.sh"
