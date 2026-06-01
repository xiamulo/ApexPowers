---
name: apex-init-project-agent
description: 初始化已有项目的项目级 AGENTS.md 和 .claude/rules 规则文档。适用于用户希望创建可维护的项目协作手册、分层规则文档，且不覆盖已有手写规则文件的场景。
---

# Apex Init Project Agent

## 工作流

运行 `scripts/init_project_agent.py <project-root>`。默认只预览将创建哪些文件；确认范围合理后，才传入 `--write` 真正写入。

脚本会创建项目根目录 `AGENTS.md`，以及 `.claude/rules/*.md` 规则文档，包括 project-structure、never-list、coding-style、api-design、backend、frontend、git-workflow 和 hooks。默认跳过已有文件，保护用户已经手写过的规则。

只有在用户明确要求重新生成已有规则文档时，才使用 `--force`。创建完成后，要根据项目真实技术栈和目录结构复核生成内容，删除不适用的模板化约定。
