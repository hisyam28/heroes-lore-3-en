"""Confirmed location-name suffixes; preceding script bytes are not text."""
from __future__ import annotations
import re

NAMES = {
    '네오 솔티아':'NEO SOLTIA','네오솔티아':'NEO SOLTIA',
    '대회의실':'MEET RM','레아의 집':'LEA HOME','쉼터':'REST',
    '훈련대기실':'TRAIN RM','네메시스 숲':'NEMESIS WDS',
    '작은 동굴':'CAVE','오래된 지하도':'OLD TUNNEL',
    '황혼의 땅':'DUSK LAND','홀리코어의 제단':'HOLY CORE ALTAR',
    '빛의 신당':'LIGHT SHR','광산도시 토레즈':'TOREZ',
    '토레즈 관청':'TOREZ HALL','일레느의 집':'ILENE HOME',
    '토레즈 여관':'TOREZ INN','졸부의 집':'RICH HOME','민가':'HOME',
    '토레즈 지하 감옥':'TOREZ PRISON','토레즈 지하':'TOREZ B1',
    '토레즈 광산':'TOREZ MINE','검은 공장':'BLK FCT',
    '비밀의 작업실':'SECRET LAB','채굴장':'MINE',
    '솔티안 주둔지':'SOLT CAMP','네메시스 고원':'NEMESIS HT',
    '네메시스 협곡':'NEMESIS CYN','비밀의 회랑':'SECRET HALL',
    '아스크란 주둔지':'ASKRA CAMP','폐쇄된 공장':'CLOSED FCT',
    '사막마을 엔자크':'ENZAK','용병 길드':'MERC HQ','엔자크 여관':'ENZAK INN',
    '고고학자의 집':'ARCHEO HOME','엔자크 사막':'ENZAK DUNE',
    '리파이너의 유적':'REFINER RUINS','연구실':'LAB','등대':'BEAC',
    '초원마을 로우엔':'LOWEN','로우엔 복지회관':'LOWEN CENTER',
    '로우엔 관청':'LOWEN HALL','로우엔 여관':'LOWEN INN','로우엔 평원':'LOWEN FLD',
    '코르버스 본부':'CORVUS HQ','코르버스 사령부':'CORVUS CMD',
    '로우엔 공장':'LOWEN FCT','숨겨진 회의실':'HIDDEN MTG RM',
    '사령의 동굴':'DEAD CAVE','파괴된 대지':'RUINED LAND',
    '굴베이그의 방':'GULVEIG ROOM','유적의 전장':'RUIN BATTLE',
    '야수의 숲':'BEAST WDS','잔존민의 은거지':'REFUGE',
    '지하 통로':'TUNNEL','고대 연구 시설':'ANCIENT LAB','유적의 코어':'RUIN CORE',
    '촌장의 집':'ELDER HUT','도서관':'LIB',
}
PATTERN=re.compile('('+'|'.join(re.escape(s) for s in sorted(NAMES,key=len,reverse=True))+r')(\s+[1-9])?$')


def location_suffix(source: str):
    match=PATTERN.search(source)
    if not match:return None
    prefix=source[:match.start()]
    if not prefix.isascii():return None
    name=match.group(1);number=match.group(2) or ''
    value=NAMES[name]+number
    # B1 would duplicate a floor number; use basement abbreviation instead.
    if name=='토레즈 지하':value='TOREZ B'+number
    # The forest name must fit the original 13-byte slot with its area number.
    if name=='네메시스 숲' and number:value='NEMESIS WD'+number
    return prefix,source[match.start():],value


def normalize_entry(entry: dict) -> bool:
    match=location_suffix(entry['source'])
    if not match:return False
    prefix,source,value=match
    entry['prefix_hex']=(bytes.fromhex(entry.get('prefix_hex') or '')+prefix.encode('cp949')).hex()
    entry['source']=source
    entry['translation']=value
    if len(value.encode('ascii'))>len(source.encode('cp949')):
        raise ValueError(f"Location exceeds original text slot: {entry['id']}")
    return True
