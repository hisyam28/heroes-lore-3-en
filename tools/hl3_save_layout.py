"""Use the visible translated save length instead of its padded storage size."""
import struct
from hl3_modal_guard import file_offset

ADDRESS=0xe39304
EXPECTED=bytes.fromhex('88018052e84b06f9e8e9ff90088d2491e84706f9')


def patch(native):
    p=file_offset(native,ADDRESS)
    if native[p:p+len(EXPECTED)]!=EXPECTED:
        raise ValueError('Unknown native save-toast construction')
    result=bytearray(native)
    # mov w8,#12 -> mov w8,#6. The following existing stores construct the
    # same string slice, now excluding the six storage-padding spaces.
    result[p:p+4]=struct.pack('<I',0x528000c8)
    assert result[:p]==native[:p] and result[p+4:]==native[p+4:]
    return bytes(result),{'saved_visible_bytes':6,'saved_storage_bytes':12,
        'padding_spaces_excluded':6,'failed_message_visible_bytes':12,
        'native_instruction_bytes_reserved':4,'save_logic_and_message_addresses_unchanged':True}
