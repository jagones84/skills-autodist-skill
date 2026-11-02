#!/usr/bin/env bash
# h3-run.sh - passthrough al runner canonico MiniMax-H3 (un blocco). Vedi SKILL.md.
set -euo pipefail
exec python3 /home/jagones/Repositories/comfyui-mcp/workflow_files/runners/h3_run.py "$@"
