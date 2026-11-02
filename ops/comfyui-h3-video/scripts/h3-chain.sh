#!/usr/bin/env bash
# h3-chain.sh - passthrough all'orchestratore di catena MiniMax-H3.
set -euo pipefail
exec python3 /home/jagones/Repositories/comfyui-mcp/workflow_files/runners/h3_chain.py "$@"
