#!/usr/bin/env python3
"""Rebuild a Heroes Lore 3 APK with translated files overlaid on the game JAR."""

from __future__ import annotations

import argparse
import hashlib
import sys
import tempfile
import zipfile
from io import BytesIO
from pathlib import Path, PurePosixPath

OUTER_ASSET = "assets/hero3_fixed.zip"
SIGNATURE_NAMES = {"MANIFEST.MF"}
SIGNATURE_SUFFIXES = (".SF", ".RSA", ".DSA", ".EC")


def safe_relative(name: str) -> Path:
    relative = PurePosixPath(name)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Unsafe archive path: {name!r}")
    return Path(*relative.parts)


def copy_zip(source: zipfile.ZipFile, target: zipfile.ZipFile,
             replacement: tuple[str, bytes] | None = None,
             skip_apk_signatures: bool = False) -> int:
    replaced = False
    copied = 0
    replacement_name, replacement_data = replacement if replacement else (None, None)
    for info in source.infolist():
        name = info.filename
        upper_name = name.upper()
        if skip_apk_signatures and upper_name.startswith("META-INF/"):
            leaf = upper_name.rsplit("/", 1)[-1]
            if leaf in SIGNATURE_NAMES or leaf.endswith(SIGNATURE_SUFFIXES):
                continue
        if replacement_name == name:
            payload = replacement_data
            replaced = True
        else:
            payload = source.read(name)
        target.writestr(info, payload)
        copied += 1
    if replacement and not replaced:
        raise ValueError(f"Archive is missing replacement entry {replacement_name!r}")
    return copied


def build(apk_path: Path, overlay_root: Path, output_path: Path) -> tuple[int, int]:
    if not apk_path.is_file():
        raise ValueError(f"APK not found: {apk_path}")
    if not overlay_root.is_dir():
        raise ValueError(f"Translation overlay directory not found: {overlay_root}")
    if output_path.resolve() == apk_path.resolve():
        raise ValueError("Output APK must not overwrite the source APK")

    replacements: dict[str, bytes] = {}
    for path in sorted(overlay_root.rglob("*")):
        if path.is_dir():
            continue
        relative = path.relative_to(overlay_root).as_posix()
        safe_relative(relative)
        replacements[relative] = path.read_bytes()
    if not replacements:
        raise ValueError("Translation overlay contains no files")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=output_path.name + ".", suffix=".tmp",
                                     dir=output_path.parent, delete=False) as handle:
        temporary = Path(handle.name)
    try:
        with zipfile.ZipFile(apk_path, "r") as apk:
            nested_data = apk.read(OUTER_ASSET)
        with zipfile.ZipFile(BytesIO(nested_data), "r") as assets:
            jars = [info.filename for info in assets.infolist()
                    if not info.is_dir() and info.filename.lower().endswith(".jar")]
            if len(jars) != 1:
                raise ValueError(f"Expected exactly one game JAR; found {jars}")
            jar_name = jars[0]
            original_jar = assets.read(jar_name)

        jar_buffer = BytesIO()
        with zipfile.ZipFile(BytesIO(original_jar), "r") as original, \
                zipfile.ZipFile(jar_buffer, "w") as rebuilt:
            rebuilt.comment = original.comment
            seen: set[str] = set()
            for info in original.infolist():
                name = info.filename
                if name in replacements:
                    rebuilt.writestr(info, replacements[name])
                    seen.add(name)
                else:
                    rebuilt.writestr(info, original.read(name))
            missing = sorted(set(replacements) - seen)
            if missing:
                raise ValueError("Overlay files are not present in the source JAR: " + ", ".join(missing[:10]))

        nested_buffer = BytesIO()
        with zipfile.ZipFile(BytesIO(nested_data), "r") as assets, \
                zipfile.ZipFile(nested_buffer, "w") as rebuilt_assets:
            rebuilt_assets.comment = assets.comment
            copy_zip(assets, rebuilt_assets, (jar_name, jar_buffer.getvalue()))

        with zipfile.ZipFile(apk_path, "r") as apk, \
                zipfile.ZipFile(temporary, "w") as rebuilt_apk:
            rebuilt_apk.comment = apk.comment
            outer_count = copy_zip(apk, rebuilt_apk,
                                   (OUTER_ASSET, nested_buffer.getvalue()),
                                   skip_apk_signatures=True)
        temporary.replace(output_path)
        return len(replacements), outer_count
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_apk", type=Path)
    parser.add_argument("overlay_root", type=Path,
                        help="compiled resource tree; only files matching JAR paths are replaced")
    parser.add_argument("output_apk", type=Path)
    args = parser.parse_args()
    try:
        replaced, entries = build(args.source_apk, args.overlay_root, args.output_apk)
        print(f"Replaced {replaced} game files; wrote {entries} APK entries to {args.output_apk}")
        print(f"SHA-256: {sha256_file(args.output_apk)}")
        print("APK signatures were removed; align and sign this APK before installing it.")
    except (OSError, zipfile.BadZipFile, KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
