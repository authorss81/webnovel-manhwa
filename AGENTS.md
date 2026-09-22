# AGENTS.md — hard rules for every manhwa phase (opencode reads this)

## Hard rules
1. Prompt-lock: every image prompt reuses `manhwa/bible/characters.md` tokens verbatim. Never paraphrase Ren Qi's description.
2. Seed-lock: panel N uses seed 777+N. Retry = seed+1, never random.
3. Free generators only, in order: Pollinations flux (no key) -> HF flux-schnell (HF_TOKEN). NEVER automate perchance.org browser (Cloudflare + ToS).
4. Dialogue is overlaid with Pillow, never baked into the image prompt.
5. Evidence gate: phase is DONE only if `panels.json` (8+) + all `out/<phase>/panelNN.jpg` >10KB exist. `opencode run` exit 0 alone is NOT done.
6. Max 3 render tries per panel, max 3 phase attempts -> `.blocked`, never infinite loop.
