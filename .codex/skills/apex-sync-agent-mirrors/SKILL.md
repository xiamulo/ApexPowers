---
name: apex-sync-agent-mirrors
description: 从 .agents/*.md 源模板生成官方 Codex .codex/agents/*.toml 和 Claude Code .claude/agents/*.md 镜像。适用于希望同一套子智能体提示词可在 Codex 与 Claude Code 之间切换使用的场景。
---

# Apex Sync Agent Mirrors

## 工作流

运行 `scripts/sync_agent_mirrors.py <project-root>`。默认只预览；确认范围合理后，传入 `--write` 写入生成结果。

`.agents/*.md` 是唯一源模板。不要手写维护 `.codex/agents/*.toml` 或 `.claude/agents/*.md`；需要调整角色、调度描述、handoff 或工具边界时，先改 `.agents/*.md`，再重新生成镜像。

## 生成目标

- Codex：生成 `.codex/agents/*.toml`，使用官方 custom agent schema：`name`、`description`、`developer_instructions`，并补充 `model = "gpt-5.5"`、`sandbox_mode` 与 `model_reasoning_effort`。
- Claude Code：生成 `.claude/agents/*.md`，使用官方 Markdown + YAML frontmatter schema：`name`、`description`、`tools`、`mcpServers`，正文使用源模板提示词。

脚本会把源模板里的 `description` 和 `routingDescription` 合并到官方镜像的 `description`，因为官方调度主要读取 `description`。源模板里的 `routingDescription`、`context: fork` 等 ApexPowers 私有字段不直接写入官方镜像 schema。

## 常用命令

```powershell
python .codex\skills\apex-sync-agent-mirrors\scripts\sync_agent_mirrors.py .
python .codex\skills\apex-sync-agent-mirrors\scripts\sync_agent_mirrors.py . --target codex --write
python .codex\skills\apex-sync-agent-mirrors\scripts\sync_agent_mirrors.py . --target claude --write
python .codex\skills\apex-sync-agent-mirrors\scripts\sync_agent_mirrors.py . --target all --write --force
```

## 覆盖规则

- 不存在的镜像会创建。
- 已生成过的镜像含有生成标记，会自动覆盖。
- 没有生成标记的已有文件默认跳过，避免覆盖别人手写的官方 agent。
- 用户明确要求“重新生成 / 覆盖 / 刷新 / regenerate”时，使用 `--force` 或 `--regenerate`。

## 禁止事项

- 不要把 `.codex/agents/*.toml` 或 `.claude/agents/*.md` 当作新的源头维护。
- 不要把 Codex TOML schema 和 Claude Code Markdown schema 混用。
- 不要手动删除 `.agents/*.md` 中的重要提示词内容。
