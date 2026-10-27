#!/usr/bin/env python3
"""Strict artifact checks for the optimized APK; fail on any unmet invariant."""
from __future__ import annotations
import argparse
import collections
import hashlib
import json
import re
import struct
import zipfile
from io import BytesIO
from pathlib import Path
from hl3_assets import find_game_jar
from hl3_text import parse_string_table,build_string_table
from hl3_record_text import parse as parse_records,build as build_records
from hl3_item_names import parse_records as parse_items
from hl3_markup import sequence,MARKUP
from hl3_font_runtime import patch_metrics,build_font,TEXT_DELTA,PATCHES as FONT_PATCHES
from hl3_native_profile import rekey,profile_region
from hl3_locations import location_suffix
from hl3_bitmap import parse as parse_bitmaps,decode
from hl3_skill_text import parse as parse_skills,DESCRIPTIONS
from hl3_item_descriptions import split_tail,COPY as ITEM_DESCRIPTIONS
from hl3_enemy_text import NAMES as ENEMY_NAMES
from hl3_native_ui import localize as localize_native_ui
from hl3_shared_formats import validate as validate_shared_formats
from hl3_home_ui import patch_slots,PATCHES as SLOT_PATCHES

ROOT=Path(__file__).resolve().parents[1]


def catalog(name):return json.loads((ROOT/'translations'/name).read_text(encoding='utf-8'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('apk',type=Path,nargs='?',default=ROOT/'work/heroes-lore-3-en-optimized.apk')
    args=parser.parse_args();original=ROOT/'work/original'
    with zipfile.ZipFile(args.apk) as apk:
        assert apk.testzip() is None
        jar_bytes,jar_name=find_game_jar(apk)
        with zipfile.ZipFile(BytesIO(jar_bytes)) as jar:
            assert jar.testzip() is None
            inv=catalogs_inv=json.loads((ROOT/'reports/source-inventory.json').read_text(encoding='utf-8'))
            expected_names={e['path'] for e in inv['entries']}
            assert {i.filename for i in jar.infolist() if not i.is_dir()}==expected_names
            overlay={p.relative_to(ROOT/'work/optimized').as_posix():p for p in (ROOT/'work/optimized').rglob('*') if p.is_file()}
            for name in expected_names:
                data=jar.read(name)
                assert data==(overlay[name].read_bytes() if name in overlay else (original/name).read_bytes()),name
            events=catalog('event-catalog.json')['entries'];byfile=collections.defaultdict(dict)
            location_count=0;restored_prefix_bytes=0
            old_entries={e['id']:e for e in json.loads((ROOT/'work/baseline-final-catalogs/event-catalog.json').read_text(encoding='utf-8'))['entries']}
            for e in events:
                byfile[e['file']][e['segment']]=e
                assert e['translation'] and e['translation'].isascii() and '\0' not in e['translation']
                assert sequence(e['source'])==sequence(e['translation']),e['id']
                assert len(e['translation'])<=len(e['source'].encode('cp949')),e['id']
                if location_suffix(e['source']):
                    location_count+=1
                    old=old_entries[e['id']]
                    restored_prefix_bytes+=len(bytes.fromhex(e.get('prefix_hex') or ''))-len(bytes.fromhex(old.get('prefix_hex') or ''))
            event_count=0
            for name,rows in byfile.items():
                source=(original/name).read_bytes();output=jar.read(name)
                assert len(source)==len(output),name
                a=source.split(b'\0');b=output.split(b'\0');assert len(a)==len(b),name
                for i,(raw,translated) in enumerate(zip(a,b)):
                    assert len(raw)==len(translated),(name,i)
                    if i not in rows:assert raw==translated,(name,i);continue
                    e=rows[i];prefix=bytes.fromhex(e.get('prefix_hex') or '')
                    assert raw==prefix+e['source'].encode('cp949'),e['id']
                    text=e['translation'].encode('ascii')
                    assert translated==prefix+text+b' '*(len(raw)-len(prefix)-len(text)),e['id']
                    event_count+=1
            assert event_count==4767
            ui=catalog('catalog.json')['entries'];uifiles=collections.defaultdict(dict)
            for e in ui:uifiles[e['file']][e['index']]=e
            for name,rows in uifiles.items():
                source=parse_string_table((original/name).read_bytes())
                values=[rows[i]['translation'] or s for i,s in enumerate(source)]
                assert all(v.isascii() for v in values)
                assert jar.read(name)==build_string_table(values),name
            main_ui=parse_string_table(jar.read('res/dat/InGame_txt'))
            assert main_ui[17:19]==['NM','EFC'] and all(main_ui[:7])
            item_count=0
            for name in sorted({e['file'] for e in catalog('item-catalog.json')['entries']}):
                a=parse_items((original/'res/dat'/name).read_bytes(),name)
                b=parse_items(jar.read('res/dat/'+name),name)
                assert len(a)==len(b)
                for (_,ar,an,at),(_,br,bn,bt) in zip(a,b):
                    if name in ITEM_DESCRIPTIONS:
                        price,desc,tail=split_tail(ar[1+len(an):],name)
                        newprice,newdesc,newtail=split_tail(br[1+len(bn):],name)
                        assert price==newprice and tail==newtail,name
                    else:assert ar[1+len(an):]==br[1+len(bn):],name
                    assert bt.isascii() and 0<len(bt)<=22,name
                    item_count+=1
            item_descriptions=catalog('item-descriptions.json')['entries']
            for e in item_descriptions:
                name=Path(e['file']).name
                a=parse_items((original/e['file']).read_bytes(),name)[e['record']]
                b=parse_items(jar.read(e['file']),name)[e['record']]
                assert split_tail(a[1][1+len(a[2]):],name)[1]==e['source']
                assert split_tail(b[1][1+len(b[2]):],name)[1]==e['translation'] and e['translation'].isascii()
            enemy_entries=catalog('enemy-text.json')['entries']
            for name in sorted({e['file'] for e in enemy_entries}):
                a=parse_records((original/name).read_bytes(),1,name);b=parse_records(jar.read(name),1,name)
                entries=[e for e in enemy_entries if e['file']==name]
                assert len(a)==len(b)==len(entries)==161
                for i,((texts,tail),(newtexts,newtail),e) in enumerate(zip(a,b,entries)):
                    assert tail==newtail and texts==[e['source']] and newtexts==[e['translation']]
                    assert newtexts[0].isascii() and sequence(texts[0])==sequence(newtexts[0])
            records=catalog('record-text.json');record_fields=0
            for name,n in records['field_counts'].items():
                a=parse_records((original/name).read_bytes(),n,name);b=parse_records(jar.read(name),n,name)
                assert len(a)==len(b) and build_records(a)==(original/name).read_bytes()
                rows={(e['record'],e['field']):e for e in records['entries'] if e['file']==name}
                for i,((texts,tail),(translated,newtail)) in enumerate(zip(a,b)):
                    assert tail==newtail
                    for j,(s,t) in enumerate(zip(texts,translated)):
                        e=rows[(i,j)];assert s==e['source'] and t==e['translation']
                        assert t.isascii();record_fields+=1
            skill_catalog=catalog('skill-text.json')['entries'];skill_records=0;skill_changes=0
            for filename in DESCRIPTIONS:
                name='res/skill/'+filename
                source=(original/name).read_bytes();output=jar.read(name)
                a=parse_skills(source,name);b=parse_skills(output,name)
                assert len(a)==len(b)==15 and len(source)==len(output)
                rows={(e['record'],e['field']):e for e in skill_catalog if e['file']==name}
                allowed=set()
                for i,(old,new) in enumerate(zip(a,b)):
                    for key in ['offset','size','kind','tail_offset','tail','name_offset','name_size','description_offset','description_size']:
                        assert old[key]==new[key],(name,i,key)
                    for field in ['name','description']:
                        entry=rows[(i,field)]
                        assert old[field]==entry['source'] and new[field]==entry['translation']
                        assert new[field].isascii() and '\0' not in new[field]
                        pos=old[field+'_offset'];size=old[field+'_size'];raw=new[field].encode('ascii')
                        assert output[pos:pos+size]==raw+b'\0'*(size-len(raw))
                        allowed.update(range(pos,pos+size));skill_changes+=int(old[field]!=new[field])
                    skill_records+=1
                assert all(x==y for pos,(x,y) in enumerate(zip(source,output)) if pos not in allowed),name
            assert len(skill_catalog)==210 and skill_records==105 and skill_changes==163
            module=bytearray((original/'binary.mod').read_bytes())
            for e in catalog('module-ui.json')['entries']:
                p=e['offset'];src=e['source'].encode('cp949');new=e['translation'].encode('ascii')
                assert module[p:p+len(src)+1]==src+b'\0'
                module[p:p+len(src)]=new+b'\0'*(len(src)-len(new))
            assert jar.read('binary.mod')==patch_slots(patch_metrics(bytes(module)))
            validate_shared_formats(jar.read('binary.mod'))
            assert jar.read('res/font/eng5')==jar.read('res/font/eng7')==build_font()
            assert (original/'binary.mod').read_bytes()[0x5b2bc-TEXT_DELTA:0x5b2bc-TEXT_DELTA+7].decode('ascii')==MARKUP
            sprites=parse_bitmaps(jar.read('res/menu/title_bm'));old_sprites=parse_bitmaps((original/'res/menu/title_bm').read_bytes())
            assert len(sprites)==len(old_sprites)==17
            assert all(a==b for i,(a,b) in enumerate(zip(old_sprites,sprites)) if i!=12)
            assert len(sprites[12])==len(old_sprites[12]) and decode(sprites[12]).size==(146,60)
            with zipfile.ZipFile(ROOT/'work/heroes-lore-3-final.apk') as base:
                native,profile_report=rekey(base.read('lib/arm64-v8a/libmain.so'),(original/'binary.mod').read_bytes(),jar.read('binary.mod'))
                native,native_ui=localize_native_ui(native)
                assert apk.read('lib/arm64-v8a/libmain.so')==native
                for name in base.namelist():
                    if name.startswith('META-INF/') or name in ('lib/arm64-v8a/libmain.so','assets/hero3_fixed.zip'):continue
                    assert apk.read(name)==base.read(name),name
                prior_jar,_=find_game_jar(base)
                with zipfile.ZipFile(BytesIO(prior_jar)) as old_jar:
                    changed_events=sum(e['translation']!=old_entries[e['id']]['translation'] or e['source']!=old_entries[e['id']]['source'] for e in events)
                    changed_resources=sum(jar.read(name)!=old_jar.read(name) for name in expected_names)
            assert jar.read('res/dat/i15_dat')==(original/'res/dat/i15_dat').read_bytes()
            result={'apk':args.apk.name,'bytes':args.apk.stat().st_size,'sha256':hashlib.sha256(args.apk.read_bytes()).hexdigest(),
                    'game_resources':len(expected_names),'resource_overlays':len(overlay),'changed_resources_vs_previous_final':changed_resources,
                    'event_fields':event_count,'event_files_with_text':len(byfile),'event_fields_changed_vs_previous_final':changed_events,
                    'event_file_lengths_and_terminators_preserved':True,'untouched_event_bytes_identical':True,
                    'engine_control_bytes':MARKUP,'control_sequences_match':True,'locations':location_count,
                    'additional_original_prefix_bytes_protected':restored_prefix_bytes,
                    'ui_tables':len(uifiles),'ui_slots':len(ui),'item_names':item_count,'prefixed_record_fields':record_fields,
                    'item_descriptions':len(item_descriptions),'enemy_names':len(enemy_entries),
                    'native_save_notifications':sum(e['group']=='save' for e in native_ui),
                    'native_settings_strings':sum(e['group']=='settings' for e in native_ui),
                    'slot_layout_instruction_patches':len(SLOT_PATCHES),'shared_format_suffixes_preserved':2,
                    'skill_records':skill_records,'translated_skill_fields':skill_changes,'skill_metadata_bytes_preserved':skill_records*30,
                    'module_labels':len(catalog('module-ui.json')['entries']),'font_instruction_patches':len(FONT_PATCHES),
                    'native_accelerators':profile_report,'sound_android_code_and_other_assets_unchanged':True,
                    'opaque_i15_unchanged':True,'device_fps_measured':False,'all_checks_passed':True}
    (ROOT/'reports/optimized-build-validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
