"""Translate fixed-length native save notification constants without code edits."""
LABELS={'저장완료':'SAVED.','저장실패':'SAVE FAILED.'}


def localize(native: bytes):
    result=native;changes=[]
    for source,value in LABELS.items():
        old=source.encode('utf-8');new=value.encode('ascii')
        if result.count(old)!=1 or len(new)>len(old):
            raise ValueError('Unknown native save notification revision')
        pos=result.index(old);replacement=new.ljust(len(old),b' ')
        result=result[:pos]+replacement+result[pos+len(old):]
        changes.append({'source':source,'translation':value,'offset':pos,'byte_length':len(old)})
    assert len(result)==len(native)
    return result,changes
