---
name: apex-init-project-file
description: 初始化已有项目中缺失的目录级 Agents.md 文件。适用于用户要求扫描项目文件夹，并在不覆盖已有 Agents.md 的前提下，由 agent 根据真实上下文写出极简目录说明。
---

# Apex Init Project File

## 工作流

只使用 `scripts/init_agents_md.py <project-root>` 查找缺少 `Agents.md` 的文件夹。这个脚本只负责发现缺失项，不负责创建文件，也不负责生成文档内容。

对每个缺少 `Agents.md` 的文件夹，先阅读该文件夹内容和必要的相邻文件，理解它在项目里的真实作用。然后由你根据实际上下文创建 `Agents.md`，不要只根据文件夹名猜测。

每个新建的 `Agents.md` 必须控制在 3 行以内：

1. 第一行：文件夹名称 + 一句话说明真实作用。
2. 第二行：一行 bullet 风格列表，列出主要文件和简要功能。
3. 第三行：`Agents: 本文件夹文件/结构变化时，请同步更新本文件内容。`

只处理发现脚本列出的文件夹。绝不要覆盖已有 `Agents.md` 或大小写等价文件。
