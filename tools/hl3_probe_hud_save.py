"""Execute enemy HUD calls and native save-slice construction in isolation."""
from pathlib import Path
from io import BytesIO
import json,struct,sys,zipfile,tempfile
from hl3_probe_font import FontVM
from hl3_probe_modal import NativeVM
from hl3_font_runtime import build_font,patch_metrics,TEXT_DELTA
from hl3_home_ui import patch_slots
from hl3_build_optimized import compile_module
from hl3_hud_layout import MODE,DIGITS,DIGIT_ADVANCE,patch as patch_hud
from hl3_assets import find_game_jar
from hl3_confirmation_ui import patch as patch_confirmation
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
    assert after==patch_confirmation(patch_hud(before)[0])[0]
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
    for text in ('11','99','127','200','255','999'):
        expected={(i*DIGIT_ADVANCE+x+1,y+2) for i,digit in enumerate(text)
                  for y,bits in enumerate(DIGITS[int(digit)]) for x in range(3) if bits&(4>>x)}
        assert new.draw(text,mode=MODE)==expected,text
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
    frame=decode(parse((ROOT/'work/original/res/comm/ui_bm').read_bytes())[4])
    # Include every LV artwork pixel, not just the numeric frame boundary.
    lv={(x,y) for y in range(14,23) for x in range(5,22) if frame.getpixel((x,y))[3]}
    lv_right=max(x for x,y in lv);lv_top=min(y for x,y in lv);lv_bottom=max(y for x,y in lv)
    cases=[];minimum_gap=100;minimum_bar_gap=100
    for entry,stop in [(0x25da,0x2600),(0x27b6,0x27dc)]:
        for width in (240,480):
            for number in list(range(1,128))+[200,255,999]:
                points=hud(new,entry,stop,str(number),width)
                frame_x=width-88
                relative={(x-frame_x,y-2) for x,y in points}
                gap=min(x for x,y in relative)-lv_right-1
                bar_gap=31-max(x for x,y in relative)-1
                assert gap>=3 and bar_gap>=1,(entry,number,gap,bar_gap)
                assert min(y for x,y in relative)==lv_top and max(y for x,y in relative)==lv_bottom
                assert not relative&lv
                minimum_gap=min(minimum_gap,gap);minimum_bar_gap=min(minimum_bar_gap,bar_gap)
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
        'minimum_gap_after_lv_px':minimum_gap,'minimum_gap_before_hp_bar_px':minimum_bar_gap,
        'numeric_cursor_advance':DIGIT_ADVANCE,'numeric_letter_gap':1,'publication_status':'local draft; not released',
        'ordinary_glyph_mode_cases_identical':normal,'unknown_instruction_and_occupied_padding_rejected':True,
        'ordinary_font_instruction_samples':benchmark,'ordinary_font_instruction_samples_not_increased':True,
        'save_slice_before':old_text,'save_slice_after':text,
        'save_failed_slice':failed,'save_toast':save_report,
        'physical_device_tested':False,'all_checks_passed':True}
    (ROOT/'reports/hud-save-layout-validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    # Preview combines the original frame artwork with actual executed pixels.
    previews=[('LEGACY',old)]
    released_apk=ROOT/'dist/v1.1.3/heroes-lore-3-en-v1.1.3.apk'
    # An optional local released artifact adds a comparison column; validation
    # and builds do not depend on retaining old APK releases.
    if released_apk.exists():
        with zipfile.ZipFile(released_apk) as apk:
            data,_=find_game_jar(apk)
            with zipfile.ZipFile(BytesIO(data)) as jar:released_module=jar.read('binary.mod')
        previews.append(('RELEASED',FontVM(released_module,font,font)))
    previews.append(('LOCAL DRAFT',new))
    sheet=Image.new('RGB',(len(previews)*220+20,150),(30,27,25));draw=ImageDraw.Draw(sheet)
    for column,(label,vm) in enumerate(previews):
        draw.text((column*220+8,8),label,fill='white')
        for row,number in enumerate((1,99,127)):
            ox=column*220+12;oy=28+row*30
            sheet.paste(frame,(ox,oy),frame)
            points=hud(vm,0x25da,0x2600,str(number))
            for x,y in points:sheet.putpixel((ox+x-152,oy+y-2),(255,255,255))
    draw.text((8,126),'ACTUAL ARM PIXELS / NOT A DEVICE SCREENSHOT / LOCAL DRAFT ONLY',fill='white')
    sheet.resize((sheet.width*3,450),Image.Resampling.NEAREST).save(ROOT/'reports/enemy-level-preview.png')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
