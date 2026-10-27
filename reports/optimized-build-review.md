# English localization v1.1.0 — 2026-10-27

Download the signed APK from [GitHub Releases](https://github.com/hisyam28/heroes-lore-3-en/releases/latest).

This update addresses the remaining Korean enemy names, native save
notifications, item descriptions, and the invalid number in skill details.

| Area | Coverage |
| --- | --- |
| Enemy names | 161 records in each normal/hard table, 322 total |
| Item descriptions | 145 descriptions across cards, materials, orbs, quest items, consumables |
| Item names | 628 names in 18 tables |
| Skill text | 105 records, 163 translated fields |
| UI | 278 table slots and 149 module labels |
| Quests and characters | 154 quest records and 16 character records |
| Events | 4,767 text fields, with original slot sizes and control sequences retained |
| Save feedback | English success/failure notifications |

`OTHER` is now `OTHR`. The long integer in the reported screenshot was a
formatting bug: a shared string suffix moved when a containing label was
shortened, so a text pointer was interpreted as an integer. The suffix is now
preserved and guarded. Actual combo, cooldown, and duration values remain numeric.

Item descriptions are wrapped by words and checked against a two-line panel
budget. Skill descriptions and enemy names are also checked with the game's
ARM font functions. Labels such as `SCORPION`, `HENGE`, `RESTORE 200 HP.`, and
`RESTORE 20% SP.` replace the reported Korean text.

The previous graphics acceleration fix is retained, along with the 5x7 Latin
font, 6px cell advance, 1px letter gap and 11px line height. Changes to text
preserve item effect data, enemy combat metadata, skill metadata, and script
control bytes.

The final APK passed archive/resource validation, APK Signature Scheme v2/v3,
signer comparison with the previous build, and 16 KB native library alignment.
See [artifact validation](optimized-build-validation.json),
[layout validation](ui-layout-validation.json), and the
[modeled layout preview for this update](remaining-ui-preview.png).

These checks do not establish device FPS or a full playthrough. The layout proof
is modeled renderer output, not a device screenshot. Unconfirmed binary formats
are left untouched, and undiscovered text or artwork may remain untranslated.

The repository now keeps the active tooling and concise documentation; obsolete
experiments and local reports are excluded from publication. Workflow reference:
[sanixmon/heroes-lore-5-en](https://github.com/sanixmon/heroes-lore-5-en).
