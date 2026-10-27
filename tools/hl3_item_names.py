"""Confirmed item-record parser and reviewed compact name overrides."""

REVIEW_NAMES = {
    "i0_dat#3": "REINF. LTHR. HAT",
    "i12_dat#7": "INTEL RING",
    "i12_dat#28": "PROT. EARRINGS",
    "i12_dat#27": "SHARP EARRINGS",
    "i12_dat#38": "@ABS. DEF. SOUL",
    "i12_dat#39": "@DEADLY STRIKE",
    "i13_dat#3": "SOUL DOLL",
    "i13_dat#8": "MIGHTY STRIKE",
    "i13_dat#11": "IRON WALL GUARD",
    "i13_dat#20": "BRAVE GUARDIAN",
    "i13_dat#27": "PHOENIX BREATH C",
    "i13_dat#30": "DEMON POSSESS. C",
    "i13_dat#34": "HOLY SPIRIT C",
    "i14_dat#41": "ABEL'S CREST",
    "i14_dat#42": "SIMON'S CREST",
    "i14_dat#43": "POPE'S CREST",
    "i16_dat#15": "SOCKET EXPANSION",
    "i17_dat#2": "CANYON HOLY WATER",
    "i17_dat#4": "TOREZ ID CARD",
    "i17_dat#9": "ROYAL HEART",
    "i17_dat#11": "LEAH TRAINING",
    "i18_dat#11": "REVIVE BOOK (1X)",
    "i18_dat#13": "AUTO LOOT (1X)",
    "i18_dat#14": "TRAVEL BAG (1X)",
    "i18_dat#15": "STAT RESET (1X)",
    "i18_dat#16": "SKILL RESET (1X)",
    "i18_dat#17": "EXP STONE",
    "i18_dat#12": "CUP RAMEN (1X)",
    "i18_dat#22": "BETRAYAL EMBLEM",
    "i18_dat#24": "TRANSCEND. CREST",
    "i1_dat#4": "REINF. LTHR. ROBE",
    "i1_dat#14": "ICE SCALE ARMOR",
    "i1_dat#24": "'RED LION ARMOR",
    "i1_dat#27": "'NIGHT KING ARMOR",
    "i1_dat#33": "BERSERKER ARMOR",
    "i1_dat#47": "@BERSERKER ARMOR",
    "i2_dat#3": "REINF GLOVES",
    "i2_dat#6": "LEOPARD GLOVES",
    "i2_dat#18": "TEMPLE GLOVES",
    "i2_dat#26": "'N.KING GAUNTLETS",
    "i3_dat#3": "REINF. LTHR. SHOES",
    "i3_dat#4": "REINF. LTHR. BOOTS",
    "i3_dat#6": "LEOPARD SHOES",
    "i3_dat#8": "LEOPARD BOOTS",
    "i3_dat#24": "'DRGBONE WALKER",
    "i3_dat#21": "BONE ARMOR SHOES",
    "i3_dat#26": "'PLUTO ASSASSIN",
    "i5_dat#14": "RED LION G.SWORD",
    "i5_dat#19": "SUPREME SWORD",
    "i5_dat#21": "MAGIC KILLER",
    "i5_dat#27": "@JINMAGE KILLER",
    "i7_dat#14": "HARRIER BARREL",
    "i10_dat#0": "HOLYSTONE",
    "i10_dat#11": "HOLY DIAMOND",
    "i12_dat#37": "@PERFECT AIM SOUL",
    "i16_dat#13": "STORM",
}

def parse_records(data: bytes, filename: str) -> list[tuple[int, bytes, bytes, str]]:
    records = []
    pos = 0
    while pos + 2 <= len(data):
        size = int.from_bytes(data[pos:pos + 2], "little")
        end = pos + 2 + size
        if not size or end > len(data):
            raise ValueError(f"{filename}: invalid record length at {pos}")
        record = data[pos + 2:end]
        if not record:
            raise ValueError(f"{filename}: empty record at {pos}")
        n = record[0]
        if n + 1 > len(record):
            raise ValueError(f"{filename}: item name exceeds record at {pos}")
        name_raw = record[1:1 + n]
        try:
            name = name_raw.decode("cp949")
        except UnicodeDecodeError as exc:
            raise ValueError(f"{filename}: item name is not CP949 at {pos}") from exc
        records.append((pos, record, name_raw, name))
        pos = end
    if pos != len(data):
        raise ValueError(f"{filename}: trailing opaque bytes at {pos}")
    return records
