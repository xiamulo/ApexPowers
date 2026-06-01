---
name: apex-init-project-agent
description: Initialize a project-level AGENTS.md and the companion .claude/rules rule documents for an existing project. Use when the user wants a maintainable project agent handbook, progressive-disclosure rules, or rule-document scaffolding without overwriting hand-edited files.
---

# Apex Init Project Agent

## Workflow

Run `scripts/init_project_agent.py <project-root>` from this skill directory. Default mode is a dry run; pass `--write` only after reviewing the files that would be created.

The script creates a root `AGENTS.md` plus `.claude/rules/*.md` documents for project structure, never-list, coding style, API design, backend, frontend, git workflow, and hooks. It skips existing files by default so user-edited guidance is preserved.

Use `--force` only when the user explicitly asks to regenerate existing agent/rules documents. After creation, review the generated text against the real project stack and trim anything that does not apply.
