# Development

The repository contains translation catalogs, resource parsers, curated copy,
bitmap/font tooling, and validation scripts. Local build inputs and temporary
analysis data are excluded from Git.

```text
tools/         Current compiler, renderer checks, and build script
translations/ Reviewed catalogs, compact copy, and localized title art
reports/       Resource inventory, layout proof, and validation results
docs/          Development notes
```

The build requires compatible local inputs, a configured Android toolchain,
Python, and the dependencies below. It is a local workflow; cloning the
repository alone does not provide the build inputs.

```powershell
python -m pip install --target work/analysis-deps -r tools/analysis-requirements.txt
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools/build_optimized.ps1
```

Copy definitions are maintained in the curator modules. The build regenerates
their catalogs, compiles an overlay, checks the font/layout and resource
invariants, then aligns, signs, and verifies the APK. Overflow is rejected for
explicit rewriting; event clauses are not automatically dropped.

Confirmed formats include offset-based string tables, interleaved event text,
length-prefixed records, item description fields after price data, and skill
records with a fixed metadata tail. Text changes must preserve control sequences
and metadata. Module strings can have independently referenced suffixes; these
aliases must retain their original positions.

The isolated ARM renderer checks real font functions against modeled panel
budgets. It does not replace full device testing or measure Android FPS.

The modal-input regression replays the actual AArch64 detector and pointer
ownership lifecycle with synthetic native-color frames. The guard applies only
after the existing detector recognizes a confirmation panel. It consumes taps
that miss the choices and clears their ownership on release. Touchpoint
coordinates, analog/key mapping, and modal detection geometry are retained.
Allocator and library calls are modeled; Android event delivery and a physical
device are outside this check.

Launcher artwork is compiled from the supplied PNG into the existing density
slots. The title wordmark is quantized into the original sprite dimensions and
palette capacity; its other sprites remain byte-identical.

The enemy-level check executes both actual HUD call sites with compact numeric
glyphs, preserving the general font modes. It checks the original frame and HP
bar bounds at two viewport widths. The save check executes the native string
slice construction and rejects storage-padding spaces in the visible message.
The helpers use guarded padding after complete localized C strings, retaining
their first terminators and rejecting independently referenced padding.

Older experiments and local investigation notes were archived outside the public
source tree. Current build scripts do not depend on those archived experiments.
