---
name: apex-init-project-file
description: Initialize existing project folders with minimal missing Agents.md files. Use when the user asks to scan a project directory and create lightweight folder-level agent context files without overwriting existing Agents.md files.
---

# Apex Init Project File

## Workflow

Run `scripts/init_agents_md.py <project-root>` from this skill directory. If no root is specified by the user, use the current repository root.

The script scans project subdirectories, skips common generated/vendor folders, and creates `Agents.md` only where one does not already exist. It never overwrites an existing `Agents.md` or case-equivalent file.

Each created file must stay within three lines: folder name plus one-sentence purpose, a one-line bullet-style summary of main files, and `Agents: 本文件夹文件/结构变化时，请同步更新本文件内容。`
