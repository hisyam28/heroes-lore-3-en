"""Guarded layout correction for the game's three character-save rows."""
from hl3_font_runtime import TEXT_DELTA

PATCHES={
    0x5426:('0232','0132','center 12px number frame inside 14px row'),
    0x5494:('0639','0a39','align number frame with compact digit'),
    0x54b4:('391c','791e','center combined label and frame horizontally'),
    0x54b8:('0232','0132','center compact label vertically'),
}


def patch_slots(data: bytes):
    result=bytearray(data)
    for va,(expected,replacement,description) in PATCHES.items():
        pos=va-TEXT_DELTA;old=bytes.fromhex(expected);new=bytes.fromhex(replacement)
        if result[pos:pos+len(old)]!=old:raise ValueError(f'Unknown slot row instruction at {va:#x}: {description}')
        result[pos:pos+len(old)]=new
    return bytes(result)
