# ApexPowers

ApexPowers 是一套私有 Codex skill 包，用来给项目初始化 agent 可读的上下文、规则文档、文件头注释和目录说明。

当前包含：

- `.codex/skills/apex-init-project-agent`：生成项目根 `AGENTS.md` 和 `.claude/rules/*.md`
- `.codex/skills/apex-init-project-code`：为缺少说明的代码文件添加标准头部注释
- `.codex/skills/apex-init-project-file`：为项目目录生成轻量 `Agents.md`
- `.codex/skills/apex-sync-agent-mirrors`：把 `.agents/*.md` 源模板生成 Codex / Claude Code 官方子智能体镜像
- `.agents/*.md`：项目子 agent 角色提示词

这个仓库设计为私有使用。不要发布到 npm 或公开包仓库，除非你明确希望别人复制使用。

## 新机器拉取

因为仓库是私有的，新机器必须先登录 GitHub。

推荐用 GitHub CLI：

```powershell
gh auth login
git clone https://github.com/xiamulo/ApexPowers.git D:\gitdown\ApexPowers
```

如果不用 `gh`，也可以用 Git Credential Manager 或有私有仓库权限的 personal access token。不要把 token 写进脚本或 README。

## 安装到单个项目

适合希望某个目标项目自带一份 ApexPowers skills 的情况。

```powershell
$ApexRoot = "D:\gitdown\ApexPowers"
$Target = "D:\path\to\your-project"

New-Item -ItemType Directory -Force "$Target\.codex\skills" | Out-Null
Copy-Item "$ApexRoot\.codex\skills\apex-*" "$Target\.codex\skills\" -Recurse -Force

New-Item -ItemType Directory -Force "$Target\.agents" | Out-Null
Copy-Item "$ApexRoot\.agents\*.md" "$Target\.agents\" -Force
```

如果目标项目也是私有仓库，可以提交 `.codex/skills/apex-*` 和 `.agents/`。

如果目标项目希望直接使用官方 Codex 或 Claude Code 子智能体，再从 `.agents` 源模板生成镜像：

```powershell
# 同时生成 .codex/agents/*.toml 和 .claude/agents/*.md
python "$Target\.codex\skills\apex-sync-agent-mirrors\scripts\sync_agent_mirrors.py" "$Target" --target all --write

# 只生成 Codex 官方 custom agents
python "$Target\.codex\skills\apex-sync-agent-mirrors\scripts\sync_agent_mirrors.py" "$Target" --target codex --write

# 只生成 Claude Code 官方 subagents
python "$Target\.codex\skills\apex-sync-agent-mirrors\scripts\sync_agent_mirrors.py" "$Target" --target claude --write
```

`.agents/*.md` 是源模板；`.codex/agents/*.toml` 和 `.claude/agents/*.md` 是镜像。需要改提示词时，先改 `.agents`，再重新生成镜像。用户明确要求覆盖/刷新时，加 `--force`。

如果目标项目会公开，或者你不想让别人拿到 ApexPowers，把下面内容加入目标项目的 `.gitignore`：

```gitignore
.codex/skills/apex-*
.agents/
.codex/agents/
.claude/agents/
```

## 安装到本机 Codex 全局 skills

适合希望同一台机器上的所有 Codex 项目都能使用 Apex skills，但不想把它复制进每个项目仓库。

```powershell
$ApexRoot = "D:\gitdown\ApexPowers"
$CodexHome = "$env:USERPROFILE\.codex"

New-Item -ItemType Directory -Force "$CodexHome\skills" | Out-Null
Copy-Item "$ApexRoot\.codex\skills\apex-*" "$CodexHome\skills\" -Recurse -Force
```

全局安装只放在当前机器的用户目录里，不会进入目标项目源码。

## 手动运行初始化脚本

下面命令可以直接从 ApexPowers checkout 运行。把 `$Target` 换成目标项目路径。

生成项目根 `AGENTS.md` 和 `.claude/rules`：

```powershell
$ApexRoot = "D:\gitdown\ApexPowers"
$Target = "D:\path\to\your-project"

python "$ApexRoot\.codex\skills\apex-init-project-agent\scripts\init_project_agent.py" "$Target"
python "$ApexRoot\.codex\skills\apex-init-project-agent\scripts\init_project_agent.py" "$Target" --write
```

第一条是 dry run。确认将要创建的文件合理后，再运行带 `--write` 的命令。

为代码文件添加缺失头部注释：

```powershell
python "$ApexRoot\.codex\skills\apex-init-project-code\scripts\init_code_headers.py" "$Target"
python "$ApexRoot\.codex\skills\apex-init-project-code\scripts\init_code_headers.py" "$Target" --write
```

第一条是 dry run。确认目标列表合理后，再运行带 `--write` 的命令。

为目录创建缺失的 `Agents.md`：

```powershell
python "$ApexRoot\.codex\skills\apex-init-project-file\scripts\init_agents_md.py" "$Target" --dry-run
python "$ApexRoot\.codex\skills\apex-init-project-file\scripts\init_agents_md.py" "$Target"
```

注意：这个脚本用 `--dry-run` 预览；不带 `--dry-run` 时会写入文件。

生成 Codex / Claude Code 官方子智能体镜像：

```powershell
python "$ApexRoot\.codex\skills\apex-sync-agent-mirrors\scripts\sync_agent_mirrors.py" "$Target"
python "$ApexRoot\.codex\skills\apex-sync-agent-mirrors\scripts\sync_agent_mirrors.py" "$Target" --target all --write
```

第一条是 dry run。确认将要生成的 `.codex/agents/*.toml` 和 `.claude/agents/*.md` 合理后，再运行带 `--write` 的命令。

## 在 Codex 里使用

安装后，在目标项目中可以直接让 Codex 使用这些 skill：

```text
Use apex-init-project-agent to initialize this project.
Use apex-init-project-code to add missing code headers.
Use apex-init-project-file to create missing Agents.md files.
Use apex-sync-agent-mirrors to generate Codex and Claude Code agent mirrors.
```

这些 skill 默认偏保守，会尽量保留已有手写文件，不覆盖已存在的 `Agents.md` 或标准头部注释；镜像生成工具也会跳过没有生成标记的既有官方 agent 文件。

## 隐私注意事项

- 保持 GitHub 仓库为 private。
- 不要提交 `.serena/`、`.env`、token、凭据或机器本地状态。
- 对公开项目或客户项目，优先用全局安装，或者把 `.codex/skills/apex-*`、`.agents/`、`.codex/agents/`、`.claude/agents/` 加进 `.gitignore`。
- 如果用 token 拉取私有仓库，把 token 放进系统凭据管理器，不要写入脚本。

## 维护检查

修改 Python 脚本后，运行：

```powershell
python -m py_compile `
  .codex\skills\apex-init-project-agent\scripts\init_project_agent.py `
  .codex\skills\apex-init-project-code\scripts\init_code_headers.py `
  .codex\skills\apex-init-project-file\scripts\init_agents_md.py `
  .codex\skills\apex-sync-agent-mirrors\scripts\sync_agent_mirrors.py
```

提交前删除生成的 `__pycache__` 目录。
