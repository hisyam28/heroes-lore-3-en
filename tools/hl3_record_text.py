#!/usr/bin/env python3
"""Parse confirmed u16-sized records with u8-sized CP949 text fields."""
from __future__ import annotations
import json
from pathlib import Path


def parse(data: bytes,fields: int,source='<bytes>'):
    records=[];pos=0
    while pos<len(data):
        if pos+2>len(data):raise ValueError(f'{source}: truncated record header')
        size=int.from_bytes(data[pos:pos+2],'little');end=pos+2+size
        if not size or end>len(data):raise ValueError(f'{source}: invalid record at {pos}')
        payload=data[pos+2:end];cur=0;texts=[]
        for _ in range(fields):
            if cur>=len(payload):raise ValueError(f'{source}: missing text prefix')
            n=payload[cur];cur+=1
            if cur+n>len(payload):raise ValueError(f'{source}: text crosses record')
            texts.append(payload[cur:cur+n].decode('cp949'));cur+=n
        records.append((texts,payload[cur:]));pos=end
    return records


def build(records,source='<records>'):
    result=bytearray()
    for texts,tail in records:
        body=bytearray()
        for text in texts:
            raw=text.encode('cp949')
            if len(raw)>255 or b'\0' in raw:raise ValueError(f'{source}: invalid string size or NUL')
            body.append(len(raw));body.extend(raw)
        body.extend(tail)
        if len(body)>65535:raise ValueError(f'{source}: oversized record')
        result.extend(len(body).to_bytes(2,'little'));result.extend(body)
    return bytes(result)


def compile_catalog(original: Path,catalog: Path,output: Path):
    cat=json.loads(catalog.read_text(encoding='utf-8'))
    if cat['format']!='hl3-prefixed-record-text-v1':raise ValueError('Unknown record catalog')
    files={}
    for e in cat['entries']:
        rel=e['file'];path=Path(rel)
        if path.is_absolute() or '..' in path.parts:raise ValueError('Unsafe record path')
        key=(int(e['record']),int(e['field']))
        byslot=files.setdefault(rel,{})
        if key in byslot:raise ValueError(f'Duplicate record field: {rel} {key}')
        byslot[key]=e
    count=0
    for rel,entries in files.items():
        fields=cat['field_counts'][rel];data=(original/rel).read_bytes()
        records=parse(data,fields,rel)
        if build(records,rel)!=data:raise ValueError(f'{rel}: source did not roundtrip')
        expected={(i,j) for i in range(len(records)) for j in range(fields)}
        if set(entries)!=expected:raise ValueError(f'{rel}: incomplete record catalog')
        rebuilt=[]
        for i,(texts,tail) in enumerate(records):
            values=[]
            for j,text in enumerate(texts):
                e=entries[(i,j)]
                if e['source']!=text:raise ValueError(f'{rel}#{i}.{j}: changed source')
                value=e['translation'] if e.get('translation') is not None else text
                value.encode('ascii')
                values.append(value);count+=int(value!=text)
            rebuilt.append((values,tail))
        target=output/rel;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(build(rebuilt,rel))
    return count
