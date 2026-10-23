#!/usr/bin/env bash
# Demo autosufficiente: semina i file JSON di esempio in examples/out/ e applica il config.
# Non tocca $HOME. Uso: bash examples/run-demo.sh [--dry-run|--report]
set -euo pipefail

cd "$(dirname "$0")/.."          # root del repo

mkdir -p examples/out
cp examples/seed/demo-agent.json    examples/out/demo-agent.json
cp examples/seed/demo-openclaw.json examples/out/demo-openclaw.json

python3 scripts/redistribute.py --config examples/redistribution.example.yaml "$@"
