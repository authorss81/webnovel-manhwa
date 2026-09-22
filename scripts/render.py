#!/usr/bin/env python3
"""Render panels.json -> out/phase-NNN/panelNN.jpg

Character-consistency strategy (this is the important part):
1. Every character in the bible has ONE locked reference image (a plain
   turnaround portrait, generated once, never regenerated).
2. Every panel is rendered by EDITING that reference image with FLUX.1
   Kontext ("same person, now in this scene/action"), not by generating
   from a text prompt + seed alone. Seed+prompt alone does not hold facial
   identity across different scenes — this is why the old pipeline drifted.
3. If a panel has multiple named characters, the primary (first-listed)
   character is reference-conditioned via Kontext; co-characters are
   described in text only. This is a real, documented limitation of
   free/open Kontext access (most endpoints take one reference image) —
   multi-character panels will be less consistent than solo panels.
4. `fix` mode edits an EXISTING rendered panel with a corrective
   instruction instead of regenerating from scratch — used by
   manhwa_runner.sh after the vision-eval step finds a specific problem.

Usage:
    python3 scripts/render.py <phase>
    python3 scripts/render.py fix <phase> <panel_id> "<correction instruction>"
"""
import json, time, os, re, sys, base64, urllib.request, urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bible

ROOT = Path(__file__).resolve().parent.parent
STYLE = bible.get_style()
STYLE_NEG = bible.get_style_neg()

BLOCKED_WORDS = (
    "gore", "decapitat", "mutilat", "torture", "porn", "nsfw", "nude", "naked",
    "sex", "erotic", "fetish", "loli", "shota", "underage", "minor girl",
    "rape", "self.?harm", "suicide", "gun violence", "mass shoot",
)
_BLOCK_RE = re.compile(r"\b(" + "|".join(BLOCKED_WORDS) + r")\b", re.IGNORECASE)


def moderated(prompt: str) -> bool:
    return bool(_BLOCK_RE.search(prompt))


# ---------- text-to-image (used only for: character reference sheets, and
# as a last-resort fallback when no reference/Kontext path is available) ----

def pollinations(prompt, w=768, h=1344, seed=777, model="flux", out=None):
    if moderated(prompt):
        print("  BLOCKED by moderation filter"); return False
    q = urllib.parse.quote(prompt)
    for attempt in range(4):
        s = seed + attempt  # seed-lock: retry = seed+1, never random
        url = f"https://image.pollinations.ai/prompt/{q}?width={w}&height={h}&seed={s}&model={model}&nologo=true"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "manhwa-pipeline/1.0"})
            with urllib.request.urlopen(req, timeout=120) as r, open(out, "wb") as f:
                f.write(r.read())
            if Path(out).stat().st_size > 10000:
                return True
        except Exception as e:
            print(f"  pollinations retry {attempt+1}: {e}")
            time.sleep(5 * (attempt + 1))
    return False


def hf_text2img(prompt, w=768, h=1344, seed=777, out=None):
    """HF flux-schnell, text-only. Free-tier fallback / used for reference sheets."""
    tok = os.environ.get("HF_TOKEN", "")
    if not tok or moderated(prompt):
        return False
    body = json.dumps({"inputs": prompt, "parameters": {"width": w, "height": h, "seed": seed}}).encode()
    for attempt in range(2):
        try:
            req = urllib.request.Request(
                "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell",
                data=body, headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=180) as r, open(out, "wb") as f:
                f.write(r.read())
            if Path(out).stat().st_size > 10000:
                return True
        except Exception as e:
            print(f"  hf-t2i retry {attempt+1}: {e}")
            time.sleep(10 * (attempt + 1))
    return False


# ---------- reference-conditioned editing: the character-consistency fix ----

def hf_kontext(prompt, ref_path: Path, w=768, h=1344, seed=777, out=None):
    """FLUX.1 Kontext-dev via HF Inference: edits ref_path per `prompt`,
    preserving the depicted person's identity. This is what actually gives
    character consistency — seed-locked text2img alone cannot."""
    tok = os.environ.get("HF_TOKEN", "")
    if not tok or not ref_path.exists() or moderated(prompt):
        return False
    ref_b64 = base64.b64encode(ref_path.read_bytes()).decode()
    body = json.dumps({
        "inputs": prompt,
        "parameters": {"image": ref_b64, "width": w, "height": h, "seed": seed},
    }).encode()
    for attempt in range(2):
        try:
            req = urllib.request.Request(
                "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-Kontext-dev",
                data=body, headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=180) as r, open(out, "wb") as f:
                f.write(r.read())
            if Path(out).stat().st_size > 10000:
                return True
        except Exception as e:
            print(f"  kontext retry {attempt+1}: {e}")
            time.sleep(10 * (attempt + 1))
    return False


def pollinations_kontext(prompt, ref_url: str, w=768, h=1344, seed=777, out=None):
    """Unofficial free fallback: image.pollinations.ai's community-documented
    model=kontext&image=<url> editing path. NOT officially guaranteed —
    only used if HF_TOKEN is unavailable. ref_url must be a publicly
    fetchable URL (e.g. a raw.githubusercontent.com link to a file already
    pushed to this repo), not a local path."""
    if moderated(prompt) or not ref_url:
        return False
    q = urllib.parse.quote(prompt)
    url = (f"https://image.pollinations.ai/prompt/{q}"
           f"?model=kontext&image={urllib.parse.quote(ref_url, safe='')}"
           f"&width={w}&height={h}&seed={seed}&nologo=true")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "manhwa-pipeline/1.0"})
        with urllib.request.urlopen(req, timeout=120) as r, open(out, "wb") as f:
            f.write(r.read())
        return Path(out).stat().st_size > 10000
    except Exception as e:
        print(f"  pollinations-kontext failed: {e}")
        return False


def generate_reference(name: str, desc: str, out_path: Path, seed=777) -> bool:
    """One-time clean turnaround portrait for a new character. Plain
    text2img (no scene/action) — this image becomes the locked anchor
    every future panel of this character is edited from."""
    if out_path.exists() and out_path.stat().st_size > 10000:
        return True
    out_path.parent.mkdir(parents=True, exist_ok=True)
    prompt = (f"character reference sheet, front facing portrait, neutral pose, plain background, "
              f"{desc}, {STYLE}, ({STYLE_NEG})")
    print(f"  generating reference for {name} ...")
    ok = pollinations(prompt, seed=seed, out=str(out_path))
    if not ok:
        ok = hf_text2img(prompt, seed=seed, out=str(out_path))
    print("  ref OK" if ok else "  ref FAILED (character will render without conditioning)")
    return ok


# ---------- panel prompt assembly ----

def build_prompt(panel: dict, chars: dict) -> tuple[str, str | None]:
    """Returns (prompt_text, primary_character_name_or_None).
    The primary character (first in panel['characters']) is the one whose
    reference image conditions the render via Kontext. Others are
    described in text only — see module docstring for why."""
    names = panel.get("characters") or []
    primary = names[0] if names else None
    desc_bits = []
    for n in names:
        c = chars.get(n)
        if c:
            desc_bits.append(c["desc"])
    scene = panel.get("scene", "")
    action = panel.get("action", panel.get("shot", ""))
    camera = panel.get("camera", "")
    prompt = ", ".join(x for x in [
        *desc_bits, scene, action, camera, STYLE,
    ] if x) + f", ({STYLE_NEG})"
    return prompt, primary


# ---------- main render loop ----

def render_phase(phase: str):
    pd = ROOT / "workspace" / phase
    pf = pd / "panels.json"
    panels = json.loads(pf.read_text(encoding="utf-8")) if pf.exists() else []
    if not panels:
        print(f"{phase}: no panels.json content — nothing to render (opencode should have written this)")
        return

    chars = bible.parse_characters()
    # make sure every character referenced by this phase has a reference image
    for name in {n for p in panels for n in (p.get("characters") or [])}:
        c = chars.get(name)
        if c and not (c["ref"] and c["ref"].exists()):
            generate_reference(name, c["desc"], c["ref"])

    outd = ROOT / "out" / phase
    outd.mkdir(parents=True, exist_ok=True)
    for p in panels:
        out = outd / f"panel{p['id']:02d}.jpg"
        if out.exists() and out.stat().st_size > 10000:
            print(f"skip {phase} p{p['id']}")
            continue
        prompt, primary = build_prompt(p, chars)
        seed = p.get("seed", 777)
        print(f"render {phase} p{p['id']}: {p.get('shot', p.get('action',''))} (primary={primary})")

        ok = False
        ref = chars.get(primary, {}).get("ref") if primary else None
        if ref and ref.exists():
            ok = hf_kontext(prompt, ref, seed=seed, out=str(out))
        if not ok:
            ok = pollinations(prompt, seed=seed, out=str(out))
        if not ok:
            ok = hf_text2img(prompt, seed=seed, out=str(out))
        print("  OK" if ok else "  FAIL")
        time.sleep(20)  # pollinations anonymous free tier: ~1 req/15s


def fix_panel(phase: str, panel_id: str, note: str):
    """Targeted corrective edit on an EXISTING panel image, guided by a
    specific note (e.g. 'face doesn't match reference, fix hairstyle and
    face shape to match, keep pose and background'). Called by
    manhwa_runner.sh after the itemized vision-eval step."""
    pd = ROOT / "workspace" / phase
    panels = json.loads((pd / "panels.json").read_text(encoding="utf-8"))
    p = next((x for x in panels if str(x["id"]) == str(panel_id)), None)
    if not p:
        print(f"panel {panel_id} not found in {phase}"); return False
    outd = ROOT / "out" / phase
    out = outd / f"panel{int(panel_id):02d}.jpg"
    if not out.exists():
        print("nothing to fix, panel image missing"); return False
    chars = bible.parse_characters()
    prompt, primary = build_prompt(p, chars)
    fix_prompt = f"{note}. {prompt}"
    seed = p.get("seed", 777) + 1
    print(f"fix {phase} p{panel_id}: {note}")
    ok = hf_kontext(fix_prompt, out, seed=seed, out=str(out))  # edit the panel itself, in place
    print("  FIX OK" if ok else "  FIX FAILED (kept previous version)")
    return ok


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "fix":
        fix_panel(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "fix identity to match reference")
    else:
        render_phase(sys.argv[1] if len(sys.argv) > 1 else "phase-001")
