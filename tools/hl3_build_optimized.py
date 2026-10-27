#!/usr/bin/env python3
"""Build a clean overlay and unsigned optimized APK from reviewed catalogs."""
from __future__ import annotations
import argparse
import json
import re
import zipfile
from pathlib import Path
from hl3_text import compile_catalog as compile_ui
from hl3_event_text import compile_catalog as compile_events, MARKUP
from hl3_record_text import compile_catalog as compile_records
from hl3_item_names import parse_records
from hl3_font_runtime import apply as apply_font
from hl3_rebuild import build as build_apk
from hl3_native_profile import rekey
from hl3_bitmap import localize_title
from hl3_skill_text import compile_skills
from hl3_enemy_text import compile_enemies
from hl3_item_descriptions import compile_descriptions
from hl3_native_ui import localize as localize_native_ui
from hl3_shared_formats import validate as validate_shared_formats

ROOT=Path(__file__).resolve().parents[1]


def compile_items(original: Path,output: Path):
    cat=json.loads((ROOT/'translations/item-catalog.json').read_text(encoding='utf-8'))
    byfile={}
    for e in cat['entries']:
        if Path(e['file']).name!=e['file']:raise ValueError('Unsafe item filename')
        rows=byfile.setdefault(e['file'],{})
        if e['record'] in rows:raise ValueError('Duplicate item record')
        rows[e['record']]=e
    count=0
    for filename,rows in byfile.items():
        source=parse_records((original/'res/dat'/filename).read_bytes(),filename)
        if set(rows)!=set(range(len(source))):raise ValueError(f'{filename}: incomplete item catalog')
        out=bytearray()
        for i,(_,record,old_raw,old_text) in enumerate(source):
            e=rows[i];marker=e.get('marker') or ''
            if old_text!=marker+e['source']:raise ValueError(f'{filename}#{i}: item source mismatch')
            title=marker+e['translation']
            if not title or len(title)>22:raise ValueError(f'{filename}#{i}: name exceeds UI budget')
            raw=title.encode('ascii')
            if b'\0' in raw:raise ValueError('NUL in item name')
            prefix=re.match(r"[|${}@']*",old_text).group()
            if not title.startswith(prefix):raise ValueError(f'{filename}#{i}: item marker prefix changed')
            payload=bytes([len(raw)])+raw+record[1+len(old_raw):]
            out.extend(len(payload).to_bytes(2,'little'));out.extend(payload);count+=1
        target=output/'res/dat'/filename;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(out)
    return count


def compile_module(original: Path,output: Path):
    source=(original/'binary.mod').read_bytes();data=bytearray(source)
    cat=json.loads((ROOT/'translations/module-ui.json').read_text(encoding='utf-8'))
    for e in cat['entries']:
        offset=e['offset'];old=e['source'].encode('cp949');new=e['translation'].encode('ascii')
        if source[offset:offset+len(old)+1]!=old+b'\0':raise ValueError(f"Module source mismatch: {e['id']}")
        if len(new)>len(old):raise ValueError(f"Module string overflow: {e['id']}")
        data[offset:offset+len(old)]=new+b'\0'*(len(old)-len(new))
    validate_shared_formats(data)
    (output/'binary.mod').write_bytes(data)
    return len(cat['entries'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',type=Path,default=ROOT/'work/heroes-lore-3-final.apk')
    parser.add_argument('--overlay',type=Path,default=ROOT/'work/optimized')
    parser.add_argument('--apk',type=Path,default=ROOT/'work/heroes-lore-3-en-optimized-unsigned.apk')
    args=parser.parse_args()
    original=ROOT/'work/original';output=args.overlay
    output.mkdir(parents=True,exist_ok=True)
    # Existing files may be overwritten deterministically, but unrelated stale
    # overlay files must not silently enter this build.
    allowed={'binary.mod','res/font/eng5','res/font/eng7','res/menu/title_bm'}
    for name in ['catalog.json','event-catalog.json','record-text.json']:
        allowed|={e['file'] for e in json.loads((ROOT/'translations'/name).read_text(encoding='utf-8'))['entries']}
    allowed|={'res/dat/'+e['file'] for e in json.loads((ROOT/'translations/item-catalog.json').read_text(encoding='utf-8'))['entries']}
    allowed|={f'res/skill/s{i}_dat' for i in range(4,11)}
    allowed|={'res/dat/enemy_dat','res/dat/enemyh_dat'}
    unexpected={p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file()}-allowed
    if unexpected:raise ValueError(f'Unexpected files in optimized overlay: {sorted(unexpected)}')
    ui=compile_ui(original,ROOT/'translations/catalog.json',output)
    events,skipped=compile_events(original,ROOT/'translations/event-catalog.json',output)
    assert events==4767 and skipped==0
    items=compile_items(original,output)
    descriptions=compile_descriptions(original,output)
    enemies=compile_enemies(original,output)
    records=compile_records(original,ROOT/'translations/record-text.json',output)
    labels=compile_module(original,output)
    skills=compile_skills(original,output)
    apply_font(output)
    title_report=localize_title(original,output)
    with zipfile.ZipFile(args.base) as base:
        native,profile_report=rekey(base.read('lib/arm64-v8a/libmain.so'),
                                    (original/'binary.mod').read_bytes(),
                                    (output/'binary.mod').read_bytes())
    native,native_ui_report=localize_native_ui(native)
    resource_apk=args.apk.with_name(args.apk.stem+'-resources.apk')
    replaced,entries=build_apk(args.base,output,resource_apk)
    with zipfile.ZipFile(resource_apk) as source,zipfile.ZipFile(args.apk,'w') as target:
        target.comment=source.comment
        for info in source.infolist():
            data=native if info.filename=='lib/arm64-v8a/libmain.so' else source.read(info.filename)
            target.writestr(info,data)
    (ROOT/'reports/native-profile-validation.json').write_text(json.dumps(profile_report,indent=2)+'\n',encoding='utf-8')
    (ROOT/'reports/title-localization.json').write_text(json.dumps(title_report,indent=2)+'\n',encoding='utf-8')
    (ROOT/'reports/native-ui-validation.json').write_text(json.dumps(native_ui_report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'UI tables={ui}; events={events}; items={items}; translated quest/character fields={records}; module labels={labels}; skill fields={skills}.')
    print(f'Built {args.apk} with {replaced} resource overlays and {entries} APK entries. Align and sign next.')
    print('Rekeyed all four native graphics accelerators; all 14 loader-patch expectations match.')
    print(f'Enemy names={enemies}; item descriptions={descriptions}; native save notifications={len(native_ui_report)}; shared format suffixes=2.')


if __name__=='__main__':main()
