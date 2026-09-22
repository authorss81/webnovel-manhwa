#!/usr/bin/env python3
"""01 - EPUB(s) -> workspace/phase-NNN (one chapter each). Idempotent via hash."""
import zipfile, re, json, hashlib, html, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bible

ROOT = Path(__file__).resolve().parent.parent
NOVELS = ROOT / "novels"
WS = ROOT / "workspace"
WS.mkdir(exist_ok=True)


def clean_text(xhtml: bytes) -> tuple[str, str]:
    s = xhtml.decode("utf-8", "ignore")
    m = re.search(r"<h1[^>]*>(.*?)</h1>", s, re.S | re.I)
    title = html.unescape(re.sub(r"<[^>]+>", "", m.group(1)).strip()) if m else "Untitled"
    paras = re.findall(r"<p[^>]*>(.*?)</p>", s, re.S | re.I)
    out = []
    for p in paras:
        t = html.unescape(re.sub(r"<[^>]+>", "", p).replace("\n", " ").strip())
        t = re.sub(r"\s+", " ", t)
        if len(t) > 20:
            out.append(t)
    return title, "\n\n".join(out)


def prompt_md(d: Path, title: str) -> str:
    known = bible.parse_characters()
    known_list = "\n".join(f"- {n}: {c['desc']}" for n, c in known.items()) or "(none locked yet)"
    return f"""# {title} ({d.name}) — manhwa adaptation task for opencode

Read FIRST: `manhwa/bible/characters.md` (locked characters below), `AGENTS.md` (hard rules),
`workspace/{d.name}/source.txt` (chapter text), `workspace/{d.name}/meta.json`.

## Currently locked characters
{known_list}

## Step 1 — character detection (do this BEFORE writing panels.json)
Read the chapter text. For every named character who appears and is NOT already
in the locked list above:
  1. Write a short physical description (age, build, hair, distinctive clothing —
     things a portrait artist needs, not personality).
  2. Lock them in with: `python3 scripts/bible.py add "<NAME>" "<description>"`
  3. Do this ONCE per character, ever. Never re-describe or edit an already-locked
     character — reuse their exact desc from the list above verbatim in future panels.

## Step 2 — write workspace/{d.name}/panels.json
A JSON list of 8-12 panel objects, each shaped exactly like this:

```json
{{
  "id": 1,
  "scene": "rooftop, night, rain starting",
  "characters": ["REN_QI"],
  "action": "standing at the railing, gripping it, wind blowing",
  "camera": "wide establishing, low angle",
  "panel_size": "medium",
  "dialogue": [
    {{"speaker": "REN_QI", "line": "I have to go down."}}
  ],
  "seed": 778
}}
```

Rules:
- `characters`: list of LOCKED NAMEs (from Step 1) appearing in this panel. List the
  most visually important character FIRST — they get the strongest consistency
  treatment during rendering (image-reference conditioning), so put whoever the
  panel is actually about first, not a minor background character.
- `panel_size`: "small" (quick beat/reaction), "medium" (default), or "splash"
  (a key story beat — use sparingly, 1-2 per chapter, for pacing impact).
- `dialogue`: a LIST of `{{"speaker": "NAME", "line": "..."}}` objects — use
  MULTIPLE entries for a back-and-forth exchange in one panel. For pure narration
  with no speaker, use `{{"speaker": null, "line": "..."}}`. Keep each line short —
  webtoon bubbles, not narration dumps. Take dialogue from source.txt, don't invent.
- Never bake dialogue text into `action`/`scene`/`camera` — those become the image
  prompt; dialogue is rendered separately as bubbles at assembly time.
- `seed`: 777 + panel id, never random (seed-lock rule).

## Step 3 — render and check
Run: `python3 scripts/render.py {d.name}` then `python3 scripts/judge.py {d.name}`.
If judge reports a panel needs retry, DO NOT just bump the seed and hope — use
`python3 scripts/render.py fix {d.name} <panel_id> "<specific correction, e.g.
'face doesn't match reference, fix hairstyle and jawline to match, keep pose'>"`
so the fix targets what's actually wrong.

DONE = `panels.json` has 8+ panels AND `out/{d.name}/panelNN.jpg` all exist >10KB
AND (if OPENCODE_API_KEY is set) the vision-eval pass in manhwa_runner.sh is clean.
"""


def phases_from_epub(epub: Path) -> int:
    z = zipfile.ZipFile(epub)
    chs = sorted([n for n in z.namelist() if re.search(r"chapter_\d+\.xhtml", n)],
                 key=lambda x: int(re.search(r"chapter_(\d+)", x).group(1)))
    n = 0
    for ch in chs:
        raw = z.read(ch)
        h = hashlib.sha256(raw).hexdigest()[:16]
        title, text = clean_text(raw)
        if not text:
            continue
        chap = int(re.search(r"chapter_(\d+)", ch).group(1))
        d = WS / f"phase-{chap:03d}"
        d.mkdir(exist_ok=True)
        hf = d / ".source_hash"
        same = hf.exists() and hf.read_text().strip() == h
        if not same:
            (d / "source.txt").write_text(f"{title}\n\n{text}", encoding="utf-8")
            (d / "meta.json").write_text(json.dumps({
                "book": epub.name, "chapter_file": ch, "title": title,
                "phase": d.name, "chars": len(text)}, indent=2), encoding="utf-8")
            hf.write_text(h, encoding="utf-8")
            print(f"wrote {d.name}: {title} ({len(text)} chars)")
        if not (d / "panels.json").exists():
            (d / "panels.json").write_text("[]", encoding="utf-8")
        (d / ".timeout").write_text("150", encoding="utf-8")  # bumped: Kontext + per-panel vision eval is slower than flux-schnell alone
        (d / "PROMPT.md").write_text(prompt_md(d, title), encoding="utf-8")
        n += 1
    return n


def main():
    bible.ensure_header()
    epubs = sorted(NOVELS.glob("*.epub"))
    if not epubs:
        print("No novels/*.epub found"); return
    total = 0
    for e in epubs:
        total = phases_from_epub(e)
    print(f"DONE phases={total} (chapter N -> phase-NNN, re-runnable)")


if __name__ == "__main__":
    main()
