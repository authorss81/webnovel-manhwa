#!/usr/bin/env bash
# manhwa_runner.sh <phase> — write panels -> render (reference-conditioned) ->
# itemized vision-eval on EVERY panel -> targeted fix -> re-check -> assemble.
set -uo pipefail
PHASE="${1:-}"; [ -z "$PHASE" ] && { echo "ERROR: no phase"; exit 2; }
PD="workspace/$PHASE"; LOG="logs/$PHASE.log"; mkdir -p logs "out/$PHASE"
MAX_PHASE_ATTEMPTS=3
MAX_PANEL_FIX_ATTEMPTS=2

[ -f workspace/.stop ] && { echo "workspace/.stop present — halting, not running $PHASE"; exit 0; }

IFS=',' read -ra MODELS <<< "${OPENCODE_MODEL:-opencode/muse-spark-1.3-contributor-free,opencode/gemini-3-flash,opencode/deepseek-v4-flash-vision-exp,opencode/kimi-k2.5,opencode/muse-spark-1.2-contributor-free}"

[ -f "$PD/PROMPT.md" ] || { echo "ERROR: no PROMPT.md for $PHASE"; exit 2; }
[ -f "$PD/.done" ] && { echo "$PHASE already DONE — skip"; exit 0; }

ATT=0; [ -f "$PD/.attempts" ] && ATT=$(cat "$PD/.attempts" 2>/dev/null || echo 0)
if [ "$ATT" -ge "$MAX_PHASE_ATTEMPTS" ]; then echo "$PHASE BLOCKED after $ATT"; touch "$PD/.blocked"; exit 3; fi

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
  echo "WARN: no OPENCODE_API_KEY — deterministic render/judge only, no vision-eval or auto character-lock"
  python3 scripts/render.py "$PHASE"
  python3 scripts/judge.py "$PHASE" && touch "$PD/.done" || echo $((ATT+1)) > "$PD/.attempts"
  python3 scripts/bundle.py "$PHASE" || true
  exit 0
fi

# 1) opencode: character-detection + writes panels.json (see PROMPT.md for schema)
run_models "$LOG" --agent build --title "manhwa-$PHASE" < "$PD/PROMPT.md" || true

# 2) reference-conditioned render (generates any missing character refs first)
python3 scripts/render.py "$PHASE" || true

# 3) deterministic evidence gate (file existence/size, panel count)
if ! python3 scripts/judge.py "$PHASE"; then echo $((ATT+1)) > "$PD/.attempts"; exit 1; fi

# 4) itemized vision-eval on EVERY panel (not a fixed subset) + targeted fixes
N_PANELS=$(python3 -c "import json;print(len(json.load(open('$PD/panels.json'))))" 2>/dev/null || echo 0)
run_models "logs/$PHASE.vision.log" --agent build "
For phase $PHASE, evaluate EVERY panel in out/$PHASE/panel*.jpg (there are $N_PANELS)
against workspace/$PHASE/panels.json and the character reference images listed in
manhwa/bible/characters.md for each panel's characters list.

For each panel, score 0-10: identity_match (does the character actually match their
reference image — face, hair, outfit), scene_fidelity (matches scene/action text),
style_adherence (matches the STYLE line in characters.md), anatomy_sanity (no
extra limbs / warped hands / broken proportions). Also flag contains_garbled_text
(true/false — diffusion models sometimes bake illegible text into the image).

Write the full array to workspace/$PHASE/vision_scores.json as:
[{\"id\": N, \"identity_match\": 0-10, \"scene_fidelity\": 0-10, \"style_adherence\": 0-10, \"anatomy_sanity\": 0-10, \"contains_garbled_text\": bool, \"region\": \"top-left|top-right|center-left|center-right|bottom-left|bottom-right (approx head position of the primary speaker, for bubble placement)\"}, ...]

Then for any panel where identity_match < 7 OR anatomy_sanity < 6, run:
  python3 scripts/render.py fix $PHASE <panel_id> \"<specific correction describing exactly what's wrong>\"
up to $MAX_PANEL_FIX_ATTEMPTS times per panel, re-reading the fixed image before deciding
whether to fix again. Do not regenerate from scratch — the fix command edits the
existing image, which preserves what's already correct about it.

Also write workspace/$PHASE/panels.json back with a top-level \"regions\" object
per panel (e.g. panel[\"regions\"] = {\"REN_QI\": \"top-left\"}) using the region
field above, so bundle.py can place speech bubbles near the right character.
" || true

# 5) re-run deterministic judge (now folds in vision_scores.json if present)
python3 scripts/judge.py "$PHASE" || { echo $((ATT+1)) > "$PD/.attempts"; exit 1; }

# 6) evidence gate: panel count + no bad panels
N=$(python3 -c "import json;print(len(json.load(open('$PD/panels.json'))))" 2>/dev/null || echo 0)
BAD=$(python3 -c "
import json
try:
    r = json.load(open('out/$PHASE/score.json'))
    print(sum(1 for x in r if x.get('retry')))
except Exception:
    print(999)
")
if [ "$N" -ge 8 ] && [ "$BAD" -eq 0 ]; then
  rm -f "$PD/.attempts"
  python3 scripts/bundle.py "$PHASE" || true
  touch "$PD/.done"; echo "DONE $PHASE"; exit 0
fi
echo $((ATT+1)) > "$PD/.attempts"; echo "EVIDENCE-FAIL $PHASE panels=$N bad=$BAD"; exit 1
