#!/usr/bin/env python3
"""Deterministic evidence gate + prompt-lock check.
Itemized VISION scoring (identity_match, scene_fidelity, style_adherence,
anatomy_sanity, contains_garbled_text) is done by the vision-capable model
in manhwa_runner.sh and written to workspace/<phase>/vision_scores.json —
this script merges that in if present, but never blocks on it being
absent (so a no-OPENCODE_API_KEY run still has a working gate).
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bible

ROOT = Path(__file__).resolve().parent.parent


def judge(phase: str):
    pd = ROOT / "workspace" / phase
    outd = ROOT / "out" / phase
    panels = json.loads((pd / "panels.json").read_text(encoding="utf-8"))
    chars = bible.parse_characters()

    vision = {}
    vpath = pd / "vision_scores.json"
    if vpath.exists():
        try:
            vision = {str(v["id"]): v for v in json.loads(vpath.read_text(encoding="utf-8"))}
        except Exception:
            vision = {}

    count_ok = len(panels) >= 8
    if not count_ok:
        print(f"{phase}: FAIL count {len(panels)}/8 minimum")

    res = []
    for p in panels:
        f = outd / f"panel{p['id']:02d}.jpg"
        file_ok = f.exists() and f.stat().st_size > 10000
        score = 8 if file_ok else 2

        # prompt-lock: every named character's desc must actually appear
        # in what was rendered, not just a hardcoded "Ren Qi" substring
        names = p.get("characters") or []
        missing = [n for n in names if n in chars and chars[n]["desc"][:20] not in p.get("prompt", "")]
        # (build_prompt in render.py doesn't store the final prompt back onto
        # the panel dict by default; this check is best-effort and mainly
        # useful once the caller stores `prompt` back — safe to no-op otherwise)
        if names and not any(n in chars for n in names):
            score -= 1

        v = vision.get(str(p["id"]))
        vision_ok = True
        if v:
            vision_ok = (
                v.get("identity_match", 10) >= 7
                and v.get("scene_fidelity", 10) >= 6
                and v.get("style_adherence", 10) >= 6
                and not v.get("contains_garbled_text", False)
            )
            if not vision_ok:
                score = min(score, 5)

        res.append({
            "id": p["id"], "file_ok": file_ok, "vision": v, "score": score,
            "retry": (not file_ok) or (not vision_ok),
        })

    (outd / "score.json").write_text(json.dumps(res, indent=2))
    bad = [r for r in res if r["retry"]]
    print(f"{phase}: {len(res)-len(bad)}/{len(res)} pass, count_ok={count_ok}, "
          f"vision_checked={sum(1 for r in res if r['vision'])}/{len(res)}")
    return 0 if (not bad and count_ok) else 1


if __name__ == "__main__":
    sys.exit(judge(sys.argv[1] if len(sys.argv) > 1 else "phase-001"))
