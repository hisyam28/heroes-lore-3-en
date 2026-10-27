# English localization v1.1.5 — 2026-10-27

Download the signed APK from [GitHub Releases](https://github.com/hisyam28/heroes-lore-3-en/releases/latest).

Version v1.1.5 includes the [title composition correction](title-seam-review.md).
Five connected crest pieces are sampled from one full-scene artwork, aligning
the wordmark with the adjoining Roman III. Only the title bitmap differs
from v1.1.4; game bytecode, native code and controls remain identical.
See the [v1.1.5 metadata](release-v1.1.5.json) and
[composition preview](title-composition-preview.png).

Version v1.1.4 includes the [system popup and artwork fixes](system-title-icon-draft.md)
and [enemy-level spacing correction](enemy-level-spacing-draft.md). CLR now
cleans up the active system confirmation before returning to the menu;
confirmation labels read `YES`. The title tile blends the English wordmark
with its ornament and uses `STIGMATA OF EARTH`. The revised launcher icon
is included. Touchpoint configuration and key mapping remain unchanged.

The signed APK passed resource, ARM regression, signature, and alignment
checks. Automated checks model some platform callbacks and do not replace
physical-device testing. The following sections retain details from
v1.1.3 and earlier updates; linked validation reports describe the current build.

This update fits the save notification to its visible text and reduces enemy
level digits from 5x7 to a dedicated 3x5 design. Both enemy HUD paths use the
compact digits, aligned with the original five-pixel `LV` label. General font
bitmaps and ordinary font modes retain their output. The HUD helpers occupy
64 guarded bytes in existing string padding; module size stays the same and
drawing performs no heap allocation.

The native `SAVED.` string previously included six trailing storage-padding
spaces in its visible slice. Its length is now six bytes, so the notification
layout receives only the visible text. `SAVE FAILED.` keeps its full length.
Notification timing, save operations, touchpoint configuration, and analog/key
mapping are unchanged.

Validation executes both actual Thumb HUD call sites for 520 combinations of
levels and viewport widths, including levels 1 through 127, 200, 255, and 999.
All level pixels remain inside the original frame without touching the HP bar.
348 ordinary glyph/mode cases remain pixel-identical, and actual AArch64 slice
construction yields `SAVED.` without trailing spaces. Allocator/platform calls
are modeled; final appearance still needs physical-device checking. Sampled
ordinary-font instruction counts do not increase, and all four graphics
accelerators remain enabled after rekeying the updated module.
See [HUD/save validation](hud-save-layout-validation.json),
[the modeled frame preview](enemy-level-preview.png), and
[scope compared with v1.1.2](hud-save-update-scope.json).

The preceding update guarded confirmation-popup touch ownership, replaced the Android
launcher icon with the supplied artwork, and revised the home wordmark to
`STIGMATA OF EARTH`. The wordmark no longer adds a second Roman III over the
existing background emblem. Previous translation and acceleration fixes remain.

The existing native detector could recognize a confirmation panel yet return
an unowned result when a tap missed its choices. That tap could then reach a
menu underneath the popup. A guarded 60-byte native patch consumes that case
and clears ownership on release. Touchpoint configuration, analog/key mapping,
and detector geometry remain unchanged. The guard covers panels already
recognized by the existing detector; it does not expand detection to every popup.

An isolated replay executes the actual AArch64 detector and pointer lifecycle:
10 modal cases, 3 ordinary/outside cases, and 3 down/move/up lifecycles. It
reproduces the old leak and verifies that consumed taps dispatch no guest event
and leave no pointer ownership behind. Frames and allocator/library calls are
modeled; this is not an Android event-loop or physical-device test. The reported
pause > system > main-menu sequence still needs device retesting.
See [modal validation](modal-input-validation.json) and
[the update scope compared with v1.1.1](branding-input-update-scope.json).

All 20 launcher bitmap variants are replaced without changing adaptive XML or
resource IDs. The supplied icon is resized, not redrawn. The title stays within
the original 146x60 sprite and palette capacity; the other 16 title sprites are
identical. See [icon preview](android-icon-preview.png),
[icon validation](android-icon-validation.json), and
[title validation](title-localization.json). The built-in imagegen title edit is
saved as [source artwork](../translations/art/title-logo-source.png) and the
[compiled sprite](../translations/art/title-logo-146x60.png), with its
[exact prompt](../translations/art/title-logo-prompt.txt).

The preceding update translated 41 native settings strings, centered the
character-save rows, and shortened `NETWORK STORAGE` to `NET STORE`.

The actual ARM slot-row routine was exercised for slots 1–3, selected and
unselected. Number/frame and row centering errors are at most 0.5 pixel.
Only four guarded layout instructions change; save data and row selection
behavior are untouched. Native settings translation alone retains its byte
capacities and addresses without changing executable sections. This release
separately applies the narrowly scoped native modal guard described above.
See [home UI validation](home-ui-validation.json) and
[the slot comparison](home-slot-preview.png), which is modeled renderer output,
not a device screenshot.

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
