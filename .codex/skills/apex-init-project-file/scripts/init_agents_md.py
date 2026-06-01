#!/usr/bin/env python3
"""Create minimal Agents.md files for project subdirectories."""

from __future__ import annotations

import argparse
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

SKIP_FILE_PREFIXES = (".",)
MAX_MAIN_FILES = 6
SPELL = "Agents: 本文件夹文件/结构变化时，请同步更新本文件内容。"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create missing minimal Agents.md files for project folders."
    )
    parser.add_argument(
        "root",
        nargs="?",
        default=".",
        help="Existing project root to scan. Defaults to the current directory.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print target folders without writing files.",
    )
    return parser.parse_args()


def has_agents_file(directory: Path) -> bool:
    return any(child.is_file() and child.name.lower() == "agents.md" for child in directory.iterdir())


def should_skip(directory: Path) -> bool:
    return directory.name in SKIP_DIRS or directory.name.startswith(".")


def iter_target_dirs(root: Path) -> list[Path]:
    targets: list[Path] = []
    for current, dir_names, _ in os.walk(root):
        dir_names[:] = [name for name in dir_names if name not in SKIP_DIRS and not name.startswith(".")]
        current_path = Path(current)
        if current_path == root or should_skip(current_path):
            continue
        targets.append(current_path)
    return targets


def purpose_for(directory: Path) -> str:
    name = directory.name
    lower = name.lower()
    known = {
        "src": "项目源代码与主要实现所在目录。",
        "source": "项目源代码与主要实现所在目录。",
        "app": "应用入口、路由或业务装配所在目录。",
        "pages": "页面级模块与路由视图所在目录。",
        "components": "可复用界面组件所在目录。",
        "hooks": "可复用状态与副作用逻辑所在目录。",
        "utils": "通用工具函数与辅助逻辑所在目录。",
        "lib": "共享库代码与底层封装所在目录。",
        "services": "外部服务、接口调用与业务服务封装所在目录。",
        "api": "接口路由、请求处理或 API 封装所在目录。",
        "tests": "测试用例与测试辅助资源所在目录。",
        "test": "测试用例与测试辅助资源所在目录。",
        "docs": "项目文档与说明资料所在目录。",
        "scripts": "自动化脚本与开发辅助命令所在目录。",
        "config": "项目配置与环境相关设置所在目录。",
        "types": "类型声明与共享类型定义所在目录。",
        "styles": "样式、主题与视觉资源所在目录。",
        "assets": "静态资源、图片或媒体文件所在目录。",
    }
    purpose = known.get(lower, "本目录承载与其命名相关的项目文件。")
    return f"{name}：{purpose}"


def file_role(path: Path) -> str:
    lower = path.name.lower()
    if lower in {"index.ts", "index.tsx", "index.js", "index.jsx", "__init__.py"}:
        return "入口或导出聚合"
    if lower.startswith("test_") or lower.endswith((".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx")):
        return "测试用例"
    if lower.endswith((".md", ".mdx")):
        return "文档说明"
    if lower.endswith((".json", ".yaml", ".yml", ".toml", ".ini")):
        return "配置数据"
    if lower.endswith((".css", ".scss", ".sass", ".less")):
        return "样式定义"
    if lower.endswith((".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".rs", ".java", ".cs")):
        return "代码实现"
    return "项目文件"


def main_files_line(directory: Path) -> str:
    files = [
        child
        for child in sorted(directory.iterdir(), key=lambda item: item.name.lower())
        if child.is_file()
        and not child.name.startswith(SKIP_FILE_PREFIXES)
        and child.name.lower() != "agents.md"
    ]
    if not files:
        return "主要文件：- 暂无直接文件，主要包含子目录。"

    items = [f"- {path.name}: {file_role(path)}" for path in files[:MAX_MAIN_FILES]]
    if len(files) > MAX_MAIN_FILES:
        items.append(f"- 另有 {len(files) - MAX_MAIN_FILES} 个文件")
    return "主要文件：" + "；".join(items) + "。"


def content_for(directory: Path) -> str:
    return "\n".join([purpose_for(directory), main_files_line(directory), SPELL]) + "\n"


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"Project root is not a directory: {root}")

    created: list[Path] = []
    skipped_existing = 0
    for directory in iter_target_dirs(root):
        if has_agents_file(directory):
            skipped_existing += 1
            continue
        target = directory / "Agents.md"
        created.append(target)
        if not args.dry_run:
            target.write_text(content_for(directory), encoding="utf-8")

    action = "Would create" if args.dry_run else "Created"
    for path in created:
        print(f"{action}: {path}")
    print(f"Summary: {len(created)} created, {skipped_existing} skipped because Agents.md exists.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
