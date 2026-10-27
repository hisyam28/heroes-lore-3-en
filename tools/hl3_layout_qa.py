#!/usr/bin/env python3
"""Check narrow panels using the game's real font functions in the ARM probe."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from hl3_probe_font import FontVM
from hl3_font_runtime import build_font,patch_metrics
from hl3_markup import latin_copy
from hl3_item_descriptions import COPY,wrap
from hl3_enemy_text import NAMES
from hl3_skill_text import DESCRIPTIONS

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'work/analysis-deps'))
from PIL import Image,ImageDraw


def main():
    module=(ROOT/'work/original/binary.mod').read_bytes();font=build_font()
    vm=FontVM(patch_metrics(module),font,font)
    entries=json.loads((ROOT/'translations/catalog.json').read_text(encoding='utf-8'))['entries']
    byid={e['id']:e['translation'] or e['source'] for e in entries}
    checks=[]
    for e in entries:
        if e['file']=='res/menu/countrybody_txt':width,height=108,103
        elif e['file']=='res/menu/chatacterbody_txt':width,height=168,44
        else:continue
        text=e['translation'] or e['source'];widths=[vm.width(line) for line in text.split(';')]
        pixels=vm.draw(text,width=width)
        ink_height=max((y for x,y in pixels),default=-1)+1
        check={'id':e['id'],'width_budget':width,'line_widths':widths,'height_budget':height,
               'rendered_ink_height':ink_height,'fits':max(widths)<=width and ink_height<=height}
        checks.append(check)
        assert check['fits'],check
    items=json.loads((ROOT/'translations/item-catalog.json').read_text(encoding='utf-8'))['entries']
    item_widths=[vm.width((e.get('marker') or '')+e['translation']) for e in items]
    assert max(item_widths)<=133
    assert byid['res/dat/InGame_txt#17']=='NM' and byid['res/dat/InGame_txt#18']=='EFC'
    assert byid['res/dat/InGame_txt#19']=='OTHR'
    description_checks=[]
    for table,values in COPY.items():
        for i,value in enumerate(values):
            value=wrap(value);widths=[vm.width(line) for line in value.split(';')]
            pixels=vm.draw(value,width=133);height=max((y for x,y in pixels),default=-1)+1
            assert max(widths)<=133 and height<=29,(table,i,value,widths,height)
            description_checks.append({'table':table,'record':i,'width':max(widths),'ink_height':height})
    for table,values in DESCRIPTIONS.items():
        for i,value in enumerate(values):
            value=wrap(value);widths=[vm.width(line) for line in value.split(';')]
            pixels=vm.draw(value,width=133);height=max((y for x,y in pixels),default=-1)+1
            assert max(widths)<=133 and height<=33,(table,i,value,widths,height)
    assert max(vm.width(n) for n in NAMES)<=73
    # This is a font/layout proof, deliberately labelled as such, not a device screenshot.
    sheet=Image.new('RGB',(720,230),(25,25,28));draw=ImageDraw.Draw(sheet)
    def text(value,x,y,width=1000,color=(255,242,180)):
        for px,py in vm.draw(value,width=width):
            if 0<=x+px<sheet.width and 0<=y+py<sheet.height:sheet.putpixel((x+px,y+py),color)
    panels=[(0,'COUNTRY / 108 PX'),(240,'CLASS / 168 PX'),(480,'ITEM DETAIL')]
    for x,label in panels:
        draw.rectangle((x+5,6,x+234,207),fill=(75,47,30),outline=(220,205,166))
        draw.text((x+12,13),label,fill='white')
    text('NEO SOLTIA',52,40)
    draw.rectangle((18,66,77,167),outline=(120,100,80));draw.text((27,106),'PORTRAIT',fill=(150,130,100))
    text(byid['res/menu/countrybody_txt#0'],95,65,width=108)
    text('GUARDIAN KNIGHT',282,40)
    draw.rectangle((260,66,460,119),outline=(120,100,80));draw.text((306,87),'CLASS ART',fill=(150,130,100))
    text(byid['res/menu/chatacterbody_txt#3'],260,131,width=168)
    text('MAIN   SUB',315,188)
    text('ITEMS',560,40)
    text('NM',492,90);text('HAND KNIFE',530,90)
    text('EFC',492,114);text('LV1 DAGGER / AT7',530,114)
    text('NM',492,145);text('REINF LTHR ARMR',530,145)
    text('QUIT GAME?  Y / NO',492,183)
    draw.text((12,216),'ACTUAL ARM FONT OUTPUT / LAYOUT MODEL - NOT A DEVICE SCREENSHOT',fill=(200,200,200))
    sheet.resize((1440,460),Image.Resampling.NEAREST).save(ROOT/'reports/ui-layout-preview.png')
    # Reported screens in this update, using the same real ARM font renderer.
    sheet=Image.new('RGB',(720,230),(25,25,28));draw=ImageDraw.Draw(sheet)
    for x,label in [(0,'ENEMY / SAVE'),(240,'ITEM DETAILS'),(480,'SKILL DETAILS')]:
        draw.rectangle((x+5,6,x+234,207),fill=(75,47,30),outline=(220,205,166))
        draw.text((x+12,13),label,fill='white')
    text('SCORPION',28,48);text('LV2',28,67)
    draw.rectangle((28,80,150,84),fill=(210,45,45))
    text('HENGE',28,106);text('LV1',28,125);text('SAVED.',28,170)
    text('NM',250,45);text('POTION',285,45)
    text('EFC',250,62);text('RESTORE 200 HP.',285,62,width=133)
    text('NM',250,100);text('FRUIT JUICE',285,100)
    text('EFC',250,117);text('RESTORE 20% SP.',285,117,width=133)
    text('NM',250,155);text('RED SOLUTION',285,155)
    text('EFC',250,172);text(wrap(COPY['i14_dat'][0]),285,172,width=133)
    text('NM',490,45);text('SHOT',530,45)
    text('EFC',490,70);text(wrap(DESCRIPTIONS['s7_dat'][0]),530,70,width=133)
    text('OTHR',490,116);text('COMBO: 0',530,116)
    draw.text((12,216),'ACTUAL ARM FONT OUTPUT / LAYOUT MODEL - NOT A DEVICE SCREENSHOT',fill=(200,200,200))
    sheet.resize((1440,460),Image.Resampling.NEAREST).save(ROOT/'reports/remaining-ui-preview.png')
    result={'kind':'isolated game-font execution; panel budgets inferred from supplied screenshots',
            'panels':checks,'item_names_checked':len(items),'max_item_width':max(item_widths),
            'detail_caption_widths':{'NM':vm.width('NM'),'EFC':vm.width('EFC')},
            'item_description_checks':description_checks,'skill_descriptions_checked':63,
            'enemy_names_checked':len(NAMES),'max_enemy_name_width':max(vm.width(n) for n in NAMES),
            'all_panels_fit':True}
    (ROOT/'reports/ui-layout-validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(f'All 12 country/class panels fit. {len(items)} item names fit; widest = {max(item_widths)} px. NM/EFC checked.')
    print('145 item descriptions, 63 skill descriptions and 161 enemy names fit the modeled screenshot budgets.')


if __name__=='__main__':main()
