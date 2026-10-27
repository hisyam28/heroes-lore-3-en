#!/usr/bin/env python3
"""Inventory or extract the nested Heroes Lore 3 game assets from an APK."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path, PurePosixPath

OUTER_ASSET = "assets/hero3_fixed.zip"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_game_jar(apk: zipfile.ZipFile) -> tuple[bytes, str]:
    try:
        nested = apk.read(OUTER_ASSET)
    except KeyError as exc:
        raise ValueError(f"APK is missing {OUTER_ASSET}") from exc
    from io import BytesIO

    with zipfile.ZipFile(BytesIO(nested)) as assets:
        jars = [name for name in assets.namelist() if name.lower().endswith(".jar")]
        if len(jars) != 1:
            raise ValueError(f"Expected exactly one game JAR in {OUTER_ASSET}; found {jars}")
        return assets.read(jars[0]), jars[0]


def list_entries(jar_bytes: bytes) -> list[dict[str, object]]:
    from io import BytesIO

    with zipfile.ZipFile(BytesIO(jar_bytes)) as jar:
        rows = []
        for item in jar.infolist():
            if item.is_dir():
                continue
            rows.append({
                "path": item.filename,
                "size": item.file_size,
                "compressed_size": item.compress_size,
                "crc32": f"{item.CRC:08x}",
            })
        return rows


def extract(jar_bytes: bytes, destination: Path) -> int:
    from io import BytesIO

    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    written = 0
    with zipfile.ZipFile(BytesIO(jar_bytes)) as jar:
        for item in jar.infolist():
            if item.is_dir():
                continue
            relative = PurePosixPath(item.filename)
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"Unsafe path inside game JAR: {item.filename!r}")
            target = (root / Path(*relative.parts)).resolve()
            if target != root and root not in target.parents:
                raise ValueError(f"Unsafe extraction path: {item.filename!r}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with jar.open(item) as source, target.open("wb") as sink:
                shutil.copyfileobj(source, sink)
            written += 1
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    inventory = sub.add_parser("inventory", help="write a JSON inventory of the nested game JAR")
    inventory.add_argument("apk", type=Path)
    inventory.add_argument("--output", type=Path, default=Path("work/inventory.json"))
    unpack = sub.add_parser("extract", help="extract nested game JAR resources")
    unpack.add_argument("apk", type=Path)
    unpack.add_argument("destination", type=Path)
    args = parser.parse_args()

    if not args.apk.is_file():
        parser.error(f"APK not found: {args.apk}")
    try:
        with zipfile.ZipFile(args.apk) as apk:
            jar_bytes, jar_name = find_game_jar(apk)
        if args.command == "inventory":
            rows = list_entries(jar_bytes)
            payload = {
                "source_apk": args.apk.name,
                "source_sha256": sha256_file(args.apk),
                "nested_asset": OUTER_ASSET,
                "game_jar": jar_name,
                "entry_count": len(rows),
                "uncompressed_bytes": sum(int(row["size"]) for row in rows),
                "entries": rows,
            }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"Wrote {len(rows)} entries to {args.output}")
        else:
            count = extract(jar_bytes, args.destination)
            print(f"Extracted {count} files from {jar_name} to {args.destination}")
    except (OSError, zipfile.BadZipFile, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
