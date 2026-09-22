#!/usr/bin/env bash
# manhwa_runner.sh <phase> — called by 02-manhwa.yml and locally.
set -e
PHASE="$1"
echo "=== manhwa $PHASE ==="
python3 scripts/render.py "$PHASE" || true
python3 scripts/judge.py "$PHASE" || true
# mark done if all panels pass (judge exit 0)
if python3 scripts/judge.py "$PHASE"; then
  touch "workspace/$PHASE/.done"
  echo "DONE $PHASE"
else
  echo "NEEDS-RETRY $PHASE (max 3 tries enforced by workflow attempts file)"
fi
