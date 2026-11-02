#!/bin/bash
# share_images_stop.sh - kill the local image HTTP server and the cloudflared
# tunnel started by share_images_http.sh / share_images_tunnel.sh.

HTTP_PIDFILE=/tmp/imgserver.pid
CF_PIDFILE=/tmp/cf_tunnel.pid

stop_one() {
  local pf="$1"
  local name="$2"
  if [ -f "$pf" ]; then
    local pid
    pid=$(cat "$pf" 2>/dev/null || true)
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      sleep 1
      kill -9 "$pid" 2>/dev/null || true
      echo "Stopped $name (PID $pid)"
    else
      echo "$name already not running"
    fi
    rm -f "$pf"
  else
    echo "$name: no pidfile, nothing to stop"
  fi
}

stop_one "$HTTP_PIDFILE" "HTTP server"
stop_one "$CF_PIDFILE"   "Cloudflare tunnel"
rm -f /tmp/cf_tunnel_url.txt
