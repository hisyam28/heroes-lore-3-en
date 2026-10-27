# Home title composition correction

Included in [v1.1.5](https://github.com/hisyam28/heroes-lore-3-en/releases/tag/v1.1.5).

The previous replacement redrew only the center rectangle. Its ornament was
scaled independently of the surrounding Roman III, producing visible joins.
The correction samples all five connected crest pieces from one full-scene
artwork. HEROES, LORE and STIGMATA OF EARTH are centered within the crest.

The compiler reads the existing CIF placements and samples the original-size
pieces from one 280x180 canvas. Each piece retains its original palette, pixel
format, dimensions and byte length. Animation and drawing coordinates stay
unchanged. Twelve other title sprites retain their exact bytes.

[Composition preview](title-composition-preview.png) renders the static frame
from the actual compiled sprites and original CIF placements. It omits the
two scaled transition-effect instances and is not a device screenshot.

The artwork was edited with built-in imagegen:
[full-scene source](../translations/art/title-logo-source.png),
[central compiled tile](../translations/art/title-logo-146x60.png), and
[exact edit and refinement prompts](../translations/art/title-logo-prompt.txt).
The full-scene source is used only during compilation, not as an additional
runtime background texture.

[Artifact comparison](title-seam-validation.json) confirms that only the title
bitmap resource differs from v1.1.4; the other 1273 game resources and all
other APK entry contents match. Game bytecode, native code, font metrics,
launcher icons and input configuration remain identical. Strict resource
validation, 16 KB alignment, v2/v3 signatures and the previous signing
certificate were checked. Final appearance still requires device review.

Release APK: `heroes-lore-3-en-v1.1.5.apk`.
SHA-256: `a6d381da27ed58aa5a4ca2710400a0b314a8a76679aa33990eebd11ea521ed09`.
