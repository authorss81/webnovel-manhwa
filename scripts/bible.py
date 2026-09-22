#!/usr/bin/env python3
"""Shared helper: multi-character bible parser/writer.

manhwa/bible/characters.md format:

    # Character bible — LOCKED...
    STYLE: ...
    STYLE_NEG: ...
    SEED_BASE: 777
    RULE: ...

    [REN_QI]
    desc: young Chinese male structural engineer, age 24, short black hair, grey hoodie and jeans, determined tired eyes
    ref: manhwa/bible/ref_ren_qi.jpg

    [LIN_MEI]
    desc: young Chinese female paramedic, age 23, shoulder-length brown hair, red jacket, sharp eyes
    ref: manhwa/bible/ref_lin_mei.jpg

New characters are only ever appended, never edited, once locked — that's what
keeps them consistent across chapters/phases.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIBLE_PATH = ROOT / "manhwa" / "bible" / "characters.md"

STYLE_DEFAULT = (
    "inked anime line art, bold black outlines, full color Korean modern webtoon style, "
    "dynamic action-manhwa aesthetic, clean cel shading with screentone, "
    "vertical panel composition, empty space at top for speech bubble, modern characters"
)
STYLE_NEG_DEFAULT = "no medieval armor, no fantasy castle drift, no photoreal, no chibi, no sketch"


def _read() -> str:
    return BIBLE_PATH.read_text(encoding="utf-8") if BIBLE_PATH.exists() else ""


def get_style() -> str:
    m = re.search(r"^STYLE:\s*(.+)$", _read(), re.M)
    return m.group(1).strip() if m else STYLE_DEFAULT


def get_style_neg() -> str:
    m = re.search(r"^STYLE_NEG:\s*(.+)$", _read(), re.M)
    return m.group(1).strip() if m else STYLE_NEG_DEFAULT


def parse_characters() -> dict:
    """Return {NAME: {"desc": str, "ref": Path}}. Missing ref file is fine —
    callers generate it lazily the first time that character is rendered."""
    txt = _read()
    out = {}
    for block in re.split(r"\n(?=\[)", txt):
        m = re.match(r"\[([A-Z0-9_]+)\]\s*\n\s*desc:\s*(.+?)\s*\n\s*ref:\s*(.+)", block.strip(), re.S)
        if not m:
            continue
        name, desc, ref = m.group(1), m.group(2).strip(), m.group(3).strip().splitlines()[0].strip()
        out[name] = {"desc": desc, "ref": (ROOT / ref) if ref else None}
    return out


def ensure_header():
    BIBLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not BIBLE_PATH.exists():
        header = (
            "# Character bible — LOCKED. Every prompt must reuse desc tokens verbatim.\n"
            f"STYLE: {STYLE_DEFAULT}\n"
            f"STYLE_NEG: {STYLE_NEG_DEFAULT}\n"
            "SEED_BASE: 777 (panel N uses 777+N, never random)\n"
            "RULE: never edit an existing character block's desc words once locked. "
            "New characters are appended below the first time they appear.\n"
        )
        BIBLE_PATH.write_text(header, encoding="utf-8")


def add_character(name: str, desc: str) -> tuple[str, Path, bool]:
    """Append a new locked character if not already present.
    Returns (NAME, ref_path, created_bool)."""
    ensure_header()
    name = re.sub(r"[^A-Z0-9_]", "_", name.upper().strip())
    chars = parse_characters()
    if name in chars:
        return name, chars[name]["ref"], False
    ref_rel = f"manhwa/bible/ref_{name.lower()}.jpg"
    with BIBLE_PATH.open("a", encoding="utf-8") as f:
        f.write(f"\n[{name}]\ndesc: {desc}\nref: {ref_rel}\n")
    return name, ROOT / ref_rel, True


if __name__ == "__main__":
    import sys, json
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        print(json.dumps({k: {"desc": v["desc"], "ref": str(v["ref"])} for k, v in parse_characters().items()}, indent=2))
    elif len(sys.argv) > 3 and sys.argv[1] == "add":
        name, ref, created = add_character(sys.argv[2], sys.argv[3])
        print(json.dumps({"name": name, "ref": str(ref), "created": created}))
