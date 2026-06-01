#!/usr/bin/env python3
"""List code files that are missing a standard header comment."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path


LINE_COMMENT_EXTS = {
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".go",
    ".rs",
    ".java",
    ".cs",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".kt",
}
HASH_COMMENT_EXTS = {".py"}
MD_COMMENT_EXTS = {".md", ".mdx"}
SUPPORTED_EXTS = LINE_COMMENT_EXTS | HASH_COMMENT_EXTS | MD_COMMENT_EXTS
SOURCE_EXTS = SUPPORTED_EXTS - MD_COMMENT_EXTS
SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "bower_components",
    "dist",
    "build",
    "coverage",
    ".next",
    ".nuxt",
    "out",
    "target",
    "bin",
    "obj",
}
HEADER_MARKERS = ("@purpose", "文件作用")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List code files missing standard headers.")
    parser.add_argument("root", nargs="?", default=".", help="Project root. Defaults to current directory.")
    parser.add_argument(
        "paths",
        nargs="*",
        help="Optional files or directories relative to root. Defaults to all supported source files.",
    )
    parser.add_argument("--include-md", action="store_true", help="Also report .md and .mdx files.")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON.")
    return parser.parse_args()


def read_text(path: Path) -> str | None:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return None


def has_standard_marker(text: str) -> bool:
    top = "\n".join(text.splitlines()[:40])
    return any(marker in top for marker in HEADER_MARKERS)


def first_meaningful_line(lines: list[str]) -> str:
    for line in lines:
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def has_existing_header_comment(path: Path, text: str) -> bool:
    lines = text.splitlines()
    index = 0
    if lines and lines[0].startswith("#!"):
        index = 1
    if path.suffix.lower() == ".py" and len(lines) > index:
        encoding_re = re.compile(r"^#.*coding[:=]\s*[-\w.]+")
        if encoding_re.match(lines[index]):
            index += 1
    first = first_meaningful_line(lines[index : index + 8])
    if first.startswith(("//", "/*", "<!--")):
        return True
    if path.suffix.lower() in HASH_COMMENT_EXTS and first.startswith("#"):
        return True
    return False


def iter_files(root: Path, selected: list[str], include_md: bool) -> list[Path]:
    allowed = SUPPORTED_EXTS if include_md else SOURCE_EXTS
    starts = [root / item for item in selected] if selected else [root]
    files: list[Path] = []
    for start in starts:
        start = start.resolve()
        if start.is_file() and start.suffix.lower() in allowed:
            files.append(start)
            continue
        if not start.is_dir():
            continue
        for current, dir_names, file_names in os.walk(start):
            dir_names[:] = [name for name in dir_names if name not in SKIP_DIRS and not name.startswith(".")]
            for file_name in file_names:
                path = Path(current) / file_name
                if path.suffix.lower() in allowed:
                    files.append(path)
    return sorted(set(files), key=lambda item: item.as_posix().lower())


def is_missing_header(path: Path, text: str) -> bool:
    return not has_standard_marker(text) and not has_existing_header_comment(path, text)


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"Project root is not a directory: {root}")

    missing: list[Path] = []
    skipped_unreadable = 0
    for path in iter_files(root, args.paths, args.include_md):
        text = read_text(path)
        if text is None:
            skipped_unreadable += 1
            continue
        if is_missing_header(path, text):
            missing.append(path)

    if args.json:
        payload = {
            "root": str(root),
            "missing": [path.relative_to(root).as_posix() for path in missing],
            "count": len(missing),
            "skipped_unreadable": skipped_unreadable,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for path in missing:
            print(path.relative_to(root).as_posix())
        print(
            f"Summary: {len(missing)} files missing standard headers; "
            f"{skipped_unreadable} unreadable files skipped."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
