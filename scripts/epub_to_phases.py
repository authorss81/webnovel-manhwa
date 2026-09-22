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

def phases_from_epub(epub: Path, start_idx: int) -> int:
    z = zipfile.ZipFile(epub)
    chs = sorted([n for n in z.namelist() if re.search(r"chapter_\d+\.xhtml", n)],
                 key=lambda x: int(re.search(r"chapter_(\d+)", x).group(1)))
    idx = start_idx
    for ch in chs:
        raw = z.read(ch)
        h = hashlib.sha256(raw).hexdigest()[:16]
        title, text = clean_text(raw)
        if not text:
            continue
        idx += 1
        d = WS / f"phase-{idx:03d}"
        d.mkdir(exist_ok=True)
        # idempotency: skip rewrite if same source hash
        hf = d / ".source_hash"
        if hf.exists() and hf.read_text().strip() == h:
            continue
        (d / "source.txt").write_text(f"{title}\n\n{text}", encoding="utf-8")
        (d / "meta.json").write_text(json.dumps({
            "book": epub.name, "chapter_file": ch, "title": title,
            "phase": f"phase-{idx:03d}", "chars": len(text)}, indent=2), encoding="utf-8")
        if not (d / "panels.json").exists():
            (d / "panels.json").write_text("[]", encoding="utf-8")
        (d / ".timeout").write_text("90", encoding="utf-8")
        hf.write_text(h, encoding="utf-8")
        print(f"wrote {d.name}: {title} ({len(text)} chars)")
    return idx

def main():
    epubs = sorted(NOVELS.glob("*.epub"))
    if not epubs:
        print("No novels/*.epub found"); return
    # resume from existing max to stay idempotent across books
    existing = sorted([int(p.name.split('-')[1]) for p in WS.glob("phase-*") if p.is_dir()])
    idx = max(existing) if existing else 0
    for e in epubs:
        idx = phases_from_epub(e, idx)
    print(f"DONE phases=1..{idx}")

if __name__ == "__main__":
    main()
