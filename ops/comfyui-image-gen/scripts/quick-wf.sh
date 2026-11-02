#!/usr/bin/env bash
# Quick wrapper for the universal workflow_files/graphs launcher.
# Usage: quick-wf.sh <wf_short_name> "<prompt>" [width] [height] [out.png]
#        quick-wf.sh list
#        quick-wf.sh <wf_short_name> --image /path/src.png "<prompt>" ...
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/run_wf.py" "$@"
