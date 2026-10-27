"""Package the user-supplied Android icon into existing launcher resource slots."""
from pathlib import Path
from io import BytesIO
import hashlib,json,sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'work/analysis-deps'))
from PIL import Image

# Resource IDs and adaptive-icon XML stay unchanged. Tuples are legacy,
# adaptive background, adaptive foreground, and round icon for each density.
DENSITIES=[
 (48,108,('res/9w.png','res/3z.png','res/QZ.png','res/zR.png')),
 (72,162,('res/yn.png','res/I2.png','res/zr.png','res/8c.png')),
 (96,216,('res/FS.png','res/6h.png','res/Em.png','res/wb.png')),
 (144,324,('res/RJ.png','res/cV.png','res/Lf.png','res/fO.png')),
 (192,432,('res/o-.png','res/Gx.png','res/as.png','res/Gc.png')),
]
ENTRIES={name for _,_,names in DENSITIES for name in names}


def encode(image):
    stream=BytesIO();image.save(stream,format='PNG',optimize=True);return stream.getvalue()


def compile_icons(base,write_reports=True):
    source_path=ROOT/'translations/art/android-icon-source.png'
    source=Image.open(source_path).convert('RGBA');result={};checks=[]
    for legacy_size,adaptive_size,names in DENSITIES:
        for index,name in enumerate(names):
            size=legacy_size if index in (0,3) else adaptive_size
            if Image.open(BytesIO(base.read(name))).size!=(size,size):
                raise ValueError('Unknown launcher bitmap revision: '+name)
            canvas=Image.new('RGBA',(size,size),(0,0,0,0) if index==2 else (30,20,10,255))
            if index!=1:
                artwork=source.copy()
                # The revised square artwork already includes its background.
                # Legacy icons fill the square; the adaptive layer fits the
                # crest within the mask without introducing a white border.
                fraction=72/108 if index==2 else 1.0
                budget=round(size*fraction);artwork.thumbnail((budget,budget),Image.Resampling.LANCZOS)
                xy=((size-artwork.width)//2,(size-artwork.height)//2)
                canvas.alpha_composite(artwork,xy)
            result[name]=encode(canvas)
            checks.append({'entry':name,'dimensions':[size,size]})
    # Large preview uses the legacy packaging, preserving the user's source.
    preview=Image.new('RGBA',(512,512),(30,20,10,255));art=source.copy();art.thumbnail((512,512),Image.Resampling.LANCZOS)
    preview.alpha_composite(art,((512-art.width)//2,(512-art.height)//2))
    if write_reports:
        preview.save(ROOT/'reports/android-icon-preview.png')
        (ROOT/'reports/android-icon-validation.json').write_text(json.dumps({
            'source_sha256':hashlib.sha256(source_path.read_bytes()).hexdigest(),
            'launcher_bitmaps':checks,'adaptive_xml_and_resource_ids_unchanged':True,
            'source_artwork_redrawn':False},indent=2)+'\n',encoding='utf-8')
    return result
