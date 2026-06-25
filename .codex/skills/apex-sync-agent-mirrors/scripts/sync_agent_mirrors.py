#!/usr/bin/env python3
"""Mirror ApexPowers .agents templates into official Codex and Claude Code agents."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


GENERATED_MARKER = "Generated from ApexPowers .agents source template"
CODEX_MODEL = "gpt-5.5"
READ_ONLY_AGENT_NAMES = {"researcher", "code-reviewer", "perf-optimizer"}
HIGH_REASONING_AGENT_NAMES = {"planner", "code-reviewer"}
SOURCE_META_SECTION = "## 路径与 Schema 兼容说明（追加）"


@dataclass(frozen=True)
class AgentTemplate:
    """Parsed source agent template."""

    source_path: Path
    frontmatter: dict[str, object]
    body: str

    @property
    def name(self) -> str:
        return str(self.frontmatter["name"]).strip()

    @property
    def description(self) -> str:
        return str(self.frontmatter["description"]).strip()

    @property
    def routing_description(self) -> str:
        return str(self.frontmatter.get("routingDescription", "")).strip()

    @property
    def tools(self) -> list[str]:
        return as_string_list(self.frontmatter.get("tools", []))

    @property
    def mcp_servers(self) -> list[str]:
        return as_string_list(self.frontmatter.get("mcpServers", []))

    @property
    def triggers(self) -> list[str]:
        return as_string_list(self.frontmatter.get("triggers", []))


@dataclass(frozen=True)
class RenderedMirror:
    """Generated mirror file."""

    path: Path
    content: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate official agent mirrors from .agents/*.md.")
    parser.add_argument("root", nargs="?", default=".", help="Project root. Defaults to current directory.")
    parser.add_argument(
        "--source-dir",
        default=".agents",
        help="Source template directory relative to root. Defaults to .agents.",
    )
    parser.add_argument(
        "--target",
        choices=["all", "codex", "claude"],
        default="all",
        help="Mirror target to generate. Defaults to all.",
    )
    parser.add_argument(
        "--codex-dir",
        default=".codex/agents",
        help="Codex official agent output directory relative to root.",
    )
    parser.add_argument(
        "--claude-dir",
        default=".claude/agents",
        help="Claude Code official agent output directory relative to root.",
    )
    parser.add_argument("--write", action="store_true", help="Write generated mirrors. Default is dry-run.")
    parser.add_argument(
        "--force",
        "--regenerate",
        action="store_true",
        dest="force",
        help="Overwrite existing mirrors. Existing generated mirrors are overwritten automatically.",
    )
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON.")
    return parser.parse_args()


def resolve_inside(root: Path, path_value: str, label: str) -> Path:
    candidate = Path(path_value).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise SystemExit(f"{label} must stay inside project root: {resolved}") from exc
    return resolved


def as_string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def split_frontmatter(text: str, source_path: Path) -> tuple[list[str], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"Missing YAML frontmatter start: {source_path}")

    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            frontmatter_lines = lines[1:index]
            body = "\n".join(lines[index + 1 :]).strip() + "\n"
            return frontmatter_lines, body

    raise ValueError(f"Missing YAML frontmatter end: {source_path}")


def parse_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_frontmatter(lines: Iterable[str], source_path: Path) -> dict[str, object]:
    data: dict[str, object] = {}
    current_key: str | None = None

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            continue

        if line.startswith("  - ") and current_key:
            current_value = data.setdefault(current_key, [])
            if not isinstance(current_value, list):
                raise ValueError(f"Mixed scalar/list value for {current_key}: {source_path}")
            current_value.append(parse_scalar(line[4:]))
            continue

        if ":" not in line:
            raise ValueError(f"Unsupported frontmatter line in {source_path}: {line}")

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        current_key = key
        data[key] = parse_scalar(value) if value else []

    for required in ("name", "description"):
        if not str(data.get(required, "")).strip():
            raise ValueError(f"Missing required frontmatter field {required}: {source_path}")

    return data


def load_templates(source_dir: Path) -> list[AgentTemplate]:
    if not source_dir.is_dir():
        raise SystemExit(f"Source agent directory does not exist: {source_dir}")

    templates: list[AgentTemplate] = []
    for source_path in sorted(source_dir.glob("*.md")):
        if source_path.name.lower() == "agents.md":
            continue

        text = source_path.read_text(encoding="utf-8")
        frontmatter_lines, body = split_frontmatter(text, source_path)
        frontmatter = parse_frontmatter(frontmatter_lines, source_path)
        templates.append(AgentTemplate(source_path=source_path, frontmatter=frontmatter, body=body))

    if not templates:
        raise SystemExit(f"No source agent templates found in: {source_dir}")
    return templates


def remove_source_meta_section(body: str) -> str:
    lines = body.splitlines()
    output: list[str] = []
    skipping = False

    for line in lines:
        if line.strip() == SOURCE_META_SECTION:
            skipping = True
            continue
        if skipping and line.startswith("## "):
            skipping = False
        if not skipping:
            output.append(line)

    return "\n".join(output).strip() + "\n"


def combined_description(template: AgentTemplate) -> str:
    parts = [template.description]
    if template.routing_description:
        parts.append(template.routing_description)
    return " ".join(part for part in parts if part).strip()


def sandbox_mode(template: AgentTemplate) -> str:
    if template.name in READ_ONLY_AGENT_NAMES:
        return "read-only"
    return "workspace-write"


def reasoning_effort(template: AgentTemplate) -> str:
    if template.name in HIGH_REASONING_AGENT_NAMES:
        return "high"
    return "medium"


def toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def yaml_scalar(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def toml_multiline_literal(value: str) -> str:
    value = value.rstrip()
    if "'''" not in value:
        return "'''\n" + value + "\n'''"
    return toml_string(value)


def source_relative_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def source_metadata_block(template: AgentTemplate, root: Path, target_name: str) -> str:
    lines = [
        f"# Generated {target_name} Mirror",
        "",
        f"- Source template: `{source_relative_path(template.source_path, root)}`",
        f"- Source routing: {template.routing_description or '（未声明）'}",
        f"- Source tools: {', '.join(template.tools) if template.tools else '（继承运行时默认工具）'}",
        f"- Source MCP servers: {', '.join(template.mcp_servers) if template.mcp_servers else '（继承运行时 MCP）'}",
    ]
    if template.triggers:
        lines.append(f"- Source triggers: {', '.join(template.triggers)}")
    if target_name == "Codex":
        lines.append(
            "- Codex runtime note: source MCP names are prompt-level preferences; configure real MCP "
            "endpoints in `.codex/config.toml` or this TOML when exact server definitions are known."
        )
    if target_name == "Claude Code":
        lines.append("- Claude Code runtime note: source MCP names are emitted in generated frontmatter.")
    lines.extend(
        [
            "",
            "本文件由 `.agents` 源模板生成；需要调整角色提示词时，先改源模板，再重新生成镜像。",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n\n"


def render_codex(template: AgentTemplate, root: Path, output_dir: Path) -> RenderedMirror:
    body = remove_source_meta_section(template.body)
    instructions = source_metadata_block(template, root, "Codex") + body
    content = "\n".join(
        [
            f"# {GENERATED_MARKER}: {source_relative_path(template.source_path, root)}",
            "# Do not edit by hand; update .agents source and rerun apex-sync-agent-mirrors.",
            "",
            f"name = {toml_string(template.name)}",
            f"description = {toml_string(combined_description(template))}",
            f"model = {toml_string(CODEX_MODEL)}",
            f'model_reasoning_effort = "{reasoning_effort(template)}"',
            f'sandbox_mode = "{sandbox_mode(template)}"',
            f"developer_instructions = {toml_multiline_literal(instructions)}",
            "",
        ]
    )
    return RenderedMirror(path=output_dir / f"{template.name}.toml", content=content)


def yaml_list_block(key: str, values: list[str]) -> list[str]:
    if not values:
        return []
    lines = [f"{key}:"]
    lines.extend(f"  - {yaml_scalar(value)}" for value in values)
    return lines


def render_claude(template: AgentTemplate, root: Path, output_dir: Path) -> RenderedMirror:
    frontmatter = [
        "---",
        f"name: {yaml_scalar(template.name)}",
        f"description: {yaml_scalar(combined_description(template))}",
    ]
    frontmatter.extend(yaml_list_block("tools", template.tools))
    frontmatter.extend(yaml_list_block("mcpServers", template.mcp_servers))
    frontmatter.append("---")

    body = remove_source_meta_section(template.body)
    note = "\n".join(
        [
            f"<!-- {GENERATED_MARKER}: {source_relative_path(template.source_path, root)} -->",
            "<!-- Do not edit by hand; update .agents source and rerun apex-sync-agent-mirrors. -->",
            "",
            source_metadata_block(template, root, "Claude Code"),
        ]
    )
    content = "\n".join(frontmatter) + "\n\n" + note + body
    return RenderedMirror(path=output_dir / f"{template.name}.md", content=content)


def should_write(path: Path, content: str, force: bool) -> tuple[bool, str]:
    if not path.exists():
        return True, "create"

    existing = path.read_text(encoding="utf-8")
    if existing == content:
        return False, "unchanged"
    if force or GENERATED_MARKER in existing:
        return True, "overwrite"
    return False, "skip-existing"


def render_all(
    templates: list[AgentTemplate],
    root: Path,
    target: str,
    codex_dir: Path,
    claude_dir: Path,
) -> list[RenderedMirror]:
    mirrors: list[RenderedMirror] = []
    for template in templates:
        if target in {"all", "codex"}:
            mirrors.append(render_codex(template, root, codex_dir))
        if target in {"all", "claude"}:
            mirrors.append(render_claude(template, root, claude_dir))
    return mirrors


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"Project root is not a directory: {root}")

    source_dir = resolve_inside(root, args.source_dir, "source-dir")
    codex_dir = resolve_inside(root, args.codex_dir, "codex-dir")
    claude_dir = resolve_inside(root, args.claude_dir, "claude-dir")
    templates = load_templates(source_dir)
    mirrors = render_all(templates, root, args.target, codex_dir, claude_dir)

    results = []
    for mirror in mirrors:
        write, action = should_write(mirror.path, mirror.content, args.force)
        if args.write and write:
            mirror.path.parent.mkdir(parents=True, exist_ok=True)
            mirror.path.write_text(mirror.content, encoding="utf-8", newline="\n")
        results.append({"path": source_relative_path(mirror.path, root), "action": action})

    if args.json:
        print(json.dumps({"root": str(root), "target": args.target, "write": args.write, "results": results}, ensure_ascii=False, indent=2))
        return 0

    mode = "WRITE" if args.write else "DRY-RUN"
    for result in results:
        print(f"{mode} {result['action']}: {result['path']}")
    print(f"Summary: {len(results)} mirror files checked from {len(templates)} source templates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
