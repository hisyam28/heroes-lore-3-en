#!/usr/bin/env python3
"""Replay the shipped AArch64 modal detector and pointer lifecycle in Unicorn.

Frames are synthetic native-color panels, not screenshots. Allocator/libc calls
are modeled; the real detector, owner-set insert/remove and release code run.
No physical device or Android event loop is involved.
"""
from pathlib import Path
import json,struct,sys,zipfile
from hl3_modal_guard import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'work/analysis-deps'))
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm64_const import *


class NativeVM:
    STATE=0x2100000
    OUT=STATE+0x1000
    STOP=0x2000000
    def __init__(self,native):
        self.uc=Uc(UC_ARCH_ARM64,UC_MODE_ARM);u=self.uc
        for address,size in [(0,0x2000000),(0x2000000,0x1000000),(0x3000000,0x1000000),(0x4000000,0x200000)]:u.mem_map(address,size)
        h=struct.unpack_from('<16sHHIQQQIHHHHHH',native)
        for i in range(h[10]):
            p=struct.unpack_from('<IIQQQQQQ',native,h[5]+i*h[9])
            if p[0]==1:u.mem_write(p[3],native[p[2]:p[2]+p[5]])
        sh=[struct.unpack_from('<IIQQQQIIQQ',native,h[6]+i*h[11]) for i in range(h[12])]
        syms=next(s for s in sh if s[1]==11);strings=sh[syms[6]]
        names=native[strings[4]:strings[4]+strings[5]];self.imports={}
        # This guarded library revision has standard relative and PLT relocation tables.
        for p in range(0x2728,0x2728+0x66000,24):
            addr,info,addend=struct.unpack_from('<QQq',native,p)
            if info&0xffffffff==1027:u.mem_write(addr,struct.pack('<Q',addend))
        for i,p in enumerate(range(0x68728,0x68728+0x1380,24)):
            _,info,_=struct.unpack_from('<QQq',native,p)
            sym=struct.unpack_from('<IBBHQQ',native,syms[4]+(info>>32)*24)
            self.imports[0x15fe5b0+32+i*16]=names[sym[0]:names.find(b'\0',sym[0])].decode()
        u.reg_write(UC_ARM64_REG_CPACR_EL1,0x300000)
        self.heap=0x3000000;self.allocations={};self.stops=set();self.events=[];self.instructions=0
        u.hook_add(UC_HOOK_CODE,self.hook)
        s=self.STATE
        u.mem_write(s+0x338,struct.pack('<4I',0,0,480,222))
        u.mem_write(s+0x68,struct.pack('<Q',2));u.mem_write(s+0x731,b'\1');u.mem_write(s+0x6d8,b'\1\0')
        u.mem_write(0x1660268,struct.pack('<3I',480,222,0))
        u.mem_write(s+0x460,struct.pack('<i',-1));u.mem_write(s+0x510,b'\xfe')
        for offset,ctrl in [(0x550,0x2400000),(0x580,0x2400100)]:
            u.mem_write(ctrl,b'\xff'*32);u.mem_write(s+offset,struct.pack('<6Q',ctrl,0,0,0,0,0))

    def hook(self,u,pc,size,user):
        self.instructions+=1
        if self.instructions>18000000:raise AssertionError('Native replay instruction limit')
        if pc in self.stops:u.emu_stop();return
        if pc==0xde8fc8:
            self.events.append('raw_pointer_release');u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR));return
        if pc==0xde0768:raise AssertionError('Consumed modal tap dispatched a key/menu event')
        if pc not in self.imports:return
        name=self.imports[pc];a,b,c=[u.reg_read(r) for r in [UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2]]
        if name in ['malloc','calloc','realloc']:
            amount=a if name=='malloc' else a*b if name=='calloc' else b
            result=self.heap;self.heap+=(amount+15)&~15
            assert self.heap<0x4000000
            if name=='realloc' and a:u.mem_write(result,bytes(u.mem_read(a,min(amount,self.allocations.get(a,0)))))
            self.allocations[result]=amount;u.reg_write(UC_ARM64_REG_X0,result)
        elif name=='free':self.allocations.pop(a,None)
        elif name in ['memcpy','memmove']:u.mem_write(a,bytes(u.mem_read(b,c)))
        elif name=='memset':u.mem_write(a,bytes([b&255])*c)
        elif name=='memcmp':
            aa=bytes(u.mem_read(a,c));bb=bytes(u.mem_read(b,c))
            u.reg_write(UC_ARM64_REG_X0,(0 if aa==bb else -1 if aa<bb else 1)&0xffffffffffffffff)
        else:raise AssertionError('Unexpected native replay import: '+name)
        u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR))

    def frame(self,selected='left'):
        rgb=[0xff000000]*(480*222)
        if selected:
            for y in range(102,116):
                for x in range(186,236):rgb[y*480+x]=0xff5a1c00 if selected=='left' else 0xffbdb2ad
                for x in range(242,292):rgb[y*480+x]=0xffbdb2ad if selected=='left' else 0xff5a1c00
        self.uc.mem_write(0x2200000,struct.pack('<'+'I'*len(rgb),*rgb))
        self.uc.mem_write(self.STATE+0x3a0,struct.pack('<QQ',0x2200000,len(rgb)))

    def run(self,pc,x,y,pointer=7,stops=()):
        u=self.uc;self.instructions=0;self.stops=set(stops)
        for i in range(31):u.reg_write(UC_ARM64_REG_X0+i,0)
        for reg,value in [(UC_ARM64_REG_X0,self.OUT),(UC_ARM64_REG_X1,self.STATE),
                          (UC_ARM64_REG_X19,self.STATE),(UC_ARM64_REG_X20,pointer),
                          (UC_ARM64_REG_SP,0x4100000),(UC_ARM64_REG_LR,self.STOP)]:u.reg_write(reg,value)
        for reg,value in [(UC_ARM64_REG_D0,x),(UC_ARM64_REG_D1,y),(UC_ARM64_REG_D9,x),(UC_ARM64_REG_D8,y)]:
            u.reg_write(reg,int.from_bytes(struct.pack('<d',value),'little'))
        u.emu_start(pc,self.STOP,count=20000000)
        assert u.reg_read(UC_ARM64_REG_PC) in self.stops|{self.STOP}

    def detect(self,x,y):
        self.run(0xde6d08,x,y)
        return struct.unpack('<i',self.uc.mem_read(self.OUT,4))[0],self.uc.mem_read(self.OUT+4,1)[0]

    def cached(self):return struct.unpack('<i',self.uc.mem_read(self.STATE+0x460,4))[0]
    def owned_count(self):return int.from_bytes(self.uc.mem_read(self.STATE+0x568,8),'little')


def main():
    with zipfile.ZipFile(ROOT/'work/heroes-lore-3-final.apk') as apk:original=apk.read('lib/arm64-v8a/libmain.so')
    changed,patch_report=patch(original);before=NativeVM(original);after=NativeVM(changed);cases=[]
    for selected in ['left','right']:
        before.frame(selected);after.frame(selected)
        for x,y in [(210,109),(270,109),(240,85),(240,136),(240,165)]:
            a=before.detect(x,y);b=after.detect(x,y)
            if a[0]==-1:assert b[0]==-2
            else:assert a==b
            cases.append({'selection':selected,'point':[x,y],'before_tag':a[0],'after_tag':b[0]})
    before.frame(None);after.frame(None)
    for x,y in [(240,85),(0,0),(479,221)]:assert before.detect(x,y)[0]==after.detect(x,y)[0]==-1
    # Replay pointer down -> optional move -> release, with the actual owner set.
    lifecycles=[]
    for pointer,movement in [(0,0),(7,20),(13,50)]:
        vm=NativeVM(changed);vm.frame('left')
        vm.run(0xdc5a7c,240,85,pointer,{0xdc51bc})
        assert vm.cached()==-2 and vm.owned_count()==1
        if movement:
            vm.run(0xdc4640,240+movement,85,pointer,{0xdc51bc})
            assert vm.owned_count()==1
        vm.run(0xdc402c,240+movement,85,pointer,{0xdc51bc})
        assert vm.cached()==-1 and vm.owned_count()==0 and not vm.events
        lifecycles.append({'pointer_id':pointer,'movement_px':movement,'owner_cleared':True,'guest_events_emitted':0})
    legacy=NativeVM(original);legacy.frame('left')
    legacy.run(0xdc5a7c,240,85,7,{0xdc51bc});assert legacy.owned_count()==0
    legacy.run(0xdc402c,240,85,7,{0xdc51bc});assert legacy.events==['raw_pointer_release']
    result={'kind':'isolated AArch64 replay with synthetic native-color modal frames',
            'modal_cases':cases,'nonmodal_and_outside_panel_cases_unchanged':3,'pointer_lifecycles':lifecycles,
            'legacy_modal_miss_leak_reproduced':True,'touchpoint_configuration_changed':False,
            'patch':patch_report,'physical_device_tested':False,'all_checks_passed':True}
    (ROOT/'reports/modal-input-validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
