#!/usr/bin/env python3
"""Curate narrow UI copy and localize confirmed text inside binary.mod."""
from __future__ import annotations

import json
import re
from pathlib import Path

from hl3_item_names import REVIEW_NAMES
from hl3_locations import normalize_entry
from hl3_dialogue_reviews import REVIEWS
from hl3_markup import latin_copy,sequence

OPTIONS = {
    0x5B44C: ("@:메인메뉴".encode("cp949"), b"@:MENU"),
    0x5B460: ("효 과 음".encode("cp949"), b"SFX"),
    0x5B46C: ("배 경 음".encode("cp949"), b"BGM"),
    0x5B478: ("게임속도".encode("cp949"), b"GAME SPD"),
    0x5B484: ("진    동".encode("cp949"), b"VIB"),
    0x5B490: ("대화속도".encode("cp949"), b"DLG SPD"),
    0x5B49C: ("시선이동".encode("cp949"), b"CAM MOVE"),
    0x5B4A8: ("크리티컬".encode("cp949"), b"CRIT"),
    0x5B4B8: ("@:선택".encode("cp949"), b"@:SEL"),
}

ROOT = Path(__file__).resolve().parents[1]
CATALOGS = ROOT / 'translations'

UI = {
    'res/dat/InGame_txt#0':'MENU',
    'res/dat/InGame_txt#1':'STATUS',
    'res/dat/InGame_txt#2':'ITEMS',
    'res/dat/InGame_txt#3':'GEAR',
    'res/dat/InGame_txt#4':'SKILLS',
    'res/dat/InGame_txt#5':'QUESTS',
    'res/dat/InGame_txt#6':'SYSTEM',
    'res/dat/InGame_txt#17':'NM',
    'res/dat/InGame_txt#18':'EFC',
    'res/dat/InGame_txt#19':'OTHR',
    'res/dat/InGame_txt#145':'OTHR',
    'res/dat/InGame_txt#21':'SWRD',
    'res/dat/InGame_txt#64':'HELM',
    'res/dat/InGame_txt#65':'ARMR',
    'res/dat/InGame_txt#69':'SWRD',
    'res/dat/InGame_txt#72':'CANNON',
    'res/dat/InGame_txt#98':'SHLD PIERCE +',
    'res/dat/InGame_txt#120':'SWRD / SPEAR',
    'res/dat/InGame_txt#121':'GUN / RIFLE',
    'res/dat/InGame_txt#143':'ARMR',
    'res/menu/countrybody_txt#0':
        'LONG AGO, SOLTIA;LEFT EREBUS FOR;THE SKY. WHEN;THE GUARDIAN;VANISHED, SOLTIA;BEGAN TO FALL.;ITS PEOPLE FLED;TO EARTH BELOW.',
    'res/menu/countrybody_txt#1':
        'EREBUS FOUGHT;FOR CENTURIES;OVER ADVANCED;FIREARMS. UNITED;UNDER ASKRA, ITS;PEOPLE NOW SEEK;LASTING PEACE.',
    'res/menu/chatacterbody_txt#0':
        'WINDLIKE BERSERKERS.;TWIN BLADES AND GREATSWORDS;SWEEP THROUGH ENEMY RANKS.',
    'res/menu/chatacterbody_txt#1':
        'SOLTIAS REAPERS.;THEY WIELD GUARDIAN POWER;AND A MIGHTY SWORD,;CRUSHING ALL IN THEIR PATH.',
    'res/menu/chatacterbody_txt#2':
        'SHADOW ASSASSINS, HEIRS TO;THE CRUSADERS LEGACY.;NONE CAN STOP THEIR WILL.',
    'res/menu/chatacterbody_txt#3':
        'HOLY KNIGHTS WHO GUARDED;THE REFINERS. THEY DEFEND;ALLIES ON THE FRONT LINE.',
    'res/menu/chatacterbody_txt#4':
        'THE LAST GUARDIANS.;MASTERS OF HOLY CORE POWER;AND A MYSTERIOUS FORCE.',
    'res/menu/chatacterbody_txt#5':
        'ASKRAS BRAVE KNIGHTS.;THEY CHARGE WITH SHIELDS;AND SWING GREAT SWORDS.',
    'res/menu/chatacterbody_txt#6':
        'ASKRAS ULTIMATE DESTROYERS.;TWIN GUNS, A MASSIVE SWORD;READY FOR ANY SITUATION.',
    'res/menu/chatacterbody_txt#7':
        'HEROES OF THE DARK WORLD.;QUICK, PRECISE MOVEMENTS;STRIKE DOWN THEIR TARGETS.',
    'res/menu/chatacterbody_txt#8':
        'HOLY KNIGHTS OF REGALIS.;THE ORDER EXCELS IN BOTH;ATTACK AND DEFENSE.',
    'res/menu/chatacterbody_txt#9':
        'WAR-BORN TRAGIC GENIUS,;SKILLED WITH EVERY FIREARM.',
}

# Fixed byte slots. Preserve all printf operands and engine color/key markup.
MODULE = {
    0x5A380:'<INFO>',
    0x5A38C:'PLAYING THIS GAME',
    0x5A3A4:'HAS NO EXTRA FEE.',
    0x5A3BC:'PREMIUM ITEMS AND',
    0x5A3D4:'CHARACTER RESTORES',
    0x5A3F0:'MAY INCUR CALL AND',
    0x5A408:'DATA CHARGES.',
    0x5A424:'PRESS ANY KEY',
    0x5A438:'DETAILS',0x5A442:'DROP',0x5A44C:'STORE',
    0x5A546:'DETAILS',0x5A550:'DROP',0x5A55A:'TAKE',0x5A564:'ORB FUSE',
    0x5A654:'DETAILS',0x5A65E:'BUY',
    0x5A83A:'DF',0x5A83F:'AT',0x5A844:'RES',
    0x5A9BE:'NO',0x5A9C5:'Y',
    0x5AC00:'GETTING ITEM DATA...',
    0x5AC1C:'PAYMENT ERROR. PURCHASE CANCELED.',
    0x5AC4C:'Y',0x5AC50:'NO',
    0x5AC7C:'GETTING SLOT DATA...',0x5AC94:'REQUESTING SMS...',
    0x5ACB4:'GETTING NOTICES...',0x5ACDC:'ITEM DELETED.',
    0x5ACF8:'UNEQUIP THE ITEM BEFORE STORING.',
    0x5AD1C:'CANNOT STORE THIS ITEM.',
    0x5AD3C:'CANNOT STORE HEROIC OR HIGHER ITEMS.',
    0x5AD74:'CANNOT STORE THIS MATERIAL.',
    0x5AD98:'CANNOT STORE RECIPE ITEMS.',
    0x5ADC0:'CANNOT STORE QUEST ITEMS.',
    0x5ADE4:'STORING ITEM...',0x5ADFC:'DISCARDING ITEM...',
    0x5AE14:'CANNOT WITHDRAW THIS ITEM.',0x5AE34:'WITHDRAWING ITEM...',
    0x5AE4C:'WITHDRAWN ITEMS CANNOT RETURN TO ONLINE STORAGE. CONTINUE?',
    0x5AE94:'CHOOSE GEAR FOR ORB FUSION.',
    0x5AEB8:' EXTRA DATA FEE (CALL FEES SEPARATE).;BUY THIS ITEM?',
    0x5AF04:'REAL CASH',0x5AF10:'LOCAL STORAGE IS FULL.',
    0x5AF2C:'CANNOT BUY ANY MORE.',0x5AF48:'FUSE AN ORB WITH THIS GEAR?',
    0x5AF6C:'GETTING PREMIUM ITEM DATA...',
    0x5AFA0:'LV%d %s',0x5AFBC:'DF',0x5AFC0:'AT',
    0x5AFC4:'REFINE %d/10',0x5AFD4:'STUN RES +%d',
    0x5AFE4:'HONOR %s',0x5AFF4:'WEAP %s',0x5B004:'POWER %d',
    # Shared suffixes at +16 and +12 are separately referenced format strings.
    0x5B014:'REFINE %d/10',0x5B024:'LV        %d %s / %s%d',
    0x5B03C:'SOCKET',0x5B048:'STUN RES %d',
    0x5B088:'NETWORK CALLS;MAY INCUR FEES.;CONNECT?',
    0x5B0C0:'EMPTY SLOT.',0x5B0D0:'SAVING SLOT TO SERVER...',
    0x5B118:'PERMANENTLY DELETE;THIS SLOT?',
    0x5B140:'CANNOT CONNECT. TRY AGAIN LATER.',
    0x5B170:'SERVER CONNECTION ENDED.',0x5B190:'@OK:}OK',
    0x5B19C:'WAITING FOR SERVER',0x5B1B4:'SET THE AMOUNT.',
    0x5B1C8:'DELETED.',0x5B1D8:'WITHDRAWING GOLD...',
    0x5B1EC:'BUYING PREMIUM ITEM.;QUITTING NOW MAY LOSE THE ITEM.',
    0x5B22C:'FUSING ORB...',0x5B240:'QUIT GAME?',0x5B264:'@:OK',
    0x5B2A0:'RITS',0x5B2A8:'KEI',0x5B2B0:'CONTINUE?',
    0x5B2D8:'MAIN',0x5B2E0:'SUB',0x5B310:'EMPTY',
    0x5B318:'}:NEW CHAR',0x5B328:'@#:}LOAD',
    0x5B350:'@:CONTINUE',0x5B35C:'@#:}RESET',0x5B38C:'DATA FEES',
    0x5B3A0:'NETWORK USE MAY INCUR CARRIER DATA CHARGES. THIS GAME ADDS NO FEE PER 512-BYTE PACKET. INTERNATIONAL ROAMING RATES MAY APPLY.',
    0x5B4D0:'LV%d %s /   %s%d',0x5B510:'GETTING GOLD...',
    0x5B524:'ITEM STORED ONLINE.',0x5B54C:'ITEM WITHDRAWN. UPDATING...',
    0x5B580:'ITEM DELETED. UPDATING...',0x5B5B0:'GOLD WITHDRAWN.',
    0x5B5D0:' PURCHASED.',0x5B5E8:'SERVER DISCONNECTED.',
    0x5B788:'DISCONNECTED AFTER 5 MINUTES OF INACTIVITY.',
    0x5B7C4:'REGISTERING FULL GAME...',
    0x5BCB8:'DF',0x5BCBD:'AT',0x5BCC2:'RES',
    0x5BEE8:'LV%d %s/%s%d',0x5BF28:'%s;LV%d %s/%s%d',
    0x5BF50:'@OK:}REFINE',0x5BF60:'REFINE',0x5BF6C:'EA',0x5BF70:'STONE',
    0x5BF78:'CANNOT REFINE ANY FURTHER.',0x5BF94:'CANNOT REFINE ACCESSORIES.',
    0x5BFB4:'NO REFINEMENT STONES.',0x5BFCC:'NOT ENOUGH REFINEMENT STONES.',
    0x5BFF0:'NOT ENOUGH GOLD.',0x5C008:'THIS GEAR IS EQUIPPED.;CONTINUE?',
    0x5C030:'REFINING...',0x5C044:'@OK:}CRAFT',0x5C054:'CRAFT',
    0x5C078:'@ IS MISSING.',0x5C08C:'CRAFTING...',0x5C0A0:'STORAGE IS FULL.',
    0x5C0B8:'SPECIAL',0x5C0C4:'NOT ENOUGH GOLD.',0x5C0DC:'@OK:}PICK',
    0x5C0F4:'CRAFT SUCCESS.;;',0x5C110:'CRAFT FAILED.',
    0x5C128:'REFINE SUCCESS.;;',0x5C144:'REFINE FAILED. GEAR DESTROYED.',
    0x5C168:'REFINE FAILED. GEAR RESET.',0x5C18C:'REFINE FAILED.',
    0x5CBE8:'DF',0x5CBED:'AT',0x5CBF2:'RES',
    0x5CC62:'AT',0x5CC67:'DF',0x5CC6C:'RES',
    0x5CCC8:'MAIN',0x5CCD2:'SUB',0x5CEC0:'CLR:BACK',
    0x5CEE4:'SP USE:%d',0x5CF18:'REFINE',
    0x5D468:'GAMEOVER',0x5D600:'INVENTORY IS FULL.',
}

EVENT_FIXES = {
    'res/event/e0001_scn#146':'{TO SIEN} QUEST IN',
    'res/event/e0003_scn#149':"'[LEA]@ THE CANYON IS TOXIC. HAVE {THE GARRISON SMITH@ CRAFT {HOLY WATER@ BEFORE YOU GO.",
    'res/event/e0005_scn#207':'$[ROBIN]@ PROVE IT! BRING {30 RAT SKINS@ FROM THE {SHRINE OF LIGHT@.',
    'res/event/e0005_scn#209':"$[ROBIN]@ {SHRINE OF LIGHT@. {30 RAT SKINS@. DON'T OVERDO IT.",
    'res/event/e0105_scn#276':"'[MELPETO]@ FIND ME {SOUTH OF TOREZ@ AT THE {BLACK FACTORY@. WE HAVE MUCH TO DISCUSS.",
    'res/event/e0106_scn#142':"$[MINER]@ KILL {30 SPECTERS@ IN THE MINE FOR {15000 GOLD@. HELP TOREZ RECOVER!",
    'res/event/e0106_scn#145':'$[MINER]@ {MINING SITE@. {30 SPECTERS@. PLEASE.',
    'res/event/e0114_scn#247':'$[GUIDE]@ HUNT {PLANT MONSTERS@ IN THE {LOWEN AREA@.',
    'res/event/e0114_scn#276':'$[GUIDE]@ NO MORE JOBS. FOCUS ON {CRESTS HELD BY UNKNOWN GUILD MEMBERS@.',
    'res/event/e0152_scn#57':'DELIVERED {ELGIS CREST}!',
    'res/event/e0152_scn#79':'$[ELGIS MEMBER]@ REVIVE ELGIS! WE MUST RALLY UNDER {THE ELGIS CREST@!',
    'res/event/e0153_scn#60':'$[CIVIL SERVANT]@ JUST DEFEAT {15 BANDITS NEAR TOWN@.',
    'res/event/e0154_scn#43':'$[ADVENTURER]@ THE VILLAGERS WANT {BLOODY DEMONS KILLED@ IN THE SOUTHERN CAVE. A TOUGH JOB.',
    'res/event/e0218_scn#109':"'[SIEN]@ UM... TAKE ME {TO THE VILLAGE@. OKAY?",
    'res/event/e0233_scn#174':'{TO LIGHTHOUSE} QUEST IN!',
}

EVENT_FIXES.update({
    'res/event/e0003_scn#109':"'[TENOR]@ 1 YR... NO, 2.",
    'res/event/e0005_scn#125':'$[AMY]@ ANYONE CAN REST HERE FOR A 300G UPKEEP FEE.',
    'res/event/e0005_scn#153':'|[KEI]@ ...THE REST AREA FEE IS 300G, RIGHT?',
    'res/event/e0005_scn#183':'{5 POTIONS;1000G} GET!',
    'res/event/e0005_scn#195':"$[ROBIN]@ SELL THEM TO ME... I'LL PAY 500G EACH.",
    'res/event/e0036_scn#182':'}RECHARGE WITH;{3 BLUE SOLUTIONS;3 CLEAR SOLUTIONS;1 WIND FLUTE}.',
    'res/event/e0037_scn#74':"|[RITS]@ NOISE... ON FLOOR 2?",
    'res/event/e0041_scn#67':'$[MAID]@ NO, 1500...',
    'res/event/e0041_scn#69':'$[MAID]@ YES... 2500 GOLD...',
    'res/event/e0062_scn#87':"|[KEI]@ GOT IT! TOREZ: ALBERT SHU HEIM, AGE 19!",
    'res/event/e0087_scn#92':"IT'S BEEN 4 YEARS.",
    'res/event/e0114_scn#198':'{10 POTIONS,300G} GET!',
    'res/event/e0114_scn#207':'{GOLEM CREST,300G} GET!',
    'res/event/e0116_scn#120':'|[RITS]@ THAT AMULET IS WORTH 5000G...',
    'res/event/e0117_scn#37':'{PHANTOM CHARM,5000G} GET!',
    'res/event/e0117_scn#42':'$[HISTORIAN]@ YOU LOOK BRAVE. TRY IT? THE PRIZE IS 5000G.',
    'res/event/e0118_scn#128':"|[RITS]@ IT'S BEEN NEARLY 10 YEARS. NO WONDER I FORGOT.",
    'res/event/e0127_scn#48':'{SERAPHIM HAND,10000G} GET!',
    'res/event/e0150_scn#103':'$[ROBE]@ CARDS ARE 1-USE. CRAFT ANOTHER BEFORE RE-ENTRY.',
    'res/event/e0150_scn#159':'$[ROBE]@ FACTORY CARDS ARE 1-USE. CRAFT A NEW ONE FOR EACH ENTRY.',
    'res/event/e0150_scn#166':'$[ROBE]@ THE CARD IS {1-USE@. COME CRAFT A NEW ONE BEFORE RE-ENTRY.',
    'res/event/e0151_scn#165':'{SOUL STONE,20000G} GET!',
    'res/event/e0154_scn#37':"$[ADVENTURER]@ LATER THAN I EXPECTED! COUNTING MY KILLS, WE DEFEATED OVER 60 BLOODY DEMONS.",
    'res/event/e0171_scn#56':";;NOW I WILL HELP THE MAN;I DESPISED FOR 10 YEARS.",
    'res/event/e0171_scn#58':';;;...10 YEARS',
    'res/event/e0180_scn#350':'$[ELGIS MEMBER 1]@ ABOUT 40 HAVE REGROUPED...',
    'res/event/e0189_scn#119':'{807-04-12;@SOLTIA, ISLAND IN THE WESTERN SEA, ROSE INTO THE SKY!',
    'res/event/e0189_scn#122':"{807-07-27;@SUMMONS CONTINUE. THE COUNCIL WON'T END GUARDIAN STUDIES.",
    'res/event/e0189_scn#125':'{807-11-13;@THE EXPERIMENTS CONTINUE, JUST AS ON THE GROUND.',
    'res/event/e0189_scn#129':'{808-02-22;@THE COUNCIL PERFORMED REFINEMENT ON A LIVING GIRL.',
    'res/event/e0189_scn#134':"{808-07-03;@WE CANNOT CONTROL THE BEASTS' RAMPAGE.",
    'res/event/e0189_scn#138':'{810-07-04@;NATURAL ENERGY WAS A BLESSING TO HUMANKIND AT FIRST.',
    'res/event/e0189_scn#142':'{810-09-21@;2 YRS SINCE WE RETURNED TO EARTH...',
    'res/event/e0189_scn#145':"{811-03-07@;WE CHOSE SOLTIA'S LANDING SITE.",
    'res/event/e0189_scn#148':'{811-03-09@;THE NEW CORE DESIGN IS THEORETICALLY POSSIBLE.',
    'res/event/e0189_scn#151':'{811-04-30@;THE NEW CORE DESIGN IS COMPLETE.',
    'res/event/e0189_scn#155':"{811-06-11@;NYX'S PENDANT SIGNAL VANISHED.",
    'res/event/e0197_scn#93':'$[OLD MAN]@ THE ARK OPENS WITH ITS OWN LIGHT. {20 LIGHTNING POWDERS@ CAN FORCE IT OPEN.',
    'res/event/e0208_scn#213':"'[KENNET]@ OUR 4TH DUEL. 1 WIN, 1 DRAW, 1 LOSS?",
    'res/event/e0243_scn#296':'MELP. LV44',
    'res/event/e0243_scn#302':'SIEGE LV44',
    'res/event/e0243_scn#303':'SIEGE LV35',
    'res/event/e0243_scn#304':'HOLY G. 46',
    'res/event/e0238_scn#91':"...I'M CONFUSED..",
    'res/event/e0189_scn#137':"...I TRIED TO SAVE HER...;;I BROKE MY PROMISE.",
    'res/event/e0240_scn#23':'9 YRS AGO, UNIFICATION WAR;MELHAR',
    'res/event/e0004_scn#153':'{CHAPTER 1;THE BEAST TAMER@',
    'res/event/e0004_scn#165':'{CHAPTER 7;A MIRACLE OF PEACE@',
    'res/event/e0035_scn#263':'{CHAPTER 6;SKY DISASTER OF THE PAST',
    'res/event/e0035_scn#273':'{CHAPTER 4;SOLTIA STRIKES@',
    'res/event/e0035_scn#307':'{CHAPTER 6;MAN-MADE SKY DISASTER',
    'res/event/e0036_scn#300':'{CHAPTER 9;WHAT I MUST STOP@',
    'res/event/e0094_scn#22':'{CHAPTER 2;BEHIND LINES@',
    'res/event/e0098_scn#92':'{CHAPTER 2;YOUNG GUEST@',
    'res/event/e0106_scn#187':'{CHAPTER 8;CROSSED@',
    'res/event/e0114_scn#146':'{CHAPTER 1;WAR LAND@',
    'res/event/e0125_scn#60':'{CHAPTER 3;GUARDIAN ECHO@',
    'res/event/e0156_scn#51':'{CHAPTER 5;WILL FOR PEACE@',
    'res/event/e0156_scn#57':"{CHAPTER 5;THE WAR'S BANQUET@",
    'res/event/e0190_scn#55':"{FINAL CHAPTER;GUARDIAN;A LONG LIFE'S END@",
    'res/event/e0191_scn#34':'{FINAL CHAPTER;FROM SACRIF.@',
    'res/event/e0196_scn#93':'{CHAPTER 7;IF ONE IS GUILTY@',
    'res/event/e0235_scn#76':'{CHAPTER 4;AN AGE OF TURMOIL@',
})

for key,value in REVIEWS.items():
    file,segment=key.split(':')
    EVENT_FIXES[f'res/event/{file}_scn#{segment}']=value

ITEM_WORDS = {
    'REINFORCED':'REINF', 'GREATSWORD':'G.SWRD','GREAT SWORD':'G.SWRD',
    'LEATHER':'LTHR','GAUNTLETS':'GAUNT','SHOULDER':'SHLDR',
    'EARRINGS':'EARRING','TRANSCENDENCE':'TRANSCEND','ACCESSORY':'ACC',
    'ARMOR':'ARMR','SWORD':'SWRD','SHIELD':'SHLD','HELMET':'HELM',
}


def save(path: Path,payload):
    path.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def compact_item(text: str) -> str:
    for word,replacement in ITEM_WORDS.items():
        text=re.sub(r'\b'+re.escape(word)+r'\b',replacement,text)
    return text


def pack_review(text: str,capacity: int) -> str:
    """Fit punctuation and spacing only; never remove clauses or tail words."""
    if len(text.encode('cp949'))<=capacity:return text
    text=re.sub(r'([@{}|$]) +',r'\1',text)
    if len(text.encode('cp949'))<=capacity:return text
    text=re.sub(r'\.{3,}','..',text)
    if len(text.encode('cp949'))<=capacity:return text
    text=re.sub(r'\bAND\b','&',text)
    if len(text.encode('cp949'))<=capacity:return text
    return text.rstrip('.')


def main():
    p=CATALOGS/'catalog.json';catalog=json.loads(p.read_text(encoding='utf-8'))
    byid={e['id']:e for e in catalog['entries']}
    for key,value in UI.items():byid[key]['translation']=value
    for e in catalog['entries']:
        if e.get('translation'):e['translation']=latin_copy(e['translation'],e['source'])
    save(p,catalog)

    p=CATALOGS/'item-catalog.json';catalog=json.loads(p.read_text(encoding='utf-8'))
    for e in catalog['entries']:
        value=REVIEW_NAMES.get(e['id'],e.get('translation') or '')
        value=value.replace('HOLLY','HOLY').replace('TORRES','TOREZ')
        e['translation']=compact_item(latin_copy(value.strip().upper(),e['source']))
    save(p,catalog)

    p=CATALOGS/'event-catalog.json';catalog=json.loads(p.read_text(encoding='utf-8'))
    byid={e['id']:e for e in catalog['entries']}
    for key,value in EVENT_FIXES.items():
        e=byid[key]
        value=pack_review(value,len(e['source'].encode('cp949')))
        if len(value.encode('cp949'))>len(e['source'].encode('cp949')):
            raise ValueError(f'Curated event overflows: {key}')
        if ''.join(c for c in value if c in '{}@$|') != ''.join(c for c in e['source'] if c in '{}@$|'):
            raise ValueError(f'Curated event changes markup order: {key}')
        e['translation']=value
    locations=sum(normalize_entry(e) for e in catalog['entries'])
    for e in catalog['entries']:
        e['translation']=latin_copy(e['translation'],e['source'])
        if sequence(e['translation'])!=sequence(e['source']):
            raise ValueError(f"Engine control sequence changed: {e['id']}")
    save(p,catalog)

    module=(ROOT/'work/original/binary.mod').read_bytes();rows=[]
    values=dict(MODULE)
    for offset,(_,translated) in OPTIONS.items():values[offset]=translated.decode('ascii')
    for offset,value in sorted(values.items()):
        end=module.index(0,offset);source=module[offset:end].decode('cp949')
        if len(value.encode('ascii'))>end-offset:
            raise ValueError(f'Module text overflows 0x{offset:X}: {value}')
        fmt=r'%(?:[-+ 0#]*\d*(?:\.\d+)?[a-zA-Z%])'
        if re.findall(fmt,source)!=re.findall(fmt,value):
            raise ValueError(f'Format operands changed at 0x{offset:X}')
        if ''.join(c for c in source if c in '{}@$|') != ''.join(c for c in value if c in '{}@$|'):
            raise ValueError(f'Module markup changed at 0x{offset:X}')
        rows.append({'id':f'binary.mod@{offset:06x}','offset':offset,'source':source,'translation':value})
    save(CATALOGS/'module-ui.json',{'format':'hl3-module-fixed-text-v1','entries':rows})
    print(f'Curated {len(UI)} UI slots, 628 item names, {len(EVENT_FIXES)} event lines, {locations} locations, {len(rows)} module labels.')


if __name__=='__main__':main()
