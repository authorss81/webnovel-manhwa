#!/usr/bin/env python3
"""01 - EPUB(s) -> workspace/phase-NNN (one chapter each). Idempotent via hash."""
import zipfile, re, json, hashlib, html
from pathlib import Path

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

def prompt_md(d, title):
    return f"""# {title} ({d.name}) — manhwa adaptation task for opencode

Read FIRST: `manhwa/bible/characters.md` (locked tokens), `AGENTS.md` (hard rules),
`workspace/{d.name}/source.txt` (chapter text), `workspace/{d.name}/meta.json`.

DO:
1. Write 8-12 panels to `workspace/{d.name}/panels.json` as list of
   {{"id": N, "shot": "...", "prompt": "...", "dialogue": "...", "seed": 777+N}}.
2. Every prompt MUST contain verbatim: `young Chinese male structural engineer Ren Qi, age 24, short black hair, grey hoodie and jeans`
   plus `full color Korean webtoon style, solo leveling manhwa, clean cel shading, vertical composition, modern characters`.
3. Only vary shot/action/lighting. Never change hair/clothes/age words.
4. Dialogue from source.txt, short webtoon bubbles, no narration dumps.
5. Then run: `python3 scripts/render.py {d.name}` and `python3 scripts/judge.py {d.name}`.
   If judge reports retry, edit ONLY shot/lighting words in that panel's prompt (keep locked tokens), bump seed+1, re-render max 3 tries.

DONE = `panels.json` has 8+ panels AND `out/{d.name}/panelNN.jpg` all exist >10KB.
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
        (d / ".timeout").write_text("90", encoding="utf-8")
        (d / "PROMPT.md").write_text(prompt_md(d, title), encoding="utf-8")
        n += 1
    return n

def main():
    epubs = sorted(NOVELS.glob("*.epub"))
    if not epubs:
        print("No novels/*.epub found"); return
    total = 0
    for e in epubs:
        total = phases_from_epub(e)
    print(f"DONE phases={total} (chapter N -> phase-NNN, re-runnable)")

if __name__ == "__main__":
    main()
