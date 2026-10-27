#!/usr/bin/env python3
"""Execute HL3's actual Thumb font functions with stubbed platform calls.

Requires capstone/unicorn/pillow installed into work/analysis-deps. This is a
font-kernel regression test and instruction benchmark, not a device FPS test.
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"work/analysis-deps"))
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_HOOK_CODE
from unicorn.arm_const import *
from hl3_font_runtime import build_font, patch_metrics, TEXT_DELTA


class FontVM:
    def __init__(self,module: bytes, small: bytes, large: bytes, actual_pixels=False):
        self.actual_pixels=actual_pixels
        self.uc = Uc(UC_ARCH_ARM,UC_MODE_THUMB)
        for address,size in [(0x1000,0x60000),(0x1400000,0x200000),
                             (0x2000000,0x40000),(0x3000000,0x10000),
                             (0x4000000,0x1000)]:
            self.uc.mem_map(address,size)
        self.uc.mem_write(0x1000,module[0x34:0x34+383877])
        self.uc.mem_write(0x1503a45,b"\1")  # font loaded
        self.uc.mem_write(0x15000cf,small)
        self.uc.mem_write(0x15004e4,large)
        # Korean fallback glyph composition tables for regression cases.
        self.uc.mem_write(0x15027e9,(ROOT/"work/original/res/font/table").read_bytes())
        kor=(ROOT/"work/original/res/font/korb").read_bytes()
        self.uc.mem_write(0x1501a29,kor[:3520])
        self.uc.mem_write(0x1501299,kor[3520:3520+1936])
        self.uc.mem_write(0x15008f9,kor[5456:5456+2464])
        etc=(ROOT/"work/original/res/font/etc").read_bytes()
        for addr,a,b in [(0x1500072,0,93),(0x1500046,93,137),
                          (0x150001e,137,177),(0x1500008,177,199)]:
            self.uc.mem_write(addr,etc[a:b])
        if actual_pixels:
            self.uc.mem_write(0x150e754,b'\1')
            self.uc.mem_write(0x150e758,struct.pack('<I',0x2007000))
            self.uc.mem_write(0x2007000,b'\xff\xff')
        self.uc.hook_add(UC_HOOK_CODE,self._hook)
        self.pixels=[]
        self.instructions=0

    def _hook(self,uc,address,size,user):
        self.instructions+=1
        if address==0x2ad6c:
            dest=uc.reg_read(UC_ARM_REG_R0)
            uc.mem_write(dest,struct.pack('<6I',480,2,240,320,0x2008000,2))
            uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
        elif address==0x3554:
            sp=uc.reg_read(UC_ARM_REG_SP)
            x,y=struct.unpack('<ii',uc.mem_read(sp+8,8))
            self.pixels.append((x,y))
            if not self.actual_pixels:
                uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
        elif address in (0x5ae64,0x5aea4):
            dest=uc.reg_read(UC_ARM_REG_R0)
            value=uc.reg_read(UC_ARM_REG_R1)
            length=uc.reg_read(UC_ARM_REG_R2)
            payload=bytes(uc.mem_read(value,length)) if address==0x5ae64 else bytes([value&255])*length
            uc.mem_write(dest,payload)
            uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))

    def call(self,entry: int,regs: list[int],stack: list[int]) -> int:
        self.instructions=0
        self.pixels=[]
        for i in range(13):self.uc.reg_write(UC_ARM_REG_R0+i,0)
        for reg,value in zip([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3],regs):
            self.uc.reg_write(reg,value)
        self.uc.reg_write(UC_ARM_REG_SP,0x3008000)
        if stack:self.uc.mem_write(0x3008000,struct.pack('<'+'I'*len(stack),*stack))
        self.uc.reg_write(UC_ARM_REG_LR,0x4000001)
        self.uc.emu_start(entry|1,0x4000000,count=20000000)
        if self.uc.reg_read(UC_ARM_REG_PC)!=0x4000000:
            raise AssertionError(f'ARM function did not return: {entry:x}')
        return self.uc.reg_read(UC_ARM_REG_R0)

    def width(self,text: str,mode=1) -> int:
        raw=text.encode('cp949');self.uc.mem_write(0x2000000,raw+b'\0')
        return self.call(0x3600,[0x2000000,len(raw),0,0],[mode])

    def lines(self,text: str,width: int,mode=1) -> int:
        raw=text.encode('cp949');self.uc.mem_write(0x2000000,raw+b'\0')
        return self.call(0x37ac,[0x2000000,len(raw),width,mode],[])

    def draw(self,text: str,width=1000,mode=1,start=0,count=None,align=0):
        raw=text.encode('cp949');self.uc.mem_write(0x2000000,raw+b'\0')
        self.call(0x3878,[0,0,0,width],
                  [mode,0x2000000,0,start,len(raw) if count is None else start+count,align])
        return set(self.pixels)


def main():
    module=(ROOT/'work/original/binary.mod').read_bytes()
    compact=(ROOT/'work/original/res/font/eng5').read_bytes()
    old=FontVM(module,compact,compact)  # previous final used eng5 in both slots
    font=build_font()
    new=FontVM(patch_metrics(module),font,font)
    # Every printable glyph, both modes: compare actual ARM pixels with bitmap.
    for mode in (0,1):
        for code in range(33,127):
            char=chr(code)
            if char in '{}@$|;\'':continue  # engine markup
            pixels=new.draw(char,mode=mode)
            rows=font[(code-32)*11:(code-31)*11]
            expected={(x,y+2) for y,row in enumerate(rows[:7]) for x in range(5)
                      if row & (128>>x)}
            assert pixels==expected,(char,mode,pixels^expected)
        assert new.width('ABCDE',mode)==31
        assert new.width('AB CD',mode)==31
        assert new.width('AB.CD',mode)==31
        assert new.lines('ABCDEFGH',18,mode)==3
        pixels=new.draw('A;A',mode=mode)
        a=new.draw('A',mode=mode)
        assert pixels==a|{(x,y+11) for x,y in a}
        # Prefix cursor and split draws match a full draw at a safe boundary.
        full=new.draw('ABC DEF',mode=mode)
        p=new.draw('ABC DEF',mode=mode,count=4)
        q=new.draw('ABC DEF',mode=mode,start=4,count=3)
        assert full==p|q
        # Spaces and punctuation use the same measured/drawn cell, including
        # when the renderer reconstructs a skipped typewriter/scroll prefix.
        sample='AB. CD, EF'
        whole=new.draw(sample,mode=mode,width=36)
        for split in range(1,len(sample)):
            first=new.draw(sample,mode=mode,width=36,count=split)
            rest=new.draw(sample,mode=mode,width=36,start=split)
            assert whole==first|rest,(split,mode)
    samples=['HAND KNIFE','GUARDIAN KNIGHT','THEY DEFEND ALLIES ON THE FRONT LINE.',
             'ABCDEFGHIJKLMNOPQRSTUVWXYZ 0123456789']
    benchmark=[]
    actual_old=FontVM(module,compact,compact,actual_pixels=True)
    actual_new=FontVM(patch_metrics(module),font,font,actual_pixels=True)
    for sample in samples:
        old.draw(sample);before=old.instructions
        new.draw(sample);after=new.instructions
        actual_old.draw(sample,width=210);real_before=actual_old.instructions
        actual_new.draw(sample,width=210);real_after=actual_new.instructions
        benchmark.append({'text':sample,'before_instructions':before,'after_instructions':after,
                          'reduction_percent':round(100*(1-after/before),2),
                          'with_pixel_writer_before':real_before,'with_pixel_writer_after':real_after,
                          'with_pixel_writer_reduction_percent':round(100*(1-real_after/real_before),2),
                          'old_width':old.width(sample),'new_width':new.width(sample)})
    # Korean text still composes identically in a single line.
    assert new.draw('\uc8fc\ub825')==old.draw('\uc8fc\ub825')
    result={'kind':'isolated ARM font kernel: both stubbed pixel writes and real game pixel writer; platform framebuffer/memcpy stubbed',
            'glyph_grid_before':[8,11],'glyph_grid_after':[5,7],
            'latin_advance_before':8,'latin_advance_after':6,'space_advance_after':6,
            'line_height_before':13,'line_height_after':11,
            'tests':'printable glyphs, measuring, wrapping, line height, split drawing, Korean fallback',
            'benchmark':benchmark}
    out=ROOT/'reports/font-kernel-benchmark.json'
    out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
