#!/usr/bin/env python3
"""Add conservative standard headers to code files that have no header."""

from __future__ import annotations

import argparse
import ast
import os
import re
from pathlib import Path


LINE_COMMENT_EXTS = {
    ".ts": "//",
    ".tsx": "//",
    ".js": "//",
    ".jsx": "//",
    ".go": "//",
    ".rs": "//",
    ".java": "//",
    ".cs": "//",
    ".cpp": "//",
    ".c": "//",
    ".h": "//",
    ".hpp": "//",
    ".kt": "//",
}
HASH_COMMENT_EXTS = {".py"}
MD_COMMENT_EXTS = {".md", ".mdx"}
SUPPORTED_EXTS = set(LINE_COMMENT_EXTS) | HASH_COMMENT_EXTS | MD_COMMENT_EXTS
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
SOURCE_EXTS = SUPPORTED_EXTS - MD_COMMENT_EXTS
MAX_DEPS = 5
MAX_EXPORTS = 5
HEADER_MARKERS = ("@purpose", "文件作用")
CLAUDE_LINE = (
    "Claude: 本文件内容、接口、依赖、导出或架构发生任何变更时，请**立即**同步更新本头部注释，"
    "并同时更新所属文件夹的 claude.md 文件。"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize missing standard code headers.")
    parser.add_argument("root", nargs="?", default=".", help="Project root. Defaults to current directory.")
    parser.add_argument(
        "paths",
        nargs="*",
        help="Optional files or directories relative to root. Defaults to all supported code files.",
    )
    parser.add_argument("--write", action="store_true", help="Write headers. Without this, only dry-run.")
    parser.add_argument("--include-md", action="store_true", help="Also process .md and .mdx files.")
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
    if path.suffix == ".py" and len(lines) > index:
        encoding_re = re.compile(r"^#.*coding[:=]\s*[-\w.]+")
        if encoding_re.match(lines[index]):
            index += 1
    first = first_meaningful_line(lines[index : index + 8])
    if first.startswith(("//", "/*", "<!--")):
        return True
    if path.suffix.lower() in HASH_COMMENT_EXTS and first.startswith("#"):
        return True
    return False


def newline_for(text: str) -> str:
    crlf = text.count("\r\n")
    lf = text.count("\n") - crlf
    cr = text.count("\r") - crlf
    if crlf >= lf and crlf >= cr and crlf:
        return "\r\n"
    if cr > lf and cr:
        return "\r"
    return "\n"


def import_names_for_text(path: Path, text: str) -> list[str]:
    suffix = path.suffix.lower()
    if suffix == ".py":
        return python_imports(text)
    patterns = [
        r"^\s*import\s+(?:[^'\"]+\s+from\s+)?['\"]([^'\"]+)['\"]",
        r"^\s*import\s+([A-Za-z0-9_./@-]+)",
        r"^\s*from\s+['\"]([^'\"]+)['\"]\s+import",
        r"^\s*use\s+([A-Za-z0-9_:]+)",
        r"^\s*using\s+([A-Za-z0-9_.]+)",
        r"^\s*#include\s+[<\"]([^>\"]+)[>\"]",
        r"^\s*package\s+([A-Za-z0-9_.]+)",
    ]
    deps: list[str] = []
    for line in text.splitlines()[:160]:
        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                deps.append(clean_dep_name(match.group(1)))
                break
    return unique_limited(deps, MAX_DEPS)


def python_imports(text: str) -> list[str]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    deps: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            deps.extend(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            deps.append(node.module.split(".")[0])
    return unique_limited(deps, MAX_DEPS)


def clean_dep_name(value: str) -> str:
    clean = value.strip()
    if clean.startswith("."):
        return clean
    if clean.startswith("@"):
        parts = clean.split("/")
        return "/".join(parts[:2]) if len(parts) >= 2 else clean
    if "::" in clean:
        return clean.split("::")[0]
    return clean.split("/")[0]


def export_names_for_text(path: Path, text: str) -> list[str]:
    suffix = path.suffix.lower()
    if suffix == ".py":
        return python_exports(text)
    patterns = [
        r"^\s*export\s+(?:default\s+)?(?:async\s+)?(?:function|class|const|let|var|interface|type|enum)\s+([A-Za-z_][\w]*)",
        r"^\s*export\s*\{([^}]+)\}",
        r"^\s*pub\s+(?:async\s+)?(?:fn|struct|enum|trait|mod|const)\s+([A-Za-z_][\w]*)",
        r"^\s*public\s+(?:class|interface|enum|struct|record)\s+([A-Za-z_][\w]*)",
        r"^\s*func\s+([A-Za-z_][\w]*)",
        r"^\s*(?:class|interface|enum|struct)\s+([A-Za-z_][\w]*)",
    ]
    exports: list[str] = []
    for line in text.splitlines()[:260]:
        for pattern in patterns:
            match = re.match(pattern, line)
            if not match:
                continue
            value = match.group(1)
            if "," in value:
                exports.extend(clean_export_name(part) for part in value.split(","))
            else:
                exports.append(clean_export_name(value))
            break
    return unique_limited([item for item in exports if item], MAX_EXPORTS)


def python_exports(text: str) -> list[str]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    exports: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not node.name.startswith("_"):
            exports.append(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    exports.append(target.id)
    return unique_limited(exports, MAX_EXPORTS)


def clean_export_name(value: str) -> str:
    return value.strip().split(" as ")[0].strip()


def unique_limited(values: list[str], limit: int) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        clean = value.strip()
        if not clean or clean in seen:
            continue
        seen.add(clean)
        result.append(clean)
        if len(result) >= limit:
            break
    return result


def purpose_for(path: Path, exports: list[str]) -> str:
    stem = path.stem
    folder = path.parent.name
    if exports:
        return f"提供 {', '.join(exports[:3])} 等与 {folder} 相关的核心实现。"
    if stem.lower() in {"index", "mod", "__init__"}:
        return f"聚合并导出 {folder} 目录的主要能力。"
    return f"实现 {stem} 相关逻辑，服务于 {folder} 模块。"


def rules_for(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".ts", ".tsx", ".js", ".jsx"}:
        return "保持导出接口稳定；避免引入不必要的跨层依赖。"
    if suffix == ".py":
        return "保持函数职责清晰；避免隐藏副作用。"
    if suffix in {".go", ".rs"}:
        return "保持公开接口最小；错误处理必须显式。"
    if suffix in {".java", ".cs", ".kt"}:
        return "保持类职责单一；依赖关系必须清晰。"
    return "保持实现直白；依赖和导出变化需同步说明。"


def relative_folder(root: Path, path: Path) -> str:
    folder = path.parent.relative_to(root).as_posix()
    return "." if folder == "." else folder


def header_for(root: Path, path: Path, text: str) -> str:
    deps = import_names_for_text(path, text)
    exports = export_names_for_text(path, text)
    deps_text = ", ".join(deps) if deps else "无显式关键依赖"
    exports_text = ", ".join(exports) if exports else "无显式对外导出"
    location = relative_folder(root, path)
    lines = [
        f"@purpose: {purpose_for(path, exports)}",
        f"@deps: {deps_text}",
        f"@exports: {exports_text}",
        f"@location: {location}（参考 @{location}/claude.md）",
        f"@rules: {rules_for(path)}",
        "",
        CLAUDE_LINE,
    ]
    suffix = path.suffix.lower()
    if suffix in HASH_COMMENT_EXTS:
        return "\n".join(f"# {line}" if line else "#" for line in lines) + "\n\n"
    if suffix in MD_COMMENT_EXTS:
        return "<!--\n" + "\n".join(lines) + "\n-->\n\n"
    prefix = LINE_COMMENT_EXTS[suffix]
    return "\n".join(f"{prefix} {line}" if line else prefix for line in lines) + "\n\n"


def insertion_index(path: Path, text: str) -> int:
    lines = text.splitlines(keepends=True)
    index = 0
    if lines and lines[0].startswith("#!"):
        index = 1
    if path.suffix == ".py" and len(lines) > index:
        encoding_re = re.compile(r"^#.*coding[:=]\s*[-\w.]+")
        if encoding_re.match(lines[index]):
            index += 1
    return sum(len(line) for line in lines[:index])


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


def should_process(path: Path, text: str) -> tuple[bool, str]:
    if has_standard_marker(text):
        return False, "standard marker exists"
    if has_existing_header_comment(path, text):
        return False, "existing header comment"
    return True, "missing header"


def write_header(root: Path, path: Path, text: str) -> None:
    index = insertion_index(path, text)
    newline = newline_for(text)
    header = header_for(root, path, text).replace("\n", newline)
    updated = text[:index] + header + text[index:]
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(updated)


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"Project root is not a directory: {root}")

    candidates = iter_files(root, args.paths, args.include_md)
    changed = 0
    skipped = 0
    for path in candidates:
        text = read_text(path)
        if text is None:
            skipped += 1
            print(f"SKIP unreadable: {path}")
            continue
        process, reason = should_process(path, text)
        if not process:
            skipped += 1
            print(f"SKIP {reason}: {path}")
            continue
        changed += 1
        action = "WRITE" if args.write else "DRY-RUN"
        print(f"{action} missing header: {path}")
        if args.write:
            write_header(root, path, text)

    mode = "written" if args.write else "would write"
    print(f"Summary: {changed} {mode}, {skipped} skipped, {len(candidates)} scanned.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
