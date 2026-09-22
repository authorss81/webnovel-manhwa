# Chapter 3: The Fog That Breathes (phase-003) — manhwa adaptation task for opencode

Read FIRST: `manhwa/bible/characters.md` (locked tokens), `AGENTS.md` (hard rules),
`workspace/phase-003/source.txt` (chapter text), `workspace/phase-003/meta.json`.

DO:
1. Write 8-12 panels to `workspace/phase-003/panels.json` as list of
   {"id": N, "shot": "...", "prompt": "...", "dialogue": "...", "seed": 777+N}.
2. Every prompt MUST contain verbatim: `young Chinese male structural engineer Ren Qi, age 24, short black hair, grey hoodie and jeans`
   plus `full color Korean webtoon style, solo leveling manhwa, clean cel shading, vertical composition, modern characters`.
3. Only vary shot/action/lighting. Never change hair/clothes/age words.
4. Dialogue from source.txt, short webtoon bubbles, no narration dumps.
5. Then run: `python3 scripts/render.py phase-003` and `python3 scripts/judge.py phase-003`.
   If judge reports retry, edit ONLY shot/lighting words in that panel's prompt (keep locked tokens), bump seed+1, re-render max 3 tries.

DONE = `panels.json` has 8+ panels AND `out/phase-003/panelNN.jpg` all exist >10KB.
