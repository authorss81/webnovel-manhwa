# AGENTS.md — hard rules for every manhwa phase (opencode reads this)

## Hard rules
1. Character-lock: every character gets ONE locked desc + ONE locked reference
   image in `manhwa/bible/characters.md`, created the first time they appear.
   Never re-describe or edit an already-locked character. New chapters reuse
   the exact desc tokens verbatim — see `scripts/bible.py`.
2. Character consistency comes from image-reference conditioning (FLUX.1
   Kontext, editing the locked reference image per panel), NOT from
   seed+prompt-text alone. `scripts/render.py` handles this automatically —
   don't bypass it by calling a plain text-to-image endpoint directly.
3. Seed-lock: panel N uses seed 777+N. Retry = seed+1, never random.
4. Free generators only, in order: HF Kontext-dev (character reference edit,
   needs HF_TOKEN) -> Pollinations flux text2img (no key) -> HF flux-schnell
   text2img (HF_TOKEN). NEVER automate perchance.org browser (Cloudflare + ToS).
5. Dialogue is data (panels.json `dialogue` list), overlaid as bubbles by
   `bundle.py`, NEVER baked into the image generation prompt.
6. Evidence gate: phase is DONE only if `panels.json` (8+) + all
   `out/<phase>/panelNN.jpg` >10KB exist AND (when OPENCODE_API_KEY is set)
   the itemized vision-eval in `manhwa_runner.sh` reports no bad panels.
   `opencode run` exit 0 alone is NOT done.
7. Max 2 fix attempts per panel, max 3 phase attempts -> `.blocked`, never
   infinite loop. A fix EDITS the existing panel image with a specific
   correction — it does not regenerate from scratch.
8. Style lock: every panel MUST include the STYLE line from
   `manhwa/bible/characters.md` verbatim. The style is described generically
   (ink linework, cel shading, vertical composition) — it does NOT name any
   specific commercial series. Do not reintroduce a named-series style lock;
   naming a specific copyrighted work's style in every generated prompt is
   a real IP-mimicry risk once this pipeline is capable of decent output.
9. `workspace/.stop` halts everything, including the 15-minute cron ticker
   (see `.github/workflows/03-manhwa-tick.yml`) — check for it before doing
   any work, not just at phase-selection time.
10. Before adapting any source novel at scale, confirm you have the right to
    adapt and (if the pipeline auto-publishes) distribute it. State files for
    third-party platforms belong in `.gitignore`, not in an assumption that
    scraping = permission.
