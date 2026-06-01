---
name: apex-init-project-file
description: Initialize missing folder-level Agents.md files in an existing project using agent-written, context-aware content. Use when the user asks to scan project folders and create concise Agents.md files without overwriting existing ones.
---

# Apex Init Project File

## Workflow

Use `scripts/init_agents_md.py <project-root>` only to find folders that are missing `Agents.md`. The script is discovery-only and must not create or write documentation content.

For each missing folder, read the folder contents and enough nearby files to understand its real purpose. Then create `Agents.md` yourself using the actual project context; do not rely on filename guesses alone.

Each created `Agents.md` must stay within three lines:

1. Folder name plus one concise sentence describing the folder's actual purpose.
2. One-line bullet-style list of the main files and their roles.
3. `Agents: 本文件夹文件/结构变化时，请同步更新本文件内容。`

Only create files for folders reported by the discovery script. Never overwrite existing `Agents.md` or case-equivalent files.
