# AGENTS.md — hard rules for every manhwa phase (opencode reads this)

## Hard rules
1. Prompt-lock: every image prompt reuses `manhwa/bible/characters.md` tokens verbatim. Never paraphrase Ren Qi's description.
2. Seed-lock: panel N uses seed 777+N. Retry = seed+1, never random.
3. Free generators only, in order: Pollinations flux (no key) -> HF flux-schnell (HF_TOKEN). NEVER automate perchance.org browser (Cloudflare + ToS).
4. Dialogue is overlaid with Pillow, never baked into the image prompt.
5. Evidence gate: phase is DONE only if `panels.json` (8+) + all `out/<phase>/panelNN.jpg` >10KB exist. `opencode run` exit 0 alone is NOT done.
6. Max 3 render tries per panel, max 3 phase attempts -> `.blocked`, never infinite loop.
7. Consistent modern Solo Leveling style lock: every panel MUST include the STYLE line verbatim
   (`full color Korean webtoon style, solo leveling manhwa, clean cel shading, vertical composition, modern characters`).
   Modern Shenzhen setting only — no medieval/fantasy-armor drift, no photoreal drift, no chibi drift.
   VLM vision check rejects any panel with style/era break; fix = re-render, never edit STYLE.
