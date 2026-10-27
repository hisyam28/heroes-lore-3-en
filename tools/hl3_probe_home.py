#!/usr/bin/env python3
"""Execute the actual slot-row routine and validate the native settings overlay."""
from pathlib import Path
import sys,struct,json,zipfile
from hl3_probe_font import FontVM
from hl3_font_runtime import build_font,patch_metrics
from hl3_home_ui import patch_slots
from hl3_native_ui import localize

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'work/analysis-deps'))
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
from PIL import Image,ImageDraw


def slot_row(module,number,selected):
    vm=FontVM(module,build_font(),build_font());uc=vm.uc
    uc.mem_write(0x2001000,f'SLOT {number}'.encode()+b'\0')
    uc.mem_write(0x2005000,b'\0'*4);rects=[]
    def dispatch(uc,address,size,user):
        regs={0x5a6f4:UC_ARM_REG_R3,0x5a6f8:UC_ARM_REG_R4,0x5a6fc:UC_ARM_REG_R5,
              0x5a700:UC_ARM_REG_R6,0x5a704:UC_ARM_REG_R7,0x5a718:UC_ARM_REG_R12}
        if address not in regs:return
        target=uc.reg_read(regs[address]);plain=target&~1
        if plain in (0x1068,0x2ad64,0x3e14,0x5ae34,0x2c9e0,0x2bb6c):
            value=0
            if plain==0x1068:value=0x2004000
            elif plain==0x2ad64:value=0x2005000
            elif plain==0x5ae34:
                ptr=uc.reg_read(UC_ARM_REG_R0)
                while bytes(uc.mem_read(ptr+value,1))!=b'\0':value+=1
            elif plain in (0x2c9e0,0x2bb6c):
                sp=uc.reg_read(UC_ARM_REG_SP)
                rects.append((plain,uc.reg_read(UC_ARM_REG_R1),uc.reg_read(UC_ARM_REG_R2),
                              uc.reg_read(UC_ARM_REG_R3),int.from_bytes(uc.mem_read(sp,4),'little')))
            uc.reg_write(UC_ARM_REG_R0,value)
            uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
        else:uc.reg_write(UC_ARM_REG_PC,target)
    uc.hook_add(UC_HOOK_CODE,dispatch)
    vm.call(0x53c0,[120,30,0x2001000,selected],[])
    return set(vm.pixels),rects


def bounds(pixels):
    return min(x for x,y in pixels),min(y for x,y in pixels),max(x for x,y in pixels),max(y for x,y in pixels)


def main():
    original=(ROOT/'work/original/binary.mod').read_bytes()
    before=patch_metrics(original);after=patch_slots(before);results=[]
    sheet=Image.new('RGB',(480,180),(28,25,24));draw=ImageDraw.Draw(sheet)
    draw.text((12,8),'BEFORE',fill='white');draw.text((252,8),'AFTER',fill='white')
    for number in (1,2,3):
        for selected in (0,1):
            old_pixels,old_rects=slot_row(before,number,selected)
            pixels,rects=slot_row(after,number,selected)
            _,rx,ry,rw,rh=rects[0];_,bx,by,bw,bh=rects[1]
            digit={(x,y) for x,y in pixels if x>126};x0,y0,x1,y1=bounds(digit)
            error_x=abs((x0+x1)/2-(bx+(bw-1)/2));error_y=abs((y0+y1)/2-(by+(bh-1)/2))
            combined_x=(min(x for x,y in pixels)+bx+bw-1)/2
            assert error_x<=0.5 and error_y<=0.5,(number,selected,error_x,error_y)
            assert abs(combined_x-(rx+(rw-1)/2))<=0.5
            assert abs(by+(bh-1)/2-(ry+(rh-1)/2))<=0.5
            assert rects[0]==old_rects[0] and len(before)==len(after)
            results.append({'slot':number,'selected':bool(selected),'digit_center_error_px':[error_x,error_y],
                            'row_center_error_px':abs(combined_x-(rx+(rw-1)/2))})
            if selected!=1:continue
            for column,(points,boxes) in enumerate([(old_pixels,old_rects),(pixels,rects)]):
                offset_x=column*240;offset_y=number*32
                for kind,x,y,w,h in boxes:
                    area=(offset_x+x-30,offset_y+y-25,offset_x+x-30+w-1,offset_y+y-25+h-1)
                    if kind==0x2c9e0:draw.rectangle(area,fill=(106,78,62))
                    else:draw.rectangle(area,outline=(255,255,255))
                for x,y in points:sheet.putpixel((offset_x+x-30,offset_y+y-25),(255,255,255))
    font=build_font();vm=FontVM(after,font,font)
    assert vm.width('NET STORE')<=70
    with zipfile.ZipFile(ROOT/'work/heroes-lore-3-final.apk') as apk:native=apk.read('lib/arm64-v8a/libmain.so')
    translated,labels=localize(native)
    assert len(translated)==len(native)
    # All executable sections of the host library remain byte-identical.
    header=struct.unpack_from('<16sHHIQQQIHHHHHH',native);code_sections=0
    for i in range(header[12]):
        section=struct.unpack_from('<IIQQQQIIQQ',native,header[6]+i*header[11])
        if section[2]&4:
            p,n=section[4:6];assert native[p:p+n]==translated[p:p+n];code_sections+=1
    settings_count=sum(e['group']=='settings' for e in labels)
    assert settings_count==41 and code_sections>0
    draw.text((12,145),'ACTUAL ARM SLOT ROUTINE / PLATFORM DRAW CALLS MODELED',fill='white')
    draw.text((12,160),'NOT A DEVICE SCREENSHOT',fill='white')
    sheet.resize((1440,540),Image.Resampling.NEAREST).save(ROOT/'reports/home-slot-preview.png')
    result={'kind':'actual ARM slot-row function; host drawing/color/platform calls modeled',
            'slot_cases':results,'native_settings_strings':settings_count,'native_executable_sections_unchanged':code_sections,
            'network_storage_label':'NET STORE','network_label_width':vm.width('NET STORE'),'all_checks_passed':True}
    (ROOT/'reports/home-ui-validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
