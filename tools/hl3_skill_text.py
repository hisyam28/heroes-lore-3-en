#!/usr/bin/env python3
"""Localize all skill records while preserving every gameplay metadata byte.

Record: u16 payload size, u8 name size/name, u8 kind, u8 description size/
description, then exactly 30 bytes of gameplay data. Text slot lengths and all
record boundaries remain unchanged. Do not use guessed description offsets.
"""
from __future__ import annotations
import json
import re
import zipfile
from io import BytesIO
from pathlib import Path
from hl3_assets import find_game_jar
from hl3_item_descriptions import wrap

ROOT=Path(__file__).resolve().parents[1]
NAMES={
    '광아':'FANG','파동':'WAVE','격광':'FLAR','회복':'HEAL','초월':'TRAN',
    '광휘':'GLOW','보호':'PROT','신성':'HOLY','창술':'LANC','섬광':'DASH',
    '자격':'THRS','압도':'SLOW','유도':'TAUN','장벽':'WALL','태산':'MASS',
    '의지':'WILL','정신':'MIND','검술':'SWRD','선풍':'SPIN','양단':'CLEA',
    '질풍':'GALE','결의':'WILL','혼신':'ZEAL','전력':'FULL','근성':'GRIT',
    '집중':'FOCS','단도':'DAGG','참혼':'REAP','암영':'SHDW','난무':'FLRY',
    '육감':'SENS','은신':'HIDE','간파':'READ','살의':'AGGR','저력':'GRIT',
    '사격':'SHOT','연사':'RAPD','난사':'SPRY','곡예':'DODG','저격':'SNIP',
    '장탄':'LOAD','조준':'AIM!','냉정':'CALM','속공':'RUSH','격발':'FIRE',
    '직격':'HIT!','연쇄':'LINK','위협':'FEAR','지축':'QAKE','일심':'FOCS',
    '강공':'ATK!','투혼':'SOUL','인내':'GRIT','영탄':'DARK','암흑':'DARK',
    '업화':'HELL','나락':'ABYS','망각':'OBLV','전율':'SHVR','적의':'FURY','흡혼':'LECH',
}
DESCRIPTIONS={
    's4_dat':[
        'USE A ONE-HANDED SPEAR.','CHARGE FAST; CAN BE CHAINED.',
        'THRUST FORCE FROM THE SPEAR TIP.','INTIMIDATE FOES TO SLOW ATKS.',
        'DRAW ENEMY ATKS TO YOURSELF.','FOCUS TO BOOST DEF.',
        'RAISE BASE DEF.','RAISE MAX HP AND SURVIVAL.','RAISE STUN RESIST.',
    ],
    's5_dat':[
        'WIELD A TWO-HANDED GREATSWORD.','SWEEP THE GREAT SWORD AT FOES.',
        'DELIVER A LETHAL FRONTAL SLASH.','ADVANCE WITH REPEATED SLASHES.',
        'RAISE ACC WITH RESOLVE.','UNLEASH POTENTIAL TO BOOST SWORD ATK.',
        'MAXIMIZE PHYSICAL ATK.','RAISE HP AND DEF FOR MELEE.','IMPROVE AIM AND ACC.',
    ],
    's6_dat':[
        'MASTER QUICK DAGGER TECHNIQUES.','STRIKE A VITAL POINT TO STUN.',
        'DASH THROUGH FOES TO STRIKE THEM.','CHAIN ALL TECHNIQUES ON ONE FOE.',
        'SENSE ATKS TO BOOST EVA.','VANISH FROM SIGHT FOR A WHILE.',
        'READ FOES TO RAISE EVA.','RAISE AGGRO AND MELEE POWER.','BUILD ENDURANCE UNDER ATK.',
    ],
    's7_dat':[
        'USE A GUN TO HIT ONE DISTANT FOE.','FIRE REPEATEDLY AT ONE FOE.',
        'FIRE WILDLY AT MULTIPLE FOES.','FIRE WHILE RETREATING.',
        'AIM PRECISELY FOR A POWERFUL SHOT.','LARGE ROUNDS BOOST ATK FOR A WHILE.',
        'AIM QUICKLY TO RAISE ATK AND ACC.','VITAL SHOTS RAISE STUN CHANCE.','USE SKILLS FASTER.',
    ],
    's8_dat':[
        'USE A HEAVY GUN; NO RAPID FIRE.','PRECISE SHOTS CAUSE BLEEDING.',
        'USE RECOIL TO STRIKE NEARBY FOES.','INTIMIDATE FOES TO CUT STUN RES.',
        'BRACE GUN. OTHER ACTIONS CANCEL THIS.','FOCUS TO BOOST ALL ATK.',
        'MAXIMIZE ATK FOR ALL GUNS.','RAISE SHIELD-PIERCE CHANCE.','RAISE DEF VS GUNS AND MAGIC.',
    ],
    's9_dat':[
        'THROW A SHADOW SHELL.','BURST THE DARKNESS INSIDE A FOE.',
        'HELL LIGHTNING HITS A WIDE AREA.','SUMMON A LINGERING REALM OF HELL.',
        'CUT NEARBY FOE ATK SHARPLY.','SHARPLY REDUCE FOE DEF AND EVA.',
        'MAXIMIZE MAGIC ATK.','RAISE SHIELD-PIERCE CHANCE.','TURN DARKNESS FROM ATKS INTO HP.',
    ],
    's10_dat':[
        'CREATE AND FIRE A LIGHT FANG.','FOCUS LIGHT TO STRIKE A FOE.',
        'BURST LIGHT TO HIT AND LOWER ACC.','HEAL HP AND CURE AILMENTS.',
        'RAISE MAX HP AND HEALING.','IMBUE WEAPONS WITH LIGHT TO RAISE ATK.',
        'RAISE BASE DEF WITH A LIGHT BARRIER.','RAISE DEF AND RES VS SPECIAL ATKS.','BOOST ALL ATTACK DAMAGE.',
    ],
}


def parse(data: bytes,source='<skills>'):
    rows=[];pos=0
    while pos<len(data):
        if pos+2>len(data):raise ValueError(f'{source}: truncated record size')
        n=int.from_bytes(data[pos:pos+2],'little');end=pos+2+n
        if n<34 or end>len(data):raise ValueError(f'{source}: invalid record at {pos}')
        cur=pos+2;ns=data[cur];name_pos=cur+1;cur+=1+ns
        if cur+2>end:raise ValueError(f'{source}: bad name field')
        kind=data[cur];cur+=1;ds=data[cur];desc_pos=cur+1;cur+=1+ds
        if kind>3 or end-cur!=30:raise ValueError(f'{source}: unexpected skill metadata layout at {pos}')
        name=data[name_pos:name_pos+ns].decode('cp949').rstrip('\0')
        description=data[desc_pos:desc_pos+ds].decode('cp949').rstrip('\0')
        rows.append({'offset':pos,'size':n,'name_offset':name_pos,'name_size':ns,'name':name,
                     'kind':kind,'description_offset':desc_pos,'description_size':ds,
                     'description':description,'tail_offset':cur,'tail':data[cur:end]})
        pos=end
    return rows


def compile_skills(original: Path,output: Path):
    entries=[];audit=[];count=0
    with zipfile.ZipFile(ROOT/'work/heroes-lore-3-final.apk') as apk:
        legacy_jar,_=find_game_jar(apk)
    with zipfile.ZipFile(BytesIO(legacy_jar)) as jar:
        legacy_files={name:jar.read('res/skill/'+name) for name in DESCRIPTIONS}
    for filename,copy in DESCRIPTIONS.items():
        source=(original/'res/skill'/filename).read_bytes();result=bytearray(source)
        rows=parse(source,filename);assert len(rows)==15
        descriptions=iter(copy);legacy=legacy_files[filename]
        assert len(legacy)==len(source)
        allowed=set();legacy_bad=0
        for i,row in enumerate(rows):
            base=re.sub(r'[2-9]$','',row['name']);suffix=row['name'][len(base):]
            translated_name=(NAMES[base] if base in NAMES else base if base.isascii() else NAMES[base])+suffix
            translated_description=wrap(next(descriptions)) if row['description'] else ''
            for field,value in [('name',translated_name),('description',translated_description)]:
                pos=row[field+'_offset'];size=row[field+'_size'];raw=value.encode('ascii')
                if len(raw)>size:raise ValueError(f'{filename}#{i} {field}: exceeds {size} bytes: {value}')
                result[pos:pos+size]=raw+b'\0'*(size-len(raw));allowed.update(range(pos,pos+size))
                count+=int(value!=row[field])
                entries.append({'id':f'res/skill/{filename}#{i}.{field}','file':f'res/skill/{filename}',
                                'record':i,'field':field,'source':row[field],'translation':value,'byte_capacity':size})
        assert next(descriptions,None) is None
        assert len(result)==len(source)
        for pos,(a,b) in enumerate(zip(source,result)):
            if pos not in allowed:assert a==b,(filename,pos)
        legacy_bad=sum(a!=b for p,(a,b) in enumerate(zip(source,legacy)) if p not in allowed)
        target=output/'res/skill'/filename;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(result)
        rebuilt=parse(bytes(result),filename)
        for a,b in zip(rows,rebuilt):
            for key in ['offset','size','kind','tail_offset','tail','name_size','description_size']:
                assert a[key]==b[key],(filename,key)
        audit.append({'file':filename,'records':len(rows),'metadata_bytes_preserved':15*30,
                      'legacy_changes_outside_confirmed_text_slots':legacy_bad})
    (ROOT/'translations/skill-text.json').write_text(json.dumps({'format':'hl3-skill-fixed-text-v1','entries':entries},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'reports/skill-record-validation.json').write_text(json.dumps({'files':audit,'translated_nonempty_fields':count,'original_metadata_preserved':True},indent=2)+'\n',encoding='utf-8')
    return count


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=ROOT/'work/optimized')
    print('Translated skill fields:',compile_skills(ROOT/'work/original',parser.parse_args().output))
