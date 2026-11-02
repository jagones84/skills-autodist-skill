#!/usr/bin/env bash
# telegram-file-send: verifica ambiente prima di usare la skill.
#
# Controlla:
#   - python3 + modulo requests
#   - curl e jq (per debug/manuali)
#   - TELEGRAM_BOT_TOKEN caricabile (smoke test di lib_tg.py)
#   - porte / processi noti
#
# Exit code 0 = tutto OK, !=0 = problema.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
LIB="$SCRIPT_DIR/lib_tg.py"

ok=0
fail=0

color() {
    local c=$1; shift
    case "$c" in
        red)    printf '\033[31m%s\033[0m' "$*";;
        green)  printf '\033[32m%s\033[0m' "$*";;
        yellow) printf '\033[33m%s\033[0m' "$*";;
        *)      printf '%s' "$*";;
    esac
}

check() {
    local name=$1
    local cmd=$2
    if eval "$cmd" >/dev/null 2>&1; then
        printf '  [%s] %s\n' "$(color green OK)" "$name"
        ok=$((ok+1))
    else
        printf '  [%s] %s\n' "$(color red FAIL)" "$name"
        fail=$((fail+1))
    fi
}

echo "== python =="
check "python3 presente"        "command -v python3"
check "modulo requests"          "python3 -c 'import requests'"
check "python3 >= 3.8"           "python3 -c 'import sys; assert sys.version_info >= (3,8)'"

echo
echo "== strumenti shell =="
check "curl presente"            "command -v curl"
check "jq presente"              "command -v jq"
check "ss (port check)"          "command -v ss"

echo
echo "== token bot =="
if [ -f "$HOME/.openclaw/gateway.systemd.env" ]; then
    printf '  [%s] %s\n' "$(color green OK)" "gateway.systemd.env presente: $HOME/.openclaw/gateway.systemd.env"
    ok=$((ok+1))
    if grep -q '^TELEGRAM_BOT_TOKEN=' "$HOME/.openclaw/gateway.systemd.env"; then
        printf '  [%s] %s\n' "$(color green OK)" "TELEGRAM_BOT_TOKEN definito nell'env file"
        ok=$((ok+1))
    else
        printf '  [%s] %s\n' "$(color red FAIL)" "TELEGRAM_BOT_TOKEN non presente in gateway.systemd.env"
        fail=$((fail+1))
    fi
else
    printf '  [%s] %s\n' "$(color yellow WARN)" "gateway.systemd.env NON presente (skill funziona solo se token passato via --token o TG_BOT_TOKEN env)"
fi

echo
echo "== smoke test lib_tg =="
if [ -f "$LIB" ]; then
    if python3 "$LIB" 2>&1 | grep -q '^OK:'; then
        printf '  [%s] %s\n' "$(color green OK)" "lib_tg carica il token"
        ok=$((ok+1))
    else
        printf '  [%s] %s\n' "$(color red FAIL)" "lib_tg non riesce a caricare il token"
        fail=$((fail+1))
    fi
else
    printf '  [%s] %s\n' "$(color red FAIL)" "lib_tg.py non trovato in $LIB"
    fail=$((fail+1))
fi

echo
echo "== rete =="
if command -v tailscale >/dev/null 2>&1; then
    if tailscale status >/dev/null 2>&1; then
        printf '  [%s] %s\n' "$(color green OK)" "tailscale attivo"
        ok=$((ok+1))
    else
        printf '  [%s] %s\n' "$(color yellow WARN)" "tailscale installato ma non attivo"
    fi
else
    printf '  [%s] %s\n' "$(color yellow WARN)" "tailscale non installato (Caso B userà solo LAN)"
fi

echo
echo "== porte usate =="
if command -v ss >/dev/null 2>&1; then
    if ss -tlnp 2>/dev/null | grep -q ':8000 '; then
        printf '  [%s] %s\n' "$(color yellow WARN)" "porta 8000 gia' in LISTEN (probabilmente un server http ancora attivo)"
    else
        printf '  [%s] %s\n' "$(color green OK)" "porta 8000 libera"
        ok=$((ok+1))
    fi
fi

echo
printf 'Totale: %s OK, %s FAIL\n' "$(color green "$ok")" "$(color red "$fail")"
exit $fail
