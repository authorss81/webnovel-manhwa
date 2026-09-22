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
        from PIL import Image, ImageDraw, ImageFont
        try:
            font = ImageFont.truetype("arial.ttf", 30)
        except Exception:
            font = ImageFont.load_default()
        def bubble(im, text):
            d = ImageDraw.Draw(im)
            text = text[:140]
            try:
                font = ImageFont.truetype("arial.ttf", max(22, im.width // 26))
            except Exception:
                font = ImageFont.load_default()
            words, lines, cur = text.split(), [], ""
            for w_ in words:
                t = (cur + " " + w_).strip()
                if d.textlength(t, font=font) > im.width - 80:
                    lines.append(cur); cur = w_
            if cur:
                lines.append(cur)
            lines = lines[:4]
            lh = max(30, im.width // 26 + 8)
            h = 30 + lh * len(lines)
            d.rounded_rectangle([20, 20, im.width - 20, 20 + h], radius=18, fill="white", outline="black", width=3)
            y = 32
            for ln in lines:
                d.text((40, y), ln, fill="black", font=font); y += lh
            return im
        dialog = {p["id"]: p.get("dialogue", "") for p in panels}
        ids = [p["id"] for p in panels if (outd / f"panel{p['id']:02d}.jpg").exists()]
        ims = [bubble(Image.open(outd / f"panel{i:02d}.jpg").convert("RGB"), dialog.get(i, "")) for i in ids]
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
