#!/usr/bin/env python3
"""Rekey the shipped, hash-gated HL3 accelerators after a guarded module edit.

The APK embeds a TOML profile in libmain.so, keyed by the original module MD5.
Editing only binary.mod disables that entire profile, including all four host
graphics accelerators. Change only its 32 ASCII hash bytes after proving that
the hooks' code and all loader patch expectations are unchanged.
"""
from __future__ import annotations
import hashlib
import struct
import tomllib
from pathlib import Path

ORIGINAL_MD5='6a352944bb43c0789ca9f4b6f0702f4b'
NAME=b'name = "Hero3 binary.mod (LGT)"'
HOOK_RANGES=[(0x2dd7c,0x2e8c4),(0x2b700,0x2b8f8),
             (0x2e8c4,0x2fdd0),(0x2b8f8,0x2bad0)]


def sections(data: bytes):
    header=struct.unpack_from('<16sHHIIIIIHHHHHH',data)
    return [struct.unpack_from('<IIIIIIIIII',data,header[6]+i*header[11])
            for i in range(header[12])]


def file_offset(data: bytes,va: int):
    for s in sections(data):
        if s[1]!=8 and s[3]<=va<s[3]+s[5]:return s[4]+va-s[3]
    raise ValueError(f'Address 0x{va:x} is not file-backed')


def profile_region(native: bytes):
    if native.count(NAME)!=1:raise ValueError('Expected exactly one HL3 native profile')
    name=native.index(NAME);start=native.rfind(b'[[entry]]',0,name)
    end=native.find(b'[[entry]]',name)
    if start<0 or end<0:raise ValueError('Native profile boundaries not found')
    text=native[start:end].decode('utf-8').replace('\r\n','\n').replace('\r','')
    return start,end,tomllib.loads(text)['entry'][0]


def rekey(native: bytes,original: bytes,translated: bytes):
    if hashlib.md5(original).hexdigest()!=ORIGINAL_MD5:
        raise ValueError('This accelerator profile is for a different original module')
    if len(original)!=len(translated) or sections(original)!=sections(translated):
        raise ValueError('ELF addresses or layout changed')
    start,end,profile=profile_region(native)
    if profile['hash']!=ORIGINAL_MD5:raise ValueError('Base APK native profile is not original')
    expected_kinds={'blit565_lgt','blend565_lgt','blit_lut565_lgt','tint_rect565_lgt'}
    if {h['kind'] for h in profile['hook']}!=expected_kinds:
        raise ValueError('Unexpected accelerator set')
    for a,b in HOOK_RANGES:
        pos=file_offset(original,a);length=b-a
        if original[pos:pos+length]!=translated[pos:pos+length]:
            raise ValueError(f'Accelerated code changed at 0x{a:x}..0x{b:x}')
    for patch in profile.get('patch',[]):
        pos=file_offset(original,patch['pc']);expected=bytes.fromhex(patch['expect'])
        if original[pos:pos+len(expected)]!=expected or translated[pos:pos+len(expected)]!=expected:
            raise ValueError(f"Native loader patch expectation changed at 0x{patch['pc']:x}")
    new_hash=hashlib.md5(translated).hexdigest()
    old_line=f'hash = "{ORIGINAL_MD5}"'.encode('ascii')
    new_line=f'hash = "{new_hash}"'.encode('ascii')
    region=native[start:end]
    if region.count(old_line)!=1:raise ValueError('Ambiguous MD5 field')
    at=start+region.index(old_line)
    result=native[:at]+new_line+native[at+len(old_line):]
    assert len(result)==len(native)
    _,_,updated=profile_region(result)
    assert updated['hash']==new_hash
    old_structure=dict(profile);new_structure=dict(updated)
    old_structure.pop('hash');new_structure.pop('hash')
    assert old_structure==new_structure
    return result,{'original_module_md5':ORIGINAL_MD5,'translated_module_md5':new_hash,
                   'native_profile_offset':at,'enabled_hook_kinds':sorted(expected_kinds),
                   'loader_patch_expectations_verified':len(profile.get('patch',[])),
                   'native_code_changed':False,
                   'native_profile_hash_bytes_changed':sum(a!=b for a,b in zip(native,result))}
