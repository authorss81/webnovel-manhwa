#!/usr/bin/env python3
"""Render panels.json -> out/phase-NNN/panelNN.jpg via Pollinations flux (main), HF fallback."""
import json, time, os, urllib.request, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STYLE = "full color Korean webtoon style, solo leveling manhwa, clean cel shading, vertical composition, modern characters"
BASE_CHAR = "young Chinese male structural engineer Ren Qi, age 24, short black hair, grey hoodie and jeans, determined eyes"

def pollinations(prompt, w=768, h=1344, seed=777, model="flux", out=None):
    q = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{q}?width={w}&height={h}&seed={seed}&model={model}"
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "manhwa-pipeline/1.0"})
            with urllib.request.urlopen(req, timeout=120) as r, open(out, "wb") as f:
                f.write(r.read())
            if Path(out).stat().st_size > 10000:
                return True
        except Exception as e:
            print(f"  retry {attempt+1}: {e}")
            time.sleep(5 * (attempt + 1))
    return False

def default_panels(source_txt: str):
    # fallback 8-panel template from chapter text (opencode replaces with better beats)
    return [
        {"id": 1, "shot": "wide city countdown", "prompt": f"{BASE_CHAR} on balcony overlooking Shenzhen night city glowing violet countdown in sky, {STYLE}", "dialogue": "The sky was counting down.", "seed": 777},
        {"id": 2, "shot": "closeup face", "prompt": f"closeup {BASE_CHAR} tired face lit by violet light, {STYLE}", "dialogue": "00:03:42... Load-bearing exceeded.", "seed": 778},
        {"id": 3, "shot": "street panic", "prompt": f"crowded Shenzhen street panic below skyscrapers violet sky, {STYLE}", "dialogue": "The screaming started an hour ago.", "seed": 779},
        {"id": 4, "shot": "action resolve", "prompt": f"{BASE_CHAR} standing gripping railing wind blowing, glowing cracks in sky, dynamic, {STYLE}", "dialogue": "I have to go down.", "seed": 780},
    ]

def render_phase(phase: str):
    pd = ROOT / "workspace" / phase
    panels = json.loads((pd / "panels.json").read_text(encoding="utf-8"))
    if not panels:
        src = (pd / "source.txt").read_text(encoding="utf-8")[:2000]
        panels = default_panels(src)
        (pd / "panels.json").write_text(json.dumps(panels, indent=2), encoding="utf-8")
    outd = ROOT / "out" / phase
    outd.mkdir(parents=True, exist_ok=True)
    for p in panels:
        out = outd / f"panel{p['id']:02d}.jpg"
        if out.exists() and out.stat().st_size > 10000:
            print(f"skip {phase} p{p['id']}")
            continue
        print(f"render {phase} p{p['id']}: {p['shot']}")
        ok = pollinations(p["prompt"], seed=p.get("seed", 777), out=str(out))
        print("  OK" if ok else "  FAIL")
        time.sleep(20)  # anonymous 1 req / 15s

if __name__ == "__main__":
    import sys
    render_phase(sys.argv[1] if len(sys.argv) > 1 else "phase-001")
