"""The seven control bytes read by HL3 HFont at ELF VA 0x5b2bc."""
MARKUP='@|${}\'"'


def sequence(text: str) -> str:
    return ''.join(c for c in text if c in MARKUP)


def latin_copy(text: str,source: str='') -> str:
    """Keep source color-prefix quotes; English apostrophes are unsafe controls.

    Confirmed event sources have either zero quotes or one leading apostrophe.
    Use familiar uppercase game spellings such as DONT, ITS and LEAS, rather
    than introducing unexpected palette commands in the middle of words.
    """
    if source.strip("'\"")!=source.lstrip("'\""):
        raise ValueError('A trailing source quote needs explicit curation')
    prefix=''
    for char in source:
        if char not in "'\"":break
        prefix+=char
    text=text.translate(str.maketrans('','',"'\"\u2018\u2019\u201c\u201d"))
    result=prefix+text
    result.encode('ascii')
    return result
