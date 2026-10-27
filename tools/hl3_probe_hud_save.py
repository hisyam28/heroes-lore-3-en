"""Execute enemy HUD calls and native save-slice construction in isolation."""
from pathlib import Path
import json,struct,sys,zipfile,tempfile
from hl3_probe_font import FontVM
from hl3_probe_modal import NativeVM
from hl3_font_runtime import build_font,patch_metrics,TEXT_DELTA
from hl3_home_ui import patch_slots
from hl3_build_optimized import compile_module
from hl3_hud_layout import MODE,DIGITS,patch as patch_hud
from hl3_save_layout import patch as patch_save
from hl3_native_ui import localize

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'work/analysis-deps'))
from unicorn.arm_const import *
from unicorn.arm64_const import UC_ARM64_REG_SP
from PIL import Image,ImageDraw
from hl3_bitmap import parse,decode


def hud(vm,entry,stop,text,width=240):
    u=vm.uc;sp=0x3008000
    vm.pixels=[]
    u.mem_write(0x2000000,text.encode()+b'\0')
    u.mem_write(0x2003000,struct.pack('<I',0x2003100))
    u.mem_write(0x2003140,struct.pack('<HH',86,26))
    u.mem_write(0x2004000,struct.pack('<I',0))
    u.mem_write(0x1503a50,struct.pack('<I',0))
    u.mem_write(sp,bytes(0x100))
    for reg,value in [(UC_ARM_REG_SP,sp),(UC_ARM_REG_R0,len(text)),
                      (UC_ARM_REG_R4,0x2004000),(UC_ARM_REG_R5,0x2000000),
                      (UC_ARM_REG_R6,width),(UC_ARM_REG_R7,0x2003000)]:u.reg_write(reg,value)
    u.emu_start(entry|1,stop,count=1000000)
    assert u.reg_read(UC_ARM_REG_PC)==stop
    assert u.reg_read(UC_ARM_REG_SP)==sp
    # Alignment remains left; only the font mode changes at the call site.
    assert int.from_bytes(u.mem_read(sp+8,4),'little')==0
    return set(vm.pixels)


def native_slice(native,entry,stop):
    vm=NativeVM(native);u=vm.uc;sp=0x4100000
    u.reg_write(UC_ARM64_REG_SP,sp);u.emu_start(entry,stop,count=100)
    pointer,length=struct.unpack('<QQ',u.mem_read(sp+0xc88,16))
    return bytes(u.mem_read(pointer,length)).decode('ascii')


def main():
    with tempfile.TemporaryDirectory(dir=ROOT/'work',prefix='hud-regression-') as tmp:
        compile_module(ROOT/'work/original',Path(tmp))
        before=patch_slots(patch_metrics((Path(tmp)/'binary.mod').read_bytes()))
    after=(ROOT/'work/optimized/binary.mod').read_bytes();font=build_font()
    assert after==patch_hud(before)[0]
    for offset in (0x3ca2-TEXT_DELTA,0x5b420):
        bad=bytearray(before);bad[offset]^=1
        try:patch_hud(bytes(bad))
        except ValueError:pass
        else:raise AssertionError('HUD patch accepted an unknown instruction/padding revision')
    old=FontVM(before,font,font);new=FontVM(after,font,font)
    # All ordinary modes and printable glyphs retain their exact pixel output.
    normal=0
    for mode in (0,1,2,3):
        for code in range(33,127):
            if chr(code) in "{}@$|;'":continue
            text=chr(code)
            assert old.draw(text,mode=mode)==new.draw(text,mode=mode),(mode,code)
            assert old.width(text,mode)==new.width(text,mode)
            normal+=1
    for digit,rows in enumerate(DIGITS):
        expected={(x+1,y+2) for y,bits in enumerate(rows) for x in range(3) if bits&(4>>x)}
        assert new.draw(str(digit),mode=MODE)==expected
    for mode in (0,1,2,3):
        for text in ('AB CD;EF 0123456789','주력','보조'):
            assert old.draw(text,mode=mode)==new.draw(text,mode=mode)
    benchmark=[]
    for mode in (0,1):
        for text in ('HENGE','RESTORE 200 HP.','99'):
            old.draw(text,mode=mode);before_count=old.instructions
            new.draw(text,mode=mode);after_count=new.instructions
            assert after_count<=before_count
            benchmark.append({'mode':mode,'text':text,'before_instructions':before_count,'after_instructions':after_count})
    cases=[]
    for entry,stop in [(0x25da,0x2600),(0x27b6,0x27dc)]:
        for width in (240,480):
            for number in list(range(1,128))+[200,255,999]:
                points=hud(new,entry,stop,str(number),width)
                frame_x=width-88
                assert all(frame_x+16<=x<frame_x+31 and 19<=y<=23 for x,y in points),(entry,number,points)
                cases.append({'entry':hex(entry),'viewport_width':width,'level':number})
    with zipfile.ZipFile(ROOT/'work/heroes-lore-3-final.apk') as apk:native=apk.read('lib/arm64-v8a/libmain.so')
    native,_=localize(native);fixed,save_report=patch_save(native)
    old_text=native_slice(native,0xe39304,0xe39320)
    text=native_slice(fixed,0xe39304,0xe39320)
    failed=native_slice(fixed,0xe360c8,0xe360dc)
    assert old_text=='SAVED.      ' and text=='SAVED.' and failed=='SAVE FAILED.'
    result={'kind':'actual Thumb HUD calls and AArch64 save-slice construction; platform drawing modeled',
        'enemy_level_cases':len(cases),'enemy_levels_tested':'1..127, 200, 255, 999',
        'viewport_widths':[240,480],'enemy_level_ink_height':5,'enemy_level_call_sites':2,
        'lv_label_baseline_matched':True,'frame_and_hp_bar_overlap':False,
        'ordinary_glyph_mode_cases_identical':normal,'unknown_instruction_and_occupied_padding_rejected':True,
        'ordinary_font_instruction_samples':benchmark,'ordinary_font_instruction_samples_not_increased':True,
        'save_slice_before':old_text,'save_slice_after':text,
        'save_failed_slice':failed,'save_toast':save_report,
        'physical_device_tested':False,'all_checks_passed':True}
    (ROOT/'reports/hud-save-layout-validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    # Preview combines the original frame artwork with actual executed pixels.
    frame=decode(parse((ROOT/'work/original/res/comm/ui_bm').read_bytes())[4])
    sheet=Image.new('RGB',(450,140),(30,27,25));draw=ImageDraw.Draw(sheet)
    draw.text((8,8),'BEFORE',fill='white');draw.text((228,8),'AFTER',fill='white')
    for column,vm in enumerate((old,new)):
        for row,number in enumerate((1,99,127)):
            ox=column*220+12;oy=28+row*30
            sheet.paste(frame,(ox,oy),frame)
            points=hud(vm,0x25da,0x2600,str(number))
            for x,y in points:sheet.putpixel((ox+x-152,oy+y-2),(255,255,255))
    draw.text((8,123),'ACTUAL ARM PIXELS / NOT A DEVICE SCREENSHOT',fill='white')
    sheet.resize((1350,420),Image.Resampling.NEAREST).save(ROOT/'reports/enemy-level-preview.png')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
