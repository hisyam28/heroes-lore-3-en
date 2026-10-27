"""Confirmed HL3 bitmap container: u16 count, u32 payload sizes, RGB565 palettes."""
from __future__ import annotations
import struct
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'work/analysis-deps'))
from PIL import Image


def parse(data: bytes):
    count=int.from_bytes(data[:2],'little');pos=2;records=[]
    for _ in range(count):
        if pos+4>len(data):raise ValueError('Truncated bitmap record')
        n=int.from_bytes(data[pos:pos+4],'little');pos+=4
        if pos+n>len(data):raise ValueError('Truncated bitmap payload')
        records.append(data[pos:pos+n]);pos+=n
    if pos!=len(data):raise ValueError('Bitmap container has unparsed bytes')
    return records


def build(records):
    return len(records).to_bytes(2,'little')+b''.join(len(r).to_bytes(4,'little')+r for r in records)


def rgb(value):
    return ((value>>11)*255//31,((value>>5)&63)*255//63,(value&31)*255//31)


def rgb565(color):
    r,g,b=color
    return ((r*31+127)//255)<<11 | ((g*63+127)//255)<<5 | ((b*31+127)//255)


def decode(data: bytes):
    fmt=data[0];w,h,pitch,colors=struct.unpack_from('<4H',data,1)
    if fmt not in (11,12):raise ValueError('Unsupported bitmap pixel format')
    pal=struct.unpack_from('<'+'H'*colors,data,9);raw=data[9+2*colors:]
    stride=(pitch+1)//2 if fmt==11 else pitch
    if len(raw)!=stride*h:raise ValueError('Bitmap pitch/height mismatch')
    pixels=[]
    for y in range(h):
        for x in range(w):
            index=raw[y*stride+(x//2 if fmt==11 else x)]
            if fmt==11:index=index>>4 if x%2==0 else index&15
            pixels.append((*rgb(pal[index]),255 if index else 0))
    out=Image.new('RGBA',(w,h));out.putdata(pixels)
    return out


def compile_title(data: bytes,cif: bytes,image):
    from hl3_title_layout import placements
    records=parse(data)
    assert build(records)==data
    originals=list(records)
    assert records[12][0]==12 and struct.unpack_from('<4H',records[12],1)==(146,60,146,32)
    # Sample the five connected crest pieces from ONE full-scene source. A
    # separately generated central rectangle cannot keep the Roman III and
    # adjoining ornament in the same scale and position as its neighbors.
    if image.getextrema()[3]!=(255,255):raise ValueError('Title scene must be fully opaque')
    if abs(image.width/image.height-14/9)>0.005:raise ValueError('Title source must use the full 14:9 composition')
    canvas=image.resize((280,180),Image.Resampling.LANCZOS)
    parts={i:(flags,x,y) for flags,i,x,y in placements(cif) if 12<=i<=16}
    assert set(parts)==set(range(12,17))
    crops={}
    for i,(flags,x,y) in parts.items():
        assert flags==0
        source=records[i];fmt=source[0]
        w,h,pitch,colors=struct.unpack_from('<4H',source,1)
        left,top=140+x-w//2,90+y-h//2
        crops[i]=[left,top,left+w,top+h]
        tile=canvas.crop(tuple(crops[i]))
        palette=struct.unpack_from('<'+'H'*colors,source,9)
        choices=[rgb(v) for v in palette[1:]]
        start=9+2*colors;raw=bytearray(source[start:])
        stride=(pitch+1)//2 if fmt==11 else pitch
        for y in range(h):
            for x in range(w):
                pixel=tile.getpixel((x,y))
                index=1+min(range(colors-1),key=lambda k:sum((pixel[c]-choices[k][c])**2 for c in range(3)))
                p=y*stride+(x//2 if fmt==11 else x)
                if fmt==11:
                    raw[p]=(raw[p]&15)|(index<<4) if x%2==0 else (raw[p]&240)|index
                else:raw[p]=index
        records[i]=source[:start]+bytes(raw)
    result=build(records)
    if len(result)!=len(data):raise ValueError('Title bitmap size changed')
    if any(a!=b for i,(a,b) in enumerate(zip(originals,records)) if i not in parts):
        raise ValueError('Unrelated title sprites changed')
    report={'sprites':list(parts),'central_tile_dimensions':[146,60],'file_size_preserved':True,
            'subtitle':'STIGMATA OF EARTH','wordmark_has_extra_roman_iii':False,
            'replacement_mode':'five connected crest pieces sampled from one full composition',
            'source_canvas':[280,180],'source_rectangles':crops,
            'composition_coordinates_and_animation_unchanged':True,
            'palette_colors_reused_from_original':True,
            'transparent_pixels':0,'other_12_sprites_identical':True}
    return result,report


def localize_title(original: Path,output: Path):
    from hl3_title_layout import render
    rel=Path('res/menu/title_bm')
    cif=(original/'res/menu/title_cif').read_bytes()
    image=Image.open(ROOT/'translations/art/title-logo-source.png').convert('RGBA')
    result,report=compile_title((original/rel).read_bytes(),cif,image)
    records=parse(result)
    target=output/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(result)
    decode(records[12]).save(ROOT/'translations/art/title-logo-146x60.png')
    decode(records[12]).resize((1168,480),Image.Resampling.NEAREST).save(ROOT/'reports/title-tile-preview.png')
    render(records,cif).resize((1120,720),Image.Resampling.NEAREST).save(ROOT/'reports/title-composition-preview.png')
    return report
