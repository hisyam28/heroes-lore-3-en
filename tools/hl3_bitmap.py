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


def localize_title(original: Path,output: Path):
    rel=Path('res/menu/title_bm');data=(original/rel).read_bytes();records=parse(data)
    assert build(records)==data
    source=records[12]
    assert source[0]==12 and struct.unpack_from('<4H',source,1)==(146,60,146,32)
    image=Image.open(ROOT/'translations/art/title-logo-source.png').convert('RGBA')
    bbox=image.getbbox()
    if not bbox:raise ValueError('Generated title logo is empty')
    # Fit the generated English artwork inside the original native sprite.
    image=image.crop(bbox);image.thumbnail((146,60),Image.Resampling.LANCZOS)
    canvas=Image.new('RGBA',(146,60));canvas.alpha_composite(image,((146-image.width)//2,(60-image.height)//2))
    px=list(canvas.getdata());opaque=[p[:3] for p in px if p[3]>=128]
    colors=Image.new('RGB',(len(opaque),1));colors.putdata(opaque)
    palette=colors.quantize(colors=31,method=Image.Quantize.MEDIANCUT).getpalette()
    values=[rgb565(tuple(palette[i*3:i*3+3])) for i in range(31)]
    choices=[rgb(v) for v in values]
    indices=bytearray()
    for pixel in px:
        if pixel[3]<128:indices.append(0);continue
        index=min(range(31),key=lambda i:sum((pixel[c]-choices[i][c])**2 for c in range(3)))
        indices.append(index+1)
    records[12]=source[:9]+struct.pack('<32H',0xf81f,*values)+indices
    result=build(records)
    if len(result)!=len(data):raise ValueError('Title bitmap size changed')
    if any(a!=b for i,(a,b) in enumerate(zip(parse(data),parse(result))) if i!=12):
        raise ValueError('Unrelated title sprites changed')
    target=output/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(result)
    preview=ROOT/'translations/art/title-logo-146x60.png'
    decode(records[12]).save(preview)
    return {'sprite':12,'dimensions':[146,60],'palette_entries':32,'file_size_preserved':True}
