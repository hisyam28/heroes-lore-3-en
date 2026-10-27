"""Consume already-recognized modal misses without changing touchpoint mapping.

The shipped detector reports a modal-owned miss as the same -1 tag used for
ordinary unowned taps. This lets the caller forward the tap to the game below
the popup. Use a private -2 consumed tag only for that terminal path; clear it
at release through the existing cleanup, never dispatching a key or menu action.
"""
import struct

OWNED=0xde89bc
RELEASE=0xdc4034
STUB=OWNED+44
EPILOGUE=0xde6f18
FREE=0x15fe600
CLEANUP=0xdc5048
EXPECTED=bytes.fromhex('a88301d18904009029f12991e8270ca9a84301d1e8270da9c199ffd0219c0f91a0c300d1e20303919ae40294f4030391a9035ef808008012')


def file_offset(native,va):
    h=struct.unpack_from('<16sHHIQQQIHHHHHH',native)
    for i in range(h[10]):
        p=struct.unpack_from('<IIQQQQQQ',native,h[5]+i*h[9])
        if p[0]==1 and p[3]<=va< p[3]+p[5]:return p[2]+va-p[3]
    raise ValueError('Native address is not file-backed')


def branch(src,dst,base=0x14000000):
    distance=dst-src
    if distance%4 or not -(1<<27)<=distance<(1<<27):raise ValueError('Native branch out of range')
    return base|((distance//4)&0x3ffffff)


def conditional(src,dst,condition):
    distance=dst-src
    if distance%4 or not -(1<<20)<=distance<(1<<20):raise ValueError('Native conditional branch out of range')
    return 0x54000000|(((distance//4)&0x7ffff)<<5)|condition


def patch(native):
    owned=file_offset(native,OWNED);release=file_offset(native,RELEASE)
    if (native[owned:owned+56]!=EXPECTED or native[release-4:release+4]!=bytes.fromhex('ff060031a0800054')):
        raise ValueError('Unknown native modal input revision')
    # The selected-choice and alternate-choice paths remain intact. This path
    # frees the same temporary row vector, writes a zeroed plain result and
    # returns without attempting to format the private consumed tag for logs.
    words=[0xf94013f3,0xa9007e7f,0xa9017e7f,0xa9027e7f,0xf9001a7f,
           0x12800028,0xb9000268,
           0xb4000000|((((EPILOGUE-(OWNED+28))//4)&0x7ffff)<<5)|23,
           0xf9401fe0,branch(OWNED+36,FREE,0x94000000),branch(OWNED+40,EPILOGUE),
           0x12800008,0xb9046268,branch(STUB+8,CLEANUP)]
    result=bytearray(native);result[owned:owned+56]=struct.pack('<14I',*words)
    # After cmn(tag,1), LE covers both ordinary None (-1) and consumed (-2).
    # A tiny SP-independent cleanup block clears the cache before the original
    # pointer-owner cleanup. Valid action tags 0..2 follow their original path.
    result[release:release+4]=struct.pack('<I',conditional(RELEASE,STUB,13))
    allowed=set(range(owned,owned+56))|set(range(release,release+4))
    assert len(result)==len(native)
    assert all(a==b for i,(a,b) in enumerate(zip(native,result)) if i not in allowed)
    return bytes(result),{'modal_owned_miss_guard':True,'patch_bytes_reserved':60,
        'touchpoint_and_key_mapping_bytes_unchanged':True,'file_size_preserved':True,
        'ordinary_touch_and_selected_choice_paths_unchanged':True}
