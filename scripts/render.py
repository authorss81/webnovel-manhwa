#!/usr/bin/env python3
"""Render panels.json -> out/phase-NNN/panelNN.jpg via Pollinations flux (main), HF fallback."""
import json, time, os, urllib.request, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STYLE = "inked anime line art, bold black outlines, full color Korean webtoon style, solo leveling manhwa, clean cel shading with screentone, vertical panel composition, empty space at top for speech bubble, modern characters"
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
    # extractive fallback: real beats from THIS chapter (opencode replaces with better beats)
    import re
    body = source_txt.split("\n\n", 1)[-1]  # drop title header line
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", body) if 30 < len(s.strip()) < 220]
    if not sents:
        sents = [source_txt[:120]]
    n = min(6, max(4, len(sents) // 8))
    idxs = [int(i * (len(sents) - 1) / max(1, n - 1)) for i in range(n)]
    shots = ["wide establishing", "closeup face", "action beat", "tension beat", "reaction", "cliffhanger"]
    out = []
    for k, si in enumerate(idxs):
        line = sents[si][:90]
        out.append({"id": k + 1, "shot": f"{shots[k % len(shots)]}: {line[:50]}",
                    "prompt": f"{BASE_CHAR}, {shots[k % len(shots)]}, scene: {line}, {STYLE}",
                    "dialogue": line, "seed": 777 + k})
    return out

def render_phase(phase: str):
    pd = ROOT / "workspace" / phase
    pf = pd / "panels.json"
    panels = json.loads(pf.read_text(encoding="utf-8")) if pf.exists() else []
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
