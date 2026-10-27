"""Guard independently referenced suffixes inside module string literals."""
ALIASES={0x5b034:b'/ %s%d',0x5b4dc:b'%s%d'}


def validate(data: bytes):
    for offset,expected in ALIASES.items():
        if data[offset:offset+len(expected)+1]!=expected+b'\0':
            raise ValueError(f'Shared format suffix changed at {offset:#x}')
    return len(ALIASES)
