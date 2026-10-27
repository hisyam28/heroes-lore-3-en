#!/usr/bin/env python3
"""Patch the confirmed HL3 Thumb font metrics; keep module addresses fixed.

Addresses below are ELF virtual addresses, not file offsets. The corresponding
instructions were disassembled from the inventoried 519,952-byte game module.
Both measuring functions and the renderer must use the same Latin advance.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_DELTA = 0x1000 - 0x34
ADVANCE = 6
LINE_HEIGHT = 11

# Exact instruction guards make this patch fail on a different game revision.
# The Latin bitmap stride remains eleven bytes even though only seven rows
# contain ink. Korean composition, record sizes, relocations and pointers stay.
PATCHES = {
    0x3614: ("0721", "0521", "measure: large Latin width 7 -> 5 (+1 gap)"),
    0x36C0: ("0722", "0522", "line scanner: large Latin width 7 -> 5"),
    0x38AE: ("0722", "0522", "renderer: large Latin width 7 -> 5"),
    0x3656: ("0536", "0636", "measure: space uses the same 6px cell"),
    0x3716: ("0537", "0637", "line scanner: 6px space"),
    0x3C5C: ("0530", "0630", "renderer: 6px space width"),
    0x3C5E: ("0537", "0637", "renderer: 6px space cursor"),
    0x366C: ("de1e", "5e1c", "measure: punctuation uses the same 6px cell"),
    0x3738: ("df1e", "5f1c", "line scanner: 6px punctuation"),
    0x3D12: ("df1e", "5f1c", "renderer: 6px punctuation cursor"),
    0x3D16: ("033b", "0133", "renderer: 6px punctuation width"),
    0x3934: ("0d31", "0b31", "Korean prefix wrap: line height 13 -> 11"),
    0x39A6: ("0d30", "0b30", "Latin prefix wrap: line height 13 -> 11"),
    0x3A22: ("0d32", "0b32", "Korean draw wrap: line height 13 -> 11"),
    0x3C20: ("0d31", "0b31", "Latin draw wrap: line height 13 -> 11"),
    0x3CE8: ("072c", "042c", "Latin glyph loop: 8 -> 5 columns"),
    0x3CFA: ("0a28", "0628", "Latin glyph loop: 11 -> 7 rows"),
}

# Five by seven capital glyphs, stored in the engine's existing 11-byte slots.
# Lowercase input maps to capitals because the original lowercase slots hold
# unrelated glyph artwork. Punctuation comes from the game's compact font.
GLYPHS = {
    "A": [14,17,17,31,17,17,17], "B": [30,17,17,30,17,17,30],
    "C": [14,17,16,16,16,17,14], "D": [30,17,17,17,17,17,30],
    "E": [31,16,16,30,16,16,31], "F": [31,16,16,30,16,16,16],
    "G": [14,17,16,23,17,17,15], "H": [17,17,17,31,17,17,17],
    "I": [14,4,4,4,4,4,14], "J": [7,2,2,2,18,18,12],
    "K": [17,18,20,24,20,18,17], "L": [16,16,16,16,16,16,31],
    "M": [17,27,21,21,17,17,17], "N": [17,25,21,19,17,17,17],
    "O": [14,17,17,17,17,17,14], "P": [30,17,17,30,16,16,16],
    "Q": [14,17,17,17,21,18,13], "R": [30,17,17,30,20,18,17],
    "S": [15,16,16,14,1,1,30], "T": [31,4,4,4,4,4,4],
    "U": [17,17,17,17,17,17,14], "V": [17,17,17,17,17,10,4],
    "W": [17,17,17,21,21,21,10], "X": [17,17,10,4,10,17,17],
    "Y": [17,17,10,4,4,4,4], "Z": [31,1,2,4,8,16,31],
    "0": [14,17,19,21,25,17,14], "1": [4,12,4,4,4,4,14],
    "2": [14,17,1,2,4,8,31], "3": [30,1,1,14,1,1,30],
    "4": [2,6,10,18,31,2,2], "5": [31,16,16,30,1,1,30],
    "6": [14,16,16,30,17,17,14], "7": [31,1,2,4,8,8,8],
    "8": [14,17,17,14,17,17,14], "9": [14,17,17,15,1,1,14],
    ".": [0,0,0,0,0,0,16], ",": [0,0,0,0,0,16,16],
    "'": [4,4,0,0,0,0,0], '"': [10,10,0,0,0,0,0],
    ":": [0,4,4,0,4,4,0], ";": [0,4,4,0,4,4,8],
    "!": [4,4,4,4,4,0,4], "?": [14,17,1,2,4,0,4],
    "-": [0,0,0,31,0,0,0], "/": [1,2,2,4,8,8,16],
    "(": [2,4,8,8,8,4,2], ")": [8,4,2,2,2,4,8],
    "[": [14,8,8,8,8,8,14], "]": [14,2,2,2,2,2,14],
    "+": [0,4,4,31,4,4,0], "=": [0,31,0,31,0,0,0],
    "%": [25,25,2,4,8,19,19], "&": [12,18,20,8,21,18,13],
    "<": [1,2,4,8,4,2,1], ">": [16,8,4,2,4,8,16],
    "_": [0,0,0,0,0,0,31], "*": [0,21,14,31,14,21,0],
    "#": [10,31,10,10,31,10,0], "@": [14,17,23,21,23,16,14],
    "$": [4,15,20,14,5,30,4], "|": [4,4,4,4,4,4,4],
    "{": [3,4,4,8,4,4,3], "}": [24,4,4,2,4,4,24],
    "\\": [16,8,8,4,2,2,1], "^": [4,10,17,0,0,0,0],
    "`": [8,4,0,0,0,0,0], "~": [0,0,9,22,0,0,0],
    " ": [0,0,0,0,0,0,0],
}


def build_font() -> bytes:
    slots = []
    for code in range(32,127):
        glyph = GLYPHS[chr(code).upper()]
        slots.append(bytes(row << 3 for row in glyph) + bytes(4))
    font = b"".join(slots)
    assert len(font) == 95 * 11
    assert all(not value & 7 for value in font)
    return font


def patch_metrics(data: bytes) -> bytes:
    result = bytearray(data)
    for va, (old_hex, new_hex, label) in PATCHES.items():
        pos = va - TEXT_DELTA
        old, new = bytes.fromhex(old_hex), bytes.fromhex(new_hex)
        if result[pos:pos+len(old)] != old:
            raise ValueError(f"Font instruction mismatch at 0x{va:X}: {label}")
        result[pos:pos+len(old)] = new
    return bytes(result)


def apply(overlay: Path) -> None:
    module = overlay / "binary.mod"
    module.write_bytes(patch_metrics(module.read_bytes()))
    target = overlay / "res/font"
    target.mkdir(parents=True,exist_ok=True)
    for name in ("eng5","eng7"):
        (target/name).write_bytes(build_font())


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("overlay",type=Path)
    apply(parser.parse_args().overlay)
