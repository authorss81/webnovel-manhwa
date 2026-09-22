# Chapter 44: Market Manipulation (phase-044) — manhwa adaptation task for opencode

Read FIRST: `manhwa/bible/characters.md` (locked characters below), `AGENTS.md` (hard rules),
`workspace/phase-044/source.txt` (chapter text), `workspace/phase-044/meta.json`.

## Currently locked characters
- REN_QI: young Chinese male structural engineer, age 24, short black hair, grey hoodie and jeans, determined tired eyes

## Step 1 — character detection (do this BEFORE writing panels.json)
Read the chapter text. For every named character who appears and is NOT already
in the locked list above:
  1. Write a short physical description (age, build, hair, distinctive clothing —
     things a portrait artist needs, not personality).
  2. Lock them in with: `python3 scripts/bible.py add "<NAME>" "<description>"`
  3. Do this ONCE per character, ever. Never re-describe or edit an already-locked
     character — reuse their exact desc from the list above verbatim in future panels.

## Step 2 — write workspace/phase-044/panels.json
A JSON list of 8-12 panel objects, each shaped exactly like this:

```json
{
  "id": 1,
  "scene": "rooftop, night, rain starting",
  "characters": ["REN_QI"],
  "action": "standing at the railing, gripping it, wind blowing",
  "camera": "wide establishing, low angle",
  "panel_size": "medium",
  "dialogue": [
    {"speaker": "REN_QI", "line": "I have to go down."}
  ],
  "seed": 778
}
```

Rules:
- `characters`: list of LOCKED NAMEs (from Step 1) appearing in this panel. List the
  most visually important character FIRST — they get the strongest consistency
  treatment during rendering (image-reference conditioning), so put whoever the
  panel is actually about first, not a minor background character.
- `panel_size`: "small" (quick beat/reaction), "medium" (default), or "splash"
  (a key story beat — use sparingly, 1-2 per chapter, for pacing impact).
- `dialogue`: a LIST of `{"speaker": "NAME", "line": "..."}` objects — use
  MULTIPLE entries for a back-and-forth exchange in one panel. For pure narration
  with no speaker, use `{"speaker": null, "line": "..."}`. Keep each line short —
  webtoon bubbles, not narration dumps. Take dialogue from source.txt, don't invent.
- Never bake dialogue text into `action`/`scene`/`camera` — those become the image
  prompt; dialogue is rendered separately as bubbles at assembly time.
- `seed`: 777 + panel id, never random (seed-lock rule).

## Step 3 — render and check
Run: `python3 scripts/render.py phase-044` then `python3 scripts/judge.py phase-044`.
If judge reports a panel needs retry, DO NOT just bump the seed and hope — use
`python3 scripts/render.py fix phase-044 <panel_id> "<specific correction, e.g.
'face doesn't match reference, fix hairstyle and jawline to match, keep pose'>"`
so the fix targets what's actually wrong.

DONE = `panels.json` has 8+ panels AND `out/phase-044/panelNN.jpg` all exist >10KB
AND (if OPENCODE_API_KEY is set) the vision-eval pass in manhwa_runner.sh is clean.
