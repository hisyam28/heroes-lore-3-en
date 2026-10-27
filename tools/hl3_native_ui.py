"""Translate guarded native UI constants while preserving offsets and byte lengths."""
LABELS={'저장완료':'SAVED.','저장실패':'SAVE FAILED.'}

# Adjacent Rust string slices use explicit byte lengths rather than NULs.
# Guard the entire sequence, then replace each slice at its original position.
SETTINGS_OFFSET=0xb73e52
SETTINGS=[
 ('설정','CONFIG'),('세로','  VERT'),('가로',' HORIZ'),('십자키','     DPAD'),
 ('스틱',' STICK'),('끔','OFF'),('켬',' ON'),('전체 화면','   FULLSCREEN'),
 ('화면 높이','   FIT HEIGHT'),('가로 전용','    LANDSCAPE'),('편집','  EDIT'),
 ('화면 배치','LAYOUT'),('자유 스틱','   FREE STICK'),('조작 방식','CONTROLS'),
 ('서버 주소','SERVER ADDR'),('계정 코드','ACCOUNT ID'),('보기 변경','    VIEW/EDIT'),
 ('빠른 저장','QUICK SAVE'),('지금','   NOW'),('진단 정보','DIAGNOSTICS'),
 ('발열 절감','LOW HEAT'),('기본','NORMAL'),('자동','  AUTO'),('항상 켬',' ALWAYS ON'),
 ('패드 표시','PAD HUD'),('서버','SERVER'),('오프라인','     OFFLINE'),
 ('창고 연결','STORAGE LINK'),('닫기','  OK  '),('L3','L3'),('결합',' FUSE '),('취소','CANCEL'),
]
EXTRA_SETTINGS=[
 (0xffe40,'세이브 복원','RESTORE SAVE'),
 (0x100fb0,'효과음 크기','SFX VOLUME'),
 (0x128505,'발열 절감: 끔 (재시작 후 적용)','LOW HEAT: OFF (RESTART)'),
 (0x12852e,'발열 절감: 켬 (재시작 후 적용)','LOW HEAT: ON (RESTART)'),
 (0x128557,'게임패드 HUD: 자동','PAD HUD: AUTO'),
 (0x12856f,'게임패드 HUD: 항상 켬','PAD HUD: ALWAYS ON'),
 (0x12858b,'게임패드 HUD: 끔','PAD HUD: OFF'),
 (0x1285a0,'창고: 자동','STORE: AUTO'),
 (0x1285ae,'창고: 서버','STORE: SERVER'),
 (0x1285bc,'창고: 오프라인','STORE: OFFLINE'),
]


def localize(native: bytes):
    result=native;changes=[]
    for source,value in LABELS.items():
        old=source.encode('utf-8');new=value.encode('ascii')
        if result.count(old)!=1 or len(new)>len(old):
            raise ValueError('Unknown native save notification revision')
        pos=result.index(old);replacement=new.ljust(len(old),b' ')
        result=result[:pos]+replacement+result[pos+len(old):]
        changes.append({'group':'save','source':source,'translation':value,'offset':pos,'byte_length':len(old)})
    expected=''.join(s for s,t in SETTINGS).encode('utf-8')
    if result[SETTINGS_OFFSET:SETTINGS_OFFSET+len(expected)]!=expected:
        raise ValueError('Unknown native settings string block')
    fields=[];pos=SETTINGS_OFFSET
    for source,value in SETTINGS:
        fields.append((pos,source,value));pos+=len(source.encode('utf-8'))
    for pos,source,value in fields+EXTRA_SETTINGS:
        old=source.encode('utf-8');new=value.encode('ascii')
        if result[pos:pos+len(old)]!=old or len(new)>len(old):
            raise ValueError(f'Unknown or oversized native setting at {pos:#x}')
        result=result[:pos]+new.ljust(len(old),b' ')+result[pos+len(old):]
        if source!=value:
            changes.append({'group':'settings','source':source,'translation':value.strip(),'offset':pos,'byte_length':len(old)})
    assert len(result)==len(native)
    return result,changes
