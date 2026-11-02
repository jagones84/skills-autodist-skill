#!/usr/bin/env bash
# Dated snapshot of the local skill store (the store is DATA, gitignored).
#
# The store is the single live copy for the 79 vendored skills, so this archive
# is the only safety net. Run it before any risky operation (mass adopt, repair,
# migration, harness re-apply).
#
# Usage:  bash scripts/store-snapshot.sh
set -euo pipefail

STORE="/home/jagones/Repositories/skills-autodist-skill"
DEST="/home/jagones/backups/skills-store-snapshots"
CATS="android data dev lark launchfast media meta mobile omh ops research tg"

mkdir -p "$DEST"
STAMP="$(date +%Y%m%d_%H%M)"
OUT="$DEST/store-$STAMP.tar.gz"

# shellcheck disable=SC2086
tar -czf "$OUT" -C "$STORE" \
  --exclude='.agent' --exclude='__pycache__' --exclude='.pytest_cache' \
  $CATS

echo "snapshot: $OUT"
ls -lh "$OUT"
echo "payload entries: $(tar -tzf "$OUT" | grep -c '/SKILL\.md$')"
echo "keep the last 10:" 
ls -1t "$DEST"/store-*.tar.gz | tail -n +11 | while read -r old; do
  rm -f "$old"
  echo "  pruned $old"
done
ls -1t "$DEST" | head -5