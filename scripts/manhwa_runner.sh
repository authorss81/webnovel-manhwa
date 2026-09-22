#!/usr/bin/env bash
# manhwa_runner.sh <phase> — llops-style: model chain + PROMPT.md + evidence gate.
set -uo pipefail
PHASE="${1:-}"; [ -z "$PHASE" ] && { echo "ERROR: no phase"; exit 2; }
PD="workspace/$PHASE"; LOG="logs/$PHASE.log"; mkdir -p logs "out/$PHASE"
MAX_ATTEMPTS=3

# vision-capable free fallback chain (image input): spark-1.3 first
IFS=',' read -ra MODELS <<< "${OPENCODE_MODEL:-opencode/muse-spark-1.3-contributor-free,opencode/gemini-3-flash,opencode/deepseek-v4-flash-vision-exp,opencode/kimi-k2.5,opencode/muse-spark-1.2-contributor-free}"

[ -f "$PD/PROMPT.md" ] || { echo "ERROR: no PROMPT.md for $PHASE"; exit 2; }
[ -f "$PD/.done" ] && { echo "$PHASE already DONE — skip"; exit 0; }

# attempts cap -> .blocked (stops infinite auto-trigger loop)
ATT=0; [ -f "$PD/.attempts" ] && ATT=$(cat "$PD/.attempts" 2>/dev/null || echo 0)
if [ "$ATT" -ge "$MAX_ATTEMPTS" ]; then echo "$PHASE BLOCKED after $ATT"; touch "$PD/.blocked"; exit 3; fi

run_models() { # $1=logfile, rest=opencode args; tries chain, 429/model-error advances
  local log="$1"; shift; : > "$log"
  for m in "${MODELS[@]}"; do
    echo "== trying $m ==" >> "$log"
    if opencode run --model "$m" "$@" >> "$log" 2>&1; then echo "== $m OK =="; return 0; fi
    if grep -qiE "429|rate.?limit|quota|model not found|unknown model|overloaded|502|503" "$log"; then
      echo "== $m unusable — next =="; continue
    fi
    return 1
  done
  return 1
}

if [ -z "${OPENCODE_API_KEY:-}" ]; then
  echo "WARN: no OPENCODE_API_KEY — python fallback render (no VLM judge)"
  python3 scripts/render.py "$PHASE"; python3 scripts/judge.py "$PHASE" && touch "$PD/.done" || echo $((ATT+1)) > "$PD/.attempts"
  exit 0
fi

# 1) opencode writes panels.json + renders via prompt (PROMPT.md is the instruction)
run_models "$LOG" --agent build --title "manhwa-$PHASE" < "$PD/PROMPT.md" || true
python3 scripts/render.py "$PHASE" || true

# 2) consistency retry: judge (file/size gate) + VLM vision check on 2 panels
if ! python3 scripts/judge.py "$PHASE"; then echo $((ATT+1)) > "$PD/.attempts"; exit 1; fi
FIRST=$(ls "out/$PHASE"/panel*.jpg 2>/dev/null | head -2 | tr '\n' ' ')
if [ -n "$FIRST" ]; then
  run_models "logs/$PHASE.vision.log" --agent build \
    "Vision consistency check for $PHASE. Look at images: $FIRST and character ref manhwa/bible/characters.md. Score face/hair/clothes 0-10. If any <7, edit ONLY shot/lighting in workspace/$PHASE/panels.json (keep locked Ren Qi tokens), bump seed+1, then run python3 scripts/render.py $PHASE again (max 3 tries total)." || true
  python3 scripts/judge.py "$PHASE" || { echo $((ATT+1)) > "$PD/.attempts"; exit 1; }
fi

# 3) evidence gate (like llops tree_work): panels + jpgs must exist
N=$(python3 -c "import json;print(len(json.load(open('$PD/panels.json'))))" 2>/dev/null || echo 0)
BAD=$(find "out/$PHASE" -name 'panel*.jpg' -size -10k 2>/dev/null | wc -l)
if [ "$N" -ge 8 ] && [ "$BAD" -eq 0 ]; then rm -f "$PD/.attempts"; touch "$PD/.done"; echo "DONE $PHASE"; exit 0; fi
echo $((ATT+1)) > "$PD/.attempts"; echo "EVIDENCE-FAIL $PHASE panels=$N bad=$BAD"; exit 1
