#!/usr/bin/env python3
"""Export and rebuild the confirmed Heroes Lore 3 *_txt string-table format."""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

ENCODING = "cp949"


def parse_string_table(data: bytes, source: str = "<bytes>") -> list[str]:
    if len(data) < 4:
        raise ValueError(f"{source}: file shorter than string-table header")
    declared_size, count = struct.unpack_from("<HH", data)
    if declared_size != len(data):
        raise ValueError(f"{source}: header size {declared_size} does not match file size {len(data)}")
    table_end = 4 + 2 * count
    if table_end > len(data):
        raise ValueError(f"{source}: {count} offsets exceed file boundary")
    offsets = struct.unpack_from(f"<{count}H", data, 4) if count else ()
    if any(offset < table_end or offset >= len(data) for offset in offsets):
        raise ValueError(f"{source}: string offset points outside string-data region")
    strings: list[str] = []
    for index, offset in enumerate(offsets):
        end = data.find(b"\0", offset)
        if end < 0:
            raise ValueError(f"{source}: string {index} has no NUL terminator")
        try:
            strings.append(data[offset:end].decode(ENCODING))
        except UnicodeDecodeError as exc:
            raise ValueError(f"{source}: string {index} is not valid {ENCODING}") from exc
    return strings


def build_string_table(strings: list[str], source: str = "<strings>") -> bytes:
    if len(strings) > 0xFFFF:
        raise ValueError(f"{source}: too many strings for 16-bit count")
    encoded: list[bytes] = []
    for index, value in enumerate(strings):
        if "\0" in value:
            raise ValueError(f"{source}: string {index} contains NUL")
        try:
            encoded.append(value.encode(ENCODING))
        except UnicodeEncodeError as exc:
            raise ValueError(f"{source}: string {index} cannot be encoded as {ENCODING}") from exc
    offset = 4 + 2 * len(encoded)
    offsets: list[int] = []
    body = bytearray()
    for value in encoded:
        if offset > 0xFFFF:
            raise ValueError(f"{source}: translated table exceeds 16-bit offset range")
        offsets.append(offset)
        body.extend(value)
        body.append(0)
        offset += len(value) + 1
    if offset > 0xFFFF:
        raise ValueError(f"{source}: translated table exceeds 65,535-byte format limit")
    return struct.pack("<HH", offset, len(encoded)) + struct.pack(f"<{len(offsets)}H", *offsets) + body


def extract_catalog(resource_root: Path) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    for path in sorted(resource_root.rglob("*_txt")):
        relative = path.relative_to(resource_root).as_posix()
        for index, source in enumerate(parse_string_table(path.read_bytes(), relative)):
            rows.append({"id": f"{relative}#{index}", "file": relative, "index": index,
                         "source": source, "translation": ""})
    return {"format": "heroes-lore-3-text-table-v1", "encoding": ENCODING, "entries": rows}


def compile_catalog(resource_root: Path, catalog_path: Path, output_root: Path) -> int:
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    if catalog.get("format") != "heroes-lore-3-text-table-v1":
        raise ValueError("Unsupported catalog format")
    by_file: dict[str, dict[int, dict[str, object]]] = {}
    for entry in catalog.get("entries", []):
        relative = str(entry["file"])
        index = int(entry["index"])
        if Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise ValueError(f"Unsafe catalog path: {relative!r}")
        if index in by_file.setdefault(relative, {}):
            raise ValueError(f"Duplicate translation slot: {relative}#{index}")
        by_file[relative][index] = entry
    written = 0
    for relative, translations in by_file.items():
        original_path = resource_root / Path(relative)
        original = parse_string_table(original_path.read_bytes(), relative)
        if set(translations) != set(range(len(original))):
            raise ValueError(f"{relative}: catalog slots do not match source string count")
        rebuilt = []
        for index, source in enumerate(original):
            entry = translations[index]
            if entry.get("source") != source:
                raise ValueError(f"{relative}#{index}: source text differs from extracted resource")
            # Empty catalog values mean "retain the source". This is needed
            # for the original English headings and menu labels.
            translated = str(entry.get("translation") or source)
            rebuilt.append(translated)
        target = output_root / Path(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(build_string_table(rebuilt, relative))
        written += 1
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    export = sub.add_parser("extract", help="export *_txt files to a JSON catalog")
    export.add_argument("resource_root", type=Path)
    export.add_argument("output", type=Path)
    compile_cmd = sub.add_parser("compile", help="compile translated tables into a clean output tree")
    compile_cmd.add_argument("resource_root", type=Path)
    compile_cmd.add_argument("catalog", type=Path)
    compile_cmd.add_argument("output_root", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "extract":
            catalog = extract_catalog(args.resource_root)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"Exported {len(catalog['entries'])} string slots to {args.output}")
        else:
            count = compile_catalog(args.resource_root, args.catalog, args.output_root)
            print(f"Compiled {count} translated string tables into {args.output_root}")
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
