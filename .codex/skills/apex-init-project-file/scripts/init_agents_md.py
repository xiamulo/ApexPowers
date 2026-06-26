#!/usr/bin/env python3
"""List project folders that should receive FOLDER.md attention."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List folders needing FOLDER.md work.")
    parser.add_argument(
        "root",
        nargs="?",
        default=".",
        help="Existing project root to scan. Defaults to the current directory.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON.",
    )
    parser.add_argument(
        "--all",
        "--force",
        "--regenerate",
        action="store_true",
        dest="include_existing",
        help="List all eligible folders, including folders that already have FOLDER.md.",
    )
    return parser.parse_args()


def has_folder_file(directory: Path) -> bool:
    return any(child.is_file() and child.name.lower() == "folder.md" for child in directory.iterdir())


def iter_target_dirs(root: Path, include_existing: bool) -> list[Path]:
    targets: list[Path] = []
    for current, dir_names, _ in os.walk(root):
        dir_names[:] = [name for name in dir_names if name not in SKIP_DIRS and not name.startswith(".")]
        current_path = Path(current)
        if current_path == root:
            continue
        if include_existing or not has_folder_file(current_path):
            targets.append(current_path)
    return sorted(targets, key=lambda item: item.relative_to(root).as_posix().lower())


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"Project root is not a directory: {root}")

    targets = iter_target_dirs(root, args.include_existing)
    mode = "regenerate" if args.include_existing else "missing"
    if args.json:
        payload = {
            "root": str(root),
            "mode": mode,
            "targets": [path.relative_to(root).as_posix() for path in targets],
            "count": len(targets),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for path in targets:
            print(path.relative_to(root).as_posix())
        if args.include_existing:
            print(f"Summary: {len(targets)} folders selected for FOLDER.md regeneration.")
        else:
            print(f"Summary: {len(targets)} folders missing FOLDER.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
