# System popup and artwork - unreleased development changes

The source changes are tracked on the main branch for review. The APK remains
local and retains the preceding enemy-level spacing fix. No new version, tag,
or release is published for these changes.

The active system-popup handler previously ignored CLR. CLR now enters the
existing popup cleanup before the row-selection check, releases owned UI
allocations, clears popup flags and leaves the underlying menu alone. A second
CLR follows the original inactive-menu behavior. Input mapping and touchpoint
coordinates are unchanged. The preceding native modal-miss guard remains.
The exit and related confirmation labels now read `YES`, using guarded spare
bytes without relocating strings or following data.

[Confirmation validation](confirmation-ui-validation.json) executes the actual
Thumb system input handler and cleanup. It reproduces the previous CLR issue,
checks both choices across four system rows, verifies five owned allocations
are released, checks a second CLR and reopen/cancel, and compares 20 ordinary
key/choice cases. UI creation and free callbacks are modeled; this is not a
physical-device test.

The title sprite is an opaque tile of the original ornament. A transparent
wordmark left blank rectangular regions when this tile was drawn. The new
146x60 replacement includes the crest behind and between the English letters,
keeps the subtitle `STIGMATA OF EARTH`, and has no transparent/flat-black margin.
Its original RGB565 palette is reused to match the adjoining ornament colors.
The neighboring 16 sprites keep their original bytes. Visual alignment with
the animated title background still needs checking on a device.

The title was edited using built-in imagegen. Saved assets:
[source](../translations/art/title-logo-source.png),
[compiled sprite](../translations/art/title-logo-146x60.png), and
[exact prompt](../translations/art/title-logo-prompt.txt).
[Title preview](title-tile-preview.png) is the compiled tile enlarged for review.

The launcher uses the revised square artwork supplied by the project owner,
with its textured background and no added white border. It is resized into
the existing resource slots; adaptive XML and resource IDs stay unchanged.
See [icon preview](android-icon-preview.png) and
[source](../translations/art/android-icon-source.png).
