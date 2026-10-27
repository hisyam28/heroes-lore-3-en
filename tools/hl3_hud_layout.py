"""Guarded compact enemy-level drawing; preserve the general fonts and HUD data."""
import json,struct
from pathlib import Path
from hl3_font_runtime import TEXT_DELTA

ROOT=Path(__file__).resolve().parents[1]
MODE=127  # Private numeric HUD mode; normal font modes retain their behavior.
DIGIT_ADVANCE=4
LEVEL_X_OFFSET=16
DIGITS=[
 [7,5,5,5,7],[2,6,2,2,7],[7,1,7,4,7],[7,1,7,1,7],[5,5,7,1,1],
 [7,4,7,1,7],[7,4,7,5,7],[7,1,1,1,1],[7,5,7,5,7],[7,5,7,1,7],
]


def bl(src,dst):
    delta=(dst&~1)-(src+4)
    if delta%2 or not -(1<<22)<=delta<(1<<22):raise ValueError('Thumb call out of range')
    return struct.pack('<HH',0xf000|((delta>>12)&0x7ff),0xf800|((delta>>1)&0x7ff))


def branch(src,dst):
    delta=dst-(src+4)
    if delta%2 or not -2048<=delta<2048:raise ValueError('Thumb branch out of range')
    return 0xe000|((delta//2)&2047)


def patch(module):
    result=bytearray(module);allowed=set();allocations={}
    catalog=json.loads((ROOT/'translations/module-ui.json').read_text(encoding='utf-8'))['entries']
    byoffset={e['offset']:e for e in catalog}
    # Only use proven NUL padding after complete localized C strings, not
    # unknown zero-filled structures. Keep the first terminator intact.
    for name,offset,size in [('row',373664,36),('digits',374144,20),
                             ('wrapper',374052,12),('spacing',374092,6)]:
        e=byoffset[offset];text=e['translation'].encode('ascii')
        if module[offset:offset+len(text)+1]!=text+b'\0':raise ValueError('HUD padding label changed')
        address=(offset+len(text)+1+TEXT_DELTA+3)&~3
        p=address-TEXT_DELTA;end=(offset+len(e['source'].encode('cp949'))+4)&~3
        if p+size>end or module[p:p+size]!=bytes(size):raise ValueError('HUD padding is not available')
        # Reject independently referenced suffixes/padding in the loaded image.
        for target in range(p,p+size):
            pointer=struct.pack('<I',target+TEXT_DELTA)
            if any(module[q:q+4]==pointer for q in range(0x34,0x5dbb9,4)):
                raise ValueError('HUD padding has an independent pointer')
        allocations[name]=(address,p,size);allowed.update(range(p,p+size))
    row,digits,wrapper,spacing=[allocations[k][0] for k in ['row','digits','wrapper','spacing']]
    def write(name,words,literals=()):
        address,p,size=allocations[name]
        data=struct.pack('<'+'H'*len(words),*words)
        if literals:
            data+=bytes((-len(data))%4)+struct.pack('<'+'I'*len(literals),*literals)
        if len(data)!=size:raise ValueError('HUD helper size mismatch')
        result[p:p+size]=data
    # This private mode is only used for left-aligned, single-line HUD digits.
    # Once at row zero AND column zero of each subsequent digit, reduce X
    # by two pixels: a 3px digit then has a 1px gap instead of a 3px gap.
    # Keep the first glyph's origin and the original five-pixel LV baseline.
    # Ordinary measuring/wrapping modes never enter this private row helper.
    write('row',[0x980f,0x4320,0xd102,0x2e01,0xdd00,branch(row+10,spacing),0x006a,0x4b04,
                 0x5a9a,0x980f,0x0043,0x181b,0x40da,0x0752,0x0e52,0x4770], [digits-96])
    # The row-local pixel X was cached before entering the glyph loop; update
    # it with the carried cursor so the top row keeps the same spacing too.
    write('spacing',[0x3f02,0x970d,branch(spacing+4,row+12)])
    # Tail-call the existing text wrapper with the private glyph mode. The
    # caller's length, alignment, framebuffer and original LR are retained.
    write('wrapper',[0x247f,0x9401,0x4c00,0x4720],[0x3d71])
    packed=[sum(bits<<(3*y) for y,bits in enumerate(rows)) for rows in DIGITS]
    _,p,size=allocations['digits'];result[p:p+size]=struct.pack('<10H',*packed)
    replacements={
        # Both compiled general font banks are identical. Route all normal
        # Latin modes through the original compact-bank path, reserving the
        # former large-bank branch for this private mode. This avoids adding
        # a helper call/check to ordinary glyph drawing. Korean paths retain
        # their original mode value and code.
        0x3c9e:(bytes.fromhex('012a'),bytes.fromhex('7f2a')),
        0x3ca2:(bytes.fromhex('274b07980f99c3185a5c'),bl(0x3ca2,row)+bytes.fromhex('c046')*3),
        0x25fa:(bytes.fromhex('164c58f07cf8'),bl(0x25fa,wrapper)+bytes.fromhex('c046')),
        0x27d6:(bytes.fromhex('a34c57f08eff'),bl(0x27d6,wrapper)+bytes.fromhex('c046')),
        0x25f4:(bytes.fromhex('0f31'),struct.pack('<H',0x3100|LEVEL_X_OFFSET)),
        0x27d0:(bytes.fromhex('0f31'),struct.pack('<H',0x3100|LEVEL_X_OFFSET)),
    }
    for address,(old,new) in replacements.items():
        p=address-TEXT_DELTA
        if module[p:p+len(old)]!=old:raise ValueError(f'Unknown enemy HUD revision at {address:#x}')
        result[p:p+len(old)]=new;allowed.update(range(p,p+len(old)))
    assert len(result)==len(module)
    assert all(a==b for i,(a,b) in enumerate(zip(module,result)) if i not in allowed)
    for e in catalog:
        p=e['offset'];text=e['translation'].encode('ascii')
        assert result[p:p+len(text)+1]==text+b'\0'
    return bytes(result),{'enemy_level_digit_size':[3,5],'enemy_level_call_sites':2,
        'enemy_level_y_offset':17,'enemy_level_x_offset':LEVEL_X_OFFSET,'private_font_mode':MODE,
        'numeric_cursor_advance':DIGIT_ADVANCE,'numeric_letter_gap':1,
        'helper_bytes':sum(a[2] for a in allocations.values()),'per_draw_allocations':0,
        'general_font_bitmaps_unchanged':True,'module_size_preserved':True,
        'localized_strings_and_terminators_preserved':True}
