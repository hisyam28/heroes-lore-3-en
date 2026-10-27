# Enemy level spacing - v1.1.4

This correction is included in [v1.1.4](https://github.com/hisyam28/heroes-lore-3-en/releases/tag/v1.1.4).
The separate spacing-only draft report records the intermediate validation build.

The released layout placed the first digit too close to the original `LV`
artwork and retained a six-pixel cursor advance for three-pixel digits. The
correction keeps at least three empty pixels after `LV`, uses a four-pixel numeric
advance with one empty pixel between digits, and leaves at least one empty
pixel before the HP bar even for a three-digit level. The five-pixel digit
height and baseline match the original `LV` artwork.

The private single-line HUD drawing path applies this spacing to both enemy
panels. General fonts, line wrapping, touchpoint settings, and analog/key
mapping retain their behavior. The renderer uses no per-draw heap allocation.

See [the comparison](enemy-level-preview.png) and
[the actual ARM validation](hud-save-layout-validation.json). Validation checks
individual digit pixels, repeated/multiple digits, the complete `LV` artwork,
frame and HP-bar clearance, two viewport widths, ordinary font output, and
save feedback. The preview uses actual executed font pixels and modeled frame
composition; physical-device appearance still needs checking.
