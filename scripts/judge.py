#!/usr/bin/env python3
"""Lightweight judge: file exists + size + prompt-lock check. VLM via opencode separately."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent

def judge(phase: str):
    pd = ROOT / "workspace" / phase
    outd = ROOT / "out" / phase
    panels = json.loads((pd / "panels.json").read_text(encoding="utf-8"))
    res = []
    # evidence gate: 8+ panels required on EVERY path (no-key fallback included)
    count_ok = len(panels) >= 8
    if not count_ok:
        print(f"{phase}: FAIL count {len(panels)}/8 minimum")
    for p in panels:
        f = outd / f"panel{p['id']:02d}.jpg"
        ok = f.exists() and f.stat().st_size > 10000
        score = 8 if ok else 2
        # prompt-lock: must contain locked tokens
        if "Ren Qi" not in p.get("prompt", "") and "BASE" not in p.get("prompt", ""):
            score -= 1
        res.append({"id": p["id"], "ok": ok, "score": score,
                    "retry": score < 7})
    (outd / "score.json").write_text(json.dumps(res, indent=2))
    bad = [r for r in res if r["retry"]]
    print(f"{phase}: {len(res)-len(bad)}/{len(res)} pass, count_ok={count_ok}")
    return 0 if (not bad and count_ok) else 1

if __name__ == "__main__":
    sys.exit(judge(sys.argv[1] if len(sys.argv) > 1 else "phase-001"))
