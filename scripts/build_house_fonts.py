#!/usr/bin/env python3
"""Build the open, metric-compatible house display font (Gelasio = Georgia) as
four correctly-named static styles from the upstream variable fonts.

The house style pairs Georgia (display) with Arial (body). Those are proprietary
and absent on CI runners, so the reproducible build uses the metric-compatible
open clones Gelasio (Georgia) and Arimo (Arial). Arimo ships as apt
`fonts-croscore`; Gelasio ships only as *variable* fonts upstream, and slicing a
weight instance with fontTools leaves every style advertising the same
name/weight bits, so fontspec/CoreText cannot tell Regular from Bold.

This script instantiates wght=400/700 from the upright and italic variable
fonts and rewrites the name table + OS/2 / head style bits so the four files
present as a proper Regular / Bold / Italic / Bold Italic family named "Gelasio".

Run (writes into ./fonts by default, or the dir given as argv[1]):

    python scripts/build_house_fonts.py [dest_dir]

house-preamble.tex references these by path as `Path=./fonts/`, so the default
matches what the PDF build expects. The `fonts/` dir is gitignored and rebuilt.
"""
from __future__ import annotations

import pathlib
import sys
import urllib.request

from fontTools import ttLib
from fontTools.varLib.instancer import instantiateVariableFont

FAMILY = "Gelasio"
UPSTREAM = {
    "upright": "https://raw.githubusercontent.com/google/fonts/main/ofl/gelasio/Gelasio%5Bwght%5D.ttf",
    "italic": "https://raw.githubusercontent.com/google/fonts/main/ofl/gelasio/Gelasio-Italic%5Bwght%5D.ttf",
}
# (style label, source key, weight, is_bold, is_italic)
STYLES = [
    ("Regular", "upright", 400, False, False),
    ("Bold", "upright", 700, True, False),
    ("Italic", "italic", 400, False, True),
    ("Bold Italic", "italic", 700, True, True),
]

MAC, WIN = (1, 0, 0), (3, 1, 0x409)  # (platformID, encodingID, langID)


def _download(url: str, dest: pathlib.Path) -> pathlib.Path:
    if not dest.exists():
        req = urllib.request.Request(url, headers={"User-Agent": "curl/8"})
        with urllib.request.urlopen(req, timeout=60) as r:
            dest.write_bytes(r.read())
    return dest


def _set_name(font: ttLib.TTFont, name_id: int, value: str) -> None:
    for plat in (MAC, WIN):
        font["name"].setName(value, name_id, *plat)


def build(dest_dir: pathlib.Path) -> list[pathlib.Path]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    cache = dest_dir / "_src"
    cache.mkdir(exist_ok=True)
    srcs = {k: _download(u, cache / f"gelasio-{k}.ttf") for k, u in UPSTREAM.items()}

    written = []
    for label, key, wght, is_bold, is_italic in STYLES:
        font = ttLib.TTFont(srcs[key])
        instantiateVariableFont(font, {"wght": wght}, inplace=True)

        ps = f"{FAMILY}-{label.replace(' ', '')}"
        subfamily = label
        full = f"{FAMILY} {label}".strip()
        # Name table: keep RIBBI grouping so Regular/Bold/Italic/BoldItalic are
        # one family with four styles that fontspec resolves automatically.
        _set_name(font, 1, FAMILY)          # family
        _set_name(font, 2, subfamily)       # subfamily (Regular/Bold/Italic/Bold Italic)
        _set_name(font, 4, full)            # full name
        _set_name(font, 6, ps)              # PostScript name
        _set_name(font, 16, FAMILY)         # typographic family
        _set_name(font, 17, subfamily)      # typographic subfamily

        # Style bits: OS/2 fsSelection + head macStyle must agree with the label.
        os2, head = font["OS/2"], font["head"]
        fs = os2.fsSelection & ~0b1100001  # clear ITALIC(0), BOLD(5), REGULAR(6)
        mac = head.macStyle & ~0b11         # clear bold(0), italic(1)
        if is_bold:
            fs |= 1 << 5
            mac |= 1 << 0
            os2.usWeightClass = 700
        if is_italic:
            fs |= 1 << 0
            mac |= 1 << 1
        if not is_bold and not is_italic:
            fs |= 1 << 6
        os2.fsSelection, head.macStyle = fs, mac

        out = dest_dir / f"{ps}.ttf"
        font.save(out)
        written.append(out)
        print(f"wrote {out.name}  (family={FAMILY}, style={subfamily})")
    return written


def main() -> None:
    root = pathlib.Path(__file__).resolve().parent.parent
    dest = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else root / "fonts"
    build(dest)
    print(f"done -> {dest}")


if __name__ == "__main__":
    main()
