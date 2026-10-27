#!/usr/bin/env python3
"""Regression checks for the actual failures found in the previous build."""
from __future__ import annotations
import json
import tempfile
import zipfile
from pathlib import Path
from hl3_event_text import compile_catalog
from hl3_curate_optimized import pack_review
from hl3_font_runtime import patch_metrics,TEXT_DELTA
from hl3_native_profile import rekey,file_offset
from hl3_markup import latin_copy,sequence
from hl3_shared_formats import validate as validate_shared_formats

ROOT=Path(__file__).resolve().parents[1]


def rejects(function,message):
    try:function()
    except ValueError:return
    raise AssertionError(message)


def main():
    original=ROOT/'work/original';module=(original/'binary.mod').read_bytes()
    translated=(ROOT/'work/optimized/binary.mod').read_bytes()
    validate_shared_formats(translated)
    bad=bytearray(translated);bad[0x5b4dc:0x5b4e1]=b'%d\0\0\0'
    rejects(lambda:validate_shared_formats(bad),'accepted a broken shared %s%d alias')
    label='COMBO: ';assert '%s%d' % (label,0)=='COMBO: 0'
    with zipfile.ZipFile(ROOT/'work/heroes-lore-3-final.apk') as apk:native=apk.read('lib/arm64-v8a/libmain.so')
    # An unrelated edit inside a native-accelerated function must never receive
    # the trusted old hooks, even if its font/text fields otherwise look valid.
    bad=bytearray(translated);bad[file_offset(module,0x2dd7c)]^=1
    rejects(lambda:rekey(native,module,bytes(bad)),'accepted altered accelerated code')
    bad=bytearray(translated);bad[file_offset(module,0x4840)]^=1
    rejects(lambda:rekey(native,module,bytes(bad)),'accepted broken loader expectation')
    bad=bytearray(module);bad[0x3614-TEXT_DELTA]^=1
    rejects(lambda:patch_metrics(bytes(bad)),'accepted an unknown font revision')
    # This exact failure mode previously left only FIRST and lost the reward.
    reviewed=pack_review('$[NPC]@ FIRST. IMPORTANT REWARD: 300G.',18)
    assert len(reviewed)>18 and 'REWARD: 300G' in reviewed
    assert latin_copy("'[LEA]@ DON'T USE SIEN'S POWER.","'[LEA]@") == "'[LEA]@ DONT USE SIENS POWER."
    assert sequence(latin_copy("'[LEA]@ DON'T.","'[LEA]@"))=="'@"
    row=json.loads((ROOT/'translations/event-catalog.json').read_text(encoding='utf-8'))['entries'][0]
    with tempfile.TemporaryDirectory(dir=ROOT/'work',prefix='event-regression-') as tmp:
        tmp=Path(tmp)
        def compile_value(value):
            entry=dict(row);entry['translation']=value
            cat={'format':'heroes-lore-3-event-text-v1','entries':[entry]}
            path=tmp/'catalog.json';path.write_text(json.dumps(cat),encoding='utf-8')
            return compile_catalog(original,path,tmp/'out')
        # The old five-marker validator missed apostrophes and double quotes.
        rejects(lambda:compile_value(row['translation']+"'"),'accepted an accidental color command')
        rejects(lambda:compile_value(row['translation']+'\0'),'accepted embedded NUL')
        bad_prefix=dict(row);bad_prefix['prefix_hex']='ff'
        cat={'format':'heroes-lore-3-event-text-v1','entries':[bad_prefix]}
        path=tmp/'prefix.json';path.write_text(json.dumps(cat),encoding='utf-8')
        rejects(lambda:compile_catalog(original,path,tmp/'out'),'accepted a changed opcode prefix')
    print('Regression checks passed: acceleration guards, loader guards, font revision guard, no tail deletion, seven control bytes, NUL and opcode-prefix rejection.')


if __name__=='__main__':main()
