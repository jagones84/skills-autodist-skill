#!/usr/bin/env bash
# Quick wrapper for Flux Unchained NSFW generation.
# Usage: quick-flux.sh "<prompt>" [width] [height] [output_name]
#        quick-flux.sh --file /path/to/prompt.txt [width] [height] [output_name]
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/flux_and_send.py" "$@"
