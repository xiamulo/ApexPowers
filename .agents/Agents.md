.agents：存放项目子智能体角色提示词，每个文件对应一个可被调度的专用 agent。
主要文件：- planner.md: 任务规划；- implementer.md: 按计划实现；- developer.md: 综合开发；- code-reviewer.md: 代码审查；- perf-optimizer.md: 性能分析；- researcher.md: 代码与文档调研。
Agents: 本文件夹文件/结构变化时，请同步更新本文件内容。
路径/schema 说明：本目录是 ApexPowers 私有子智能体提示词模板，当前主路径为 `.agents/*.md`；如需官方 Codex 运行时直接识别，应从这些模板镜像生成 `.codex/agents/*.toml`；如需 Claude Code 直接识别，应镜像生成 `.claude/agents/*.md`。不要把 `.agents` 直接等同于官方自动加载路径。
Schema 约定：保留现有 Markdown + YAML frontmatter；新增调度描述、handoff、兼容说明优先写在正文追加段落里，避免破坏已有私有消费者。官方镜像时再转换字段，例如 `name`、`description`、`tools`、`mcpServers`、`context` -> Codex 的 `name`、`description`、`developer_instructions`、`sandbox_mode`、`mcp_servers`，或 Claude Code 的 `name`、`description`、`tools`、`mcpServers`、`permissionMode`。
调度总原则：少量高质量 agent 优于大量泛化 agent。主上下文负责分派和综合；子智能体只处理清晰、窄范围任务，并用结构化摘要或文件产物交回，避免把搜索日志、长 diff、失败尝试和无关上下文带回主上下文。
