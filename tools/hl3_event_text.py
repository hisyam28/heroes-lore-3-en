#!/usr/bin/env python3
"""Extract and compile CP949 NUL-delimited text embedded in HL3 event scripts."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path, PurePosixPath

from hl3_locations import normalize_entry
from hl3_markup import MARKUP

ENCODING = "cp949"
HANGUL = re.compile(r"[가-힣]")


def safe_relative(name: str) -> Path:
    relative = PurePosixPath(name)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Unsafe path: {name!r}")
    return Path(*relative.parts)


def extract_file(path: Path, relative: str) -> list[dict[str, object]]:
    rows = []
    for segment, raw in enumerate(path.read_bytes().split(b"\0")):
        prefix = b""
        try:
            source = raw.decode(ENCODING)
        except UnicodeDecodeError:
            source = ""
        if any(unicodedata.category(char).startswith("C") for char in source):
            source = ""
        count = len(HANGUL.findall(source))
        if count < 1:
            source = ""
        if not source:
            # Some script records prefix visible location names with opcode bytes.
            # Preserve that prefix and expose only a clean CP949 text suffix.
            for start in range(1, len(raw)):
                if raw[start - 1] >= 0x20 and raw[start - 1] != 0x7F:
                    continue
                try:
                    candidate = raw[start:].decode(ENCODING)
                except UnicodeDecodeError:
                    continue
                if any(unicodedata.category(char).startswith("C") for char in candidate):
                    continue
                count = len(HANGUL.findall(candidate))
                if count >= 1 and len(candidate) >= 3 and count / len(candidate) >= 0.18:
                    prefix, source = raw[:start], candidate
                    break
        if not source:
            continue
        row = {"id": f"{relative}#{segment}", "file": relative,
                     "segment": segment, "prefix_hex": prefix.hex(),
                     "source": source, "translation": ""}
        normalize_entry(row)
        row['translation'] = ''
        rows.append(row)
    return rows


def extract_catalog(resource_root: Path, selected: str | None = None) -> dict[str, object]:
    if selected:
        relative = selected.replace("\\", "/")
        path = resource_root / safe_relative(relative)
        if not path.is_file():
            raise ValueError(f"Event file not found: {relative}")
        paths = [(path, relative)]
    else:
        paths = [(path, path.relative_to(resource_root).as_posix())
                 for path in sorted(resource_root.rglob("*_scn"))]
    entries = [entry for path, relative in paths for entry in extract_file(path, relative)]
    return {"format": "heroes-lore-3-event-text-v1", "encoding": ENCODING,
            "replacement": "same-byte-length; ASCII spaces pad shorter English strings",
            "entries": entries}


def compile_catalog(resource_root: Path, catalog_path: Path, output_root: Path,
                   fit_only: bool = False) -> tuple[int, int]:
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    if catalog.get("format") != "heroes-lore-3-event-text-v1":
        raise ValueError("Unsupported event catalog format")
    by_file: dict[str, dict[int, dict[str, object]]] = {}
    for entry in catalog.get("entries", []):
        relative = str(entry["file"])
        safe_relative(relative)
        segment = int(entry["segment"])
        if segment in by_file.setdefault(relative, {}):
            raise ValueError(f"Duplicate event string: {relative}#{segment}")
        by_file[relative][segment] = entry

    written = 0
    skipped = 0
    for relative, entries in by_file.items():
        source_path = resource_root / safe_relative(relative)
        parts = source_path.read_bytes().split(b"\0")
        for segment, entry in entries.items():
            translation = str(entry.get("translation") or "")
            if not translation:
                continue
            if segment < 0 or segment >= len(parts):
                raise ValueError(f"{relative}#{segment}: segment is outside the source file")
            raw = parts[segment]
            try:
                prefix = bytes.fromhex(str(entry.get("prefix_hex") or ""))
                if not raw.startswith(prefix):
                    raise ValueError("stored byte prefix differs from source")
                source = raw[len(prefix):].decode(ENCODING)
                encoded = translation.encode(ENCODING)
            except UnicodeError as exc:
                raise ValueError(f"{relative}#{segment}: text is not valid CP949") from exc
            if source != entry.get("source"):
                raise ValueError(f"{relative}#{segment}: source does not match the original script")
            for marker in MARKUP:
                if source.count(marker) != translation.count(marker):
                    if fit_only:
                        skipped += 1
                        encoded = b""
                        break
                    raise ValueError(f"{relative}#{segment}: markup marker {marker!r} changed")
            if not encoded:
                continue
            if ''.join(c for c in source if c in MARKUP) != ''.join(c for c in translation if c in MARKUP):
                if fit_only:
                    skipped += 1
                    continue
                raise ValueError(f"{relative}#{segment}: markup marker order changed")
            if b'\0' in encoded:
                raise ValueError(f"{relative}#{segment}: embedded NUL in translated event")
            field_size = len(raw) - len(prefix)
            if len(encoded) > field_size:
                if fit_only:
                    skipped += 1
                    continue
                raise ValueError(f"{relative}#{segment}: translation exceeds the {field_size}-byte field")
            parts[segment] = prefix + encoded + b" " * (field_size - len(encoded))
            written += 1
        target = output_root / safe_relative(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"\0".join(parts))
    return written, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    export = sub.add_parser("extract", help="export likely CP949 script strings")
    export.add_argument("resource_root", type=Path)
    export.add_argument("output", type=Path)
    export.add_argument("--file", help="limit extraction to a resource-relative script path")
    compile_cmd = sub.add_parser("compile", help="patch translations without shifting script bytes")
    compile_cmd.add_argument("resource_root", type=Path)
    compile_cmd.add_argument("catalog", type=Path)
    compile_cmd.add_argument("output_root", type=Path)
    compile_cmd.add_argument("--fit-only", action="store_true",
                             help="compile only translations that fit and preserve all markup")
    args = parser.parse_args()
    try:
        if args.command == "extract":
            catalog = extract_catalog(args.resource_root, args.file)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
                                   encoding="utf-8")
            print(f"Exported {len(catalog['entries'])} candidate strings to {args.output}")
        else:
            count, skipped = compile_catalog(args.resource_root, args.catalog, args.output_root,
                                             fit_only=args.fit_only)
            print(f"Compiled {count} event strings into {args.output_root}; skipped {skipped} fields")
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
