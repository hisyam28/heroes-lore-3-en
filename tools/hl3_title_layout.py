"""Preview the static first title frame from its original CIF sprite placements."""
import struct
from hl3_bitmap import parse, decode, Image, ROOT


def placements(cif):
    if cif[:6] != bytes.fromhex('010004010117'):
        raise ValueError('Unrecognized title composition')
    pos = 6
    parts = []
    for _ in range(23):
        flags, sprite, x, y = struct.unpack_from('<BBbb', cif, pos)
        pos += 4
        if flags & 0x80:
            pos += 5  # original scaled/rotated transition effects
        else:
            parts.append((flags, sprite, x, y))
    if pos != 0x6c:
        raise ValueError('Title composition boundary changed')
    return parts


def render(records, cif):
    canvas = Image.new('RGBA', (280, 180), (0, 0, 0, 255))
    for flags, sprite, x, y in placements(cif):
        image = decode(records[sprite])
        if flags & 0x20:
            image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        canvas.alpha_composite(image, (140 + x - image.width // 2,
                                       90 + y - image.height // 2))
    return canvas.convert('RGB')


if __name__ == '__main__':
    original = ROOT / 'work/original/res/menu'
    cif = (original / 'title_cif').read_bytes()
    for name, path in [('original', original / 'title_bm'),
                       ('current', ROOT / 'work/optimized/res/menu/title_bm')]:
        render(parse(path.read_bytes()), cif).resize((1120, 720), Image.Resampling.NEAREST).save(
            ROOT / 'work' / f'title-composed-{name}.png')
