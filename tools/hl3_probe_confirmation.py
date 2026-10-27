"""Replay real system-menu input and popup cleanup; model UI creation/free APIs."""
from pathlib import Path
import json,struct,tempfile
from hl3_probe_font import FontVM
from hl3_font_runtime import build_font,patch_metrics
from hl3_home_ui import patch_slots
from hl3_hud_layout import patch as patch_hud
from hl3_confirmation_ui import patch as patch_confirmation,slot_capacity,YES_SLOTS
from hl3_build_optimized import compile_module
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *

ROOT=Path(__file__).resolve().parents[1]


class PopupVM(FontVM):
    STATE=0x1404000
    def __init__(self,module):
        super().__init__(module,build_font(),build_font())
        self.freed=[];self.events=[]
        self.uc.hook_add(UC_HOOK_CODE,self.api)
        self.set8(0x9c46,6);self.set8(0x9c5a,3)
        self.set8(0xa25d,2)

    def set8(self,offset,value):self.uc.mem_write(self.STATE+offset,bytes([value]))
    def get8(self,offset):return self.uc.mem_read(self.STATE+offset,1)[0]
    def pointer(self,address):return int.from_bytes(self.uc.mem_read(address,4),'little')
    def set_pointer(self,address,value):self.uc.mem_write(address,struct.pack('<I',value))

    def open_popup(self,choice=0):
        self.set8(0xa1fc,1);self.set8(0xa221,105);self.set8(0xa220,20)
        self.set8(0xa25c,choice)
        for global_addr,offset,pointer in [(0x151292c,0xa218,0x2002200),
                                           (0x1512930,0xa228,0x2002300),
                                           (0x1512954,0xa230,0x2002400)]:
            self.set_pointer(global_addr,pointer);self.set_pointer(self.STATE+offset,pointer)
        self.set_pointer(0x2002400,0x2002500);self.set_pointer(0x2002404,0x2002600)

    def api(self,u,address,size,user):
        if address==0x1068:u.reg_write(UC_ARM_REG_R0,self.STATE)
        elif address==0x1400274:self.freed.append(u.reg_read(UC_ARM_REG_R0))
        elif address==0x14a4:self.events.append(('main_menu_transition',u.reg_read(UC_ARM_REG_R0)))
        elif address==0x46b7c:
            assert u.reg_read(UC_ARM_REG_R0)==105
            self.open_popup();self.events.append(('open_popup',105))
        else:return
        u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))

    def key(self,key):self.call(0x48098,[key&0xffffffff,0,0,0],[])
    def menu(self):return bytes(self.uc.mem_read(self.STATE+0x9c46,0x24))
    def popup(self):return bytes(self.uc.mem_read(self.STATE+0xa1fc,0x66))


def main():
    with tempfile.TemporaryDirectory(dir=ROOT/'work',prefix='confirm-regression-') as tmp:
        compile_module(ROOT/'work/original',Path(tmp))
        before=patch_hud(patch_slots(patch_metrics((Path(tmp)/'binary.mod').read_bytes())))[0]
    after,patch_report=patch_confirmation(before)
    assert after==(ROOT/'work/optimized/binary.mod').read_bytes()
    bad=bytearray(before);bad[0x480ae-0xfcc]^=1
    try:patch_confirmation(bytes(bad))
    except ValueError:pass
    else:raise AssertionError('Accepted an unknown system-popup revision')
    source=(ROOT/'work/original/binary.mod').read_bytes()
    for offset in YES_SLOTS:
        bad=bytearray(source);bad[offset+3]=1
        try:slot_capacity(bytes(bad),offset,2)
        except ValueError:pass
        else:raise AssertionError('Accepted occupied YES padding')
    for offset in YES_SLOTS:
        assert after[offset:offset+4]==b'YES\0'
    legacy=PopupVM(before);legacy.open_popup();legacy.key(-16)
    assert legacy.get8(0xa1fc)==1 and not legacy.freed
    cancellations=[]
    for selected_row in range(4):
        for choice in (0,1):
            vm=PopupVM(after);vm.set8(0x9c5a,selected_row);vm.open_popup(choice)
            menu=vm.menu();vm.key(-16)
            assert vm.menu()==menu and not vm.events
            assert all(vm.get8(p)==0 for p in (0xa1fc,0xa220,0xa221))
            assert vm.freed==[0x2002200,0x2002300,0x2002500,0x2002600,0x2002400]
            assert all(vm.pointer(p)==0 for p in (0x151292c,0x1512930,0x1512954))
            assert all(vm.pointer(vm.STATE+p)==0 for p in (0xa218,0xa228,0xa230))
            cancellations.append({'system_row':selected_row,'choice':choice,'owned_allocations_freed':5,'underlying_menu_unchanged':True})
    ordinary=[]
    for key in (-7,-6,-5,-4,-3,-2,-1,52,53,54):
        for choice in (0,1):
            a=PopupVM(before);b=PopupVM(after);a.open_popup(choice);b.open_popup(choice)
            a.key(key);b.key(key)
            assert (a.menu(),a.popup(),a.freed,a.events)==(b.menu(),b.popup(),b.freed,b.events),(key,choice)
            ordinary.append({'key':key,'choice':choice})
    vm=PopupVM(after);vm.open_popup();vm.key(-16)
    baseline=PopupVM(before)
    vm.key(-16);baseline.key(-16)
    assert vm.menu()==baseline.menu() and vm.get8(0xa1fc)==0
    assert len(vm.freed)==5 and not vm.events
    # Reopen through the actual system OK handler (UI allocation is modeled).
    vm.set8(0x9c5a,3);vm.key(-5);assert vm.get8(0xa1fc)==1
    vm.events.clear();vm.key(-16)
    assert vm.get8(0xa1fc)==0 and len(vm.freed)==10 and not vm.events
    result={'kind':'actual Thumb system input and popup cleanup; UI creation/free callbacks modeled',
        'legacy_clr_leaves_popup_open_reproduced':True,'clr_cancellation_cases':cancellations,
        'ordinary_key_choice_cases_identical':len(ordinary),'second_clr_matches_original_inactive_behavior':True,
        'reopen_then_cancel_passed':True,'yes_labels':'YES','patch':patch_report,
        'physical_device_tested':False,'publication_status':'local draft; not released','all_checks_passed':True}
    (ROOT/'reports/confirmation-ui-validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
