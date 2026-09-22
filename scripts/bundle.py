#!/usr/bin/env python3
"""Bundle phase panels into a vertical-scroll webtoon chapter (Solo Leveling's
own manhwa is vertical-scroll too — that structure is correct; what was
missing was pacing and real bubble placement, both handled below)."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent

# Ubuntu ubuntu-latest GH Actions runners ship fonts-dejavu-core by default.
# "arial.ttf" does NOT exist there — that was a silent bug: PIL would throw,
# get caught, and silently fall back to the tiny default bitmap font on every
# CI run, even though it might have looked fine testing locally on a machine
# that does have Arial.
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    str(ROOT / "manhwa" / "bible" / "NotoSans-Bold.ttf"),  # optional: commit one here for a guaranteed match
]

PANEL_SCALE = {"small": 0.75, "medium": 1.0, "splash": 1.2}
REGION_ANCHOR = {
    "top-left": (0.05, 0.05), "top-right": (0.55, 0.05),
    "center-left": (0.05, 0.4), "center-right": (0.55, 0.4),
    "bottom-left": (0.05, 0.72), "bottom-right": (0.55, 0.72),
}


def _font(size):
    from PIL import ImageFont
    for path in FONT_CANDIDATES:
        try:
            if Path(path).exists():
                return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _wrap(draw, text, font, max_width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) > max_width:
            if cur:
                lines.append(cur)
            cur = w
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines[:4]


def _draw_bubble(im, text, anchor_frac, tail_toward=None):
    from PIL import ImageDraw
    d = ImageDraw.Draw(im)
    font = _font(max(20, im.width // 26))
    text = text[:140]
    ax, ay = anchor_frac
    x0 = int(im.width * ax)
    max_w = min(int(im.width * 0.42), im.width - x0 - 20)
    lines = _wrap(d, text, font, max_w)
    lh = max(26, im.width // 26 + 6)
    h = 24 + lh * max(1, len(lines))
    w = max(d.textlength(ln, font=font) for ln in lines) + 40 if lines else 100
    y0 = int(im.height * ay)
    box = [x0, y0, min(x0 + w, im.width - 10), y0 + h]
    d.rounded_rectangle(box, radius=16, fill="white", outline="black", width=3)
    if tail_toward:
        tx, ty = tail_toward
        cx = (box[0] + box[2]) // 2
        cy = box[3]
        d.polygon([(cx - 14, cy - 2), (cx + 14, cy - 2), (tx, ty)], fill="white", outline="black")
    yy = box[1] + 12
    for ln in lines:
        d.text((box[0] + 20, yy), ln, fill="black", font=font)
        yy += lh
    return im


def _draw_narration(im, text):
    from PIL import ImageDraw
    d = ImageDraw.Draw(im)
    font = _font(max(18, im.width // 30))
    text = text[:160]
    lines = _wrap(d, text, font, im.width - 80)
    lh = max(22, im.width // 30 + 4)
    h = 20 + lh * max(1, len(lines))
    d.rectangle([20, im.height - h - 20, im.width - 20, im.height - 20], fill=(0, 0, 0, 180), outline="white")
    yy = im.height - h
    for ln in lines:
        d.text((36, yy), ln, fill="white", font=font)
        yy += lh
    return im


def annotate_panel(img_path: Path, panel: dict) -> "Image":
    from PIL import Image
    im = Image.open(img_path).convert("RGB")
    dialogue = panel.get("dialogue")
    if isinstance(dialogue, str):  # backward-compat with the old flat-string schema
        dialogue = [{"speaker": None, "line": dialogue}] if dialogue else []
    regions = panel.get("regions", {})  # e.g. {"REN_QI": "top-left"} from the vision-eval step
    for line_obj in (dialogue or []):
        speaker = line_obj.get("speaker")
        text = line_obj.get("line", "")
        if not text:
            continue
        if speaker:
            anchor = REGION_ANCHOR.get(regions.get(speaker, "top-left"), REGION_ANCHOR["top-left"])
            tail = (int(im.width * (anchor[0] + 0.1)), int(im.height * (anchor[1] + 0.25)))
            _draw_bubble(im, text, anchor, tail_toward=tail)
        else:
            _draw_narration(im, text)
    return im


def bundle(phase: str):
    outd = ROOT / "out" / phase
    panels = json.loads((ROOT / "workspace" / phase / "panels.json").read_text(encoding="utf-8"))
    valid = [p for p in panels if (outd / f"panel{p['id']:02d}.jpg").exists()
             and (outd / f"panel{p['id']:02d}.jpg").stat().st_size > 10000]
    if not valid:
        print(f"{phase}: nothing to bundle")
        return False

    try:
        from PIL import Image
        base_w = 720
        frames = []
        for p in valid:
            src = outd / f"panel{p['id']:02d}.jpg"
            im = annotate_panel(src, p)
            scale = PANEL_SCALE.get(p.get("panel_size", "medium"), 1.0)
            target_h = int(im.height * (base_w / im.width) * scale)
            im = im.resize((base_w, target_h))
            frames.append(im)
        gutter = 14
        total_h = sum(f.height for f in frames) + gutter * (len(frames) - 1)
        strip = Image.new("RGB", (base_w, total_h), "black")
        y = 0
        for f in frames:
            strip.paste(f, (0, y))
            y += f.height + gutter
        strip.save(outd / "strip.jpg", quality=90)
        print(f"{phase}: strip.jpg {strip.size}")

        # save individual annotated panels too, so panelNN.jpg used elsewhere
        # (e.g. releases) already has bubbles baked in
        for p, f in zip(valid, frames):
            f.save(outd / f"panel{p['id']:02d}.jpg", quality=90)

    except ImportError:
        print(f"{phase}: Pillow missing, skip strip (pip install pillow)")
        return False

    html = [
        "<!DOCTYPE html><html><head><meta charset=utf-8>",
        "<meta name=viewport content='width=device-width,initial-scale=1'>",
        f"<title>{phase}</title>",
        "<style>body{background:#111;margin:0;display:flex;flex-direction:column;"
        "align-items:center}img{width:720px;max-width:100vw;display:block}</style>",
        "</head><body>",
    ]
    for p in valid:
        html.append(f"<img src='panel{p['id']:02d}.jpg'>")
    html.append("</body></html>")
    (outd / "chapter.html").write_text("\n".join(html), encoding="utf-8")
    return True


if __name__ == "__main__":
    import sys
    bundle(sys.argv[1] if len(sys.argv) > 1 else "phase-001")
