"""Compile confirmed length-prefixed enemy names; preserve all combat metadata."""
from pathlib import Path
import json,re
from hl3_record_text import parse,build
from hl3_markup import sequence

ROOT=Path(__file__).resolve().parents[1]
# Indexed against both original normal/hard tables; color controls are retained.
NAMES='''ASKR GUARD
CORV WARRIOR
ASKR WARRIOR
SOLT WARRIOR
ASKR TEMPLAR
SOLT ROGUE
BANDIT
CORV ROGUE
ASKR CHASER
CORV ASSASIN
SOLT MAGE
SOLT WIZARD
SOLT WARLOCK
ASKR GUNNER
CORV GUNNER
ASKR SHOOTER
ASKR EXCEL
ASKR WARLOCK
FRST COOPER
WILD COOPER
IRON COOPER
COOPER KNGT
FLAME COOPER
ULT COOPER
SKULL WALKER
SKEL GUARD
DEAD SOLDIER
WILD SKULL
SKULL KNIGHT
KAISER GOLEM
CORV CAPTAIN
SOLT CAPTAIN
ASKR CAPTAIN
CORV CHAMP
SOLT BERSERK
FRST ROCKER
IRON ROCKER
ANCT ROCKER
BLAZE ROCKER
CHAOS ROCKER
LYCAN
ELDER LYCAN
WILD LYCAN
ARMED LYCAN
HEAVY LYCAN
DARK LYCAN
SHRINE IDOL
DEMON
GARGOYLE
HOLY GARGOYL
DEMON KNIGHT
BLOOD DEMON
SHIVA
DUST
MUD GUARDIAN
MUD GOLEM
STONE GOLEM
IRON GOLEM
HOLY GOLEM
ANCT GOLEM
WRAITH SHADE
SHADOW KEEPR
SPECTER
SPECTER LORD
AUTO CANNON
AUTO CANNON
AUTO CANNON
AUTO CANNON
AUTO CANNON
BOOBY TRAP
BOOBY TRAP
BOOBY TRAP
BOOBY TRAP
BOOBY TRAP
STONE HAMMER
IRON HAMMER
COIL PRESS
MEGATON PRSS
MINE FINDER
TRAILER BOT
HOLDER BOT
HAMMER BOT
ARMED BOT
CRAZY BOT
BEE
WASP
FIRE BUG
KING WASP
ANCT BUG
WILD RAT
RAT
BIG MOUSE
RAT
CHAOS MOUSE
SHRINE LIGHT
FLAME SPIRIT
SHINE GUARD
LIGHTN GUARD
ABYSS WRAITH
ARCHON ECHO
BAT
VAMPIRE BAT
BAT
MANEATER BAT
ULT BAT
DARK BAT
HENGE
BLACK HENGE
RED HENGE
BLOOD HENGE
CRAZY HENGE
ARC HENGE
DUST
GHOST
GIBBERLING
BEAR FROG
GIBBER ROCK
ISLE GIBBER
ISLE GIBROCK
SCORPION
POISN SCORP
ARC SCORP
SCORP KING
FROG
ELDER GHOST
ARC LARVA
MUTANT LARVA
HUNTER LARVA
MANEATER
MANEATER
DEATH PLANT
MUSCIPULA
DEATH MUSCIP
CORV SCUTUM
CORV SCUTUM
WILD SCUTUM
CORV IRA
CORV IRA
DARK IRA
IRON BEAST
IRON BEAST
CRAZY TITAN
ELDER MUSCIP
CORV ARBOR
WILD ARBOR
BOX
BOX
BOX
BOX
BOX
BOX
BOX
BOX
RAT
BEE
GHOST
DUST
RAT
BEE
GHOST
DUST'''.splitlines()


def compile_enemies(original: Path,output: Path):
    assert len(NAMES)==161 and max(map(len,NAMES))<=12
    entries=[];canonical=None
    for filename in ['enemy_dat','enemyh_dat']:
        rel='res/dat/'+filename;source=(original/rel).read_bytes();rows=parse(source,1,rel)
        if len(rows)!=len(NAMES) or build(rows)!=source:raise ValueError('Unknown enemy table layout')
        names=[v[0][0] for v in rows]
        if canonical is not None and canonical!=names:raise ValueError('Normal/hard name ordering differs')
        canonical=names;result=[]
        for i,((texts,tail),name) in enumerate(zip(rows,NAMES)):
            old=texts[0];prefix=re.match(r"[@|${}'\"]*",old).group()
            suffix=re.search(r"[@|${}'\"]*$",old).group()
            value=prefix+name+suffix
            assert sequence(old)==sequence(value) and len(tail)==21
            result.append(([value],tail))
            entries.append({'file':rel,'record':i,'source':old,'translation':value})
        target=output/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(build(result))
    (ROOT/'translations/enemy-text.json').write_text(json.dumps({'entries':entries},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return len(entries)
