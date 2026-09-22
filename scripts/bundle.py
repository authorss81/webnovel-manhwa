#!/usr/bin/env python3
"""Bundle phase panels into Solo-Leveling-style vertical strip chapter."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent

def bundle(phase: str):
    outd = ROOT / "out" / phase
    panels = json.loads((ROOT / "workspace" / phase / "panels.json").read_text(encoding="utf-8"))
    imgs = [outd / f"panel{p['id']:02d}.jpg" for p in panels]
    imgs = [f for f in imgs if f.exists() and f.stat().st_size > 10000]
    if not imgs:
        print(f"{phase}: nothing to bundle"); return False
    try:
        from PIL import Image
        ims = [Image.open(f).convert("RGB") for f in imgs]
        w = min(i.width for i in ims)
        ims = [i.resize((w, int(i.height * w / i.width))) for i in ims]
        strip = Image.new("RGB", (w, sum(i.height for i in ims)), "black")
        y = 0
        for i in ims:
            strip.paste(i, (0, y)); y += i.height
        strip.save(outd / "strip.jpg", quality=88)
        print(f"{phase}: strip.jpg {strip.size}")
    except ImportError:
        print(f"{phase}: Pillow missing, skip strip (pip install pillow)")
    # chapter html with dialogue bubbles (manhwa scroll)
    html = ["<!DOCTYPE html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>",
            f"<title>{phase}</title><style>body{{background:#111;color:#fff;margin:0;display:flex;flex-direction:column;align-items:center}}img{{width:760px;max-width:100vw}}.b{{background:#fff;color:#000;padding:8px 14px;border-radius:12px;margin:10px;max-width:600px}}</style></head><body>"]
    for p in panels:
        html.append(f"<div class=b>{p.get('dialogue','')}</div><img src='panel{p['id']:02d}.jpg'>")
    html.append("</body></html>")
    (outd / "chapter.html").write_text("\n".join(html), encoding="utf-8")
    return True

if __name__ == "__main__":
    import sys
    bundle(sys.argv[1] if len(sys.argv) > 1 else "phase-001")
