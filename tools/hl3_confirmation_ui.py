"""Cancel the active system popup on CLR without changing input mapping."""
import json,struct
from pathlib import Path
from hl3_font_runtime import TEXT_DELTA
from hl3_hud_layout import bl

ROOT=Path(__file__).resolve().parents[1]
YES_SLOTS={0x5a9c5,0x5ac4c}


def slot_capacity(module,offset,source_length):
    if offset not in YES_SLOTS:return source_length
    # Each two-byte Korean label has an independently guarded spare zero byte.
    # YES + NUL fits without moving this label or the following data.
    if module[offset:offset+4]!=bytes.fromhex('bfb90000'):
        raise ValueError('Unknown YES label storage')
    return 3


def patch(module):
    offset=0x5ad3c
    entry=next(e for e in json.loads((ROOT/'translations/module-ui.json').read_text(encoding='utf-8'))['entries'] if e['offset']==offset)
    text=entry['translation'].encode('ascii')
    if module[offset:offset+len(text)+1]!=text+b'\0':raise ValueError('Popup helper label changed')
    address=(offset+len(text)+1+TEXT_DELTA+3)&~3;p=address-TEXT_DELTA
    end=(offset+len(entry['source'].encode('cp949'))+4)&~3
    if p+12>end or module[p:p+12]!=bytes(12):raise ValueError('Popup helper padding unavailable')
    for target in range(p,p+12):
        pointer=struct.pack('<I',target+TEXT_DELTA)
        if any(module[q:q+4]==pointer for q in range(0x34,0x5dbb9,4)):
            raise ValueError('Popup helper padding is referenced')
    site=0x480ae-TEXT_DELTA
    if module[site:site+4]!=bytes.fromhex('12f025fb'):
        raise ValueError('Unknown system popup input revision')
    # Entered only after the existing active-popup check. CLR (-16) takes
    # the original cleanup and returns through the original stack frame.
    # Every other key tail-calls the original singleton dispatch in r5.
    helper=struct.pack('<3H',0x1c22,0x3210,0xd101)+bl(address+6,0x480fe)+struct.pack('<H',0x4728)
    result=bytearray(module);result[p:p+12]=helper;result[site:site+4]=bl(0x480ae,address)
    assert len(result)==len(module)
    allowed=set(range(p,p+12))|set(range(site,site+4))
    assert all(a==b for i,(a,b) in enumerate(zip(module,result)) if i not in allowed)
    return bytes(result),{'active_system_popup_clr_cancels':True,'guest_instruction_bytes_reserved':16,
        'touchpoint_and_key_mapping_unchanged':True,'original_popup_cleanup_used':True,
        'other_keys_use_original_dispatch':True,'module_size_preserved':True}
