#!/usr/bin/env python3
"""List project folders that are missing Agents.md."""

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
    parser = argparse.ArgumentParser(description="List folders missing Agents.md.")
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
    return parser.parse_args()


def has_agents_file(directory: Path) -> bool:
    return any(child.is_file() and child.name.lower() == "agents.md" for child in directory.iterdir())


def iter_missing_dirs(root: Path) -> list[Path]:
    missing: list[Path] = []
    for current, dir_names, _ in os.walk(root):
        dir_names[:] = [name for name in dir_names if name not in SKIP_DIRS and not name.startswith(".")]
        current_path = Path(current)
        if current_path == root:
            continue
        if not has_agents_file(current_path):
            missing.append(current_path)
    return sorted(missing, key=lambda item: item.relative_to(root).as_posix().lower())


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"Project root is not a directory: {root}")

    missing = iter_missing_dirs(root)
    if args.json:
        payload = {
            "root": str(root),
            "missing": [path.relative_to(root).as_posix() for path in missing],
            "count": len(missing),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for path in missing:
            print(path.relative_to(root).as_posix())
        print(f"Summary: {len(missing)} folders missing Agents.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
