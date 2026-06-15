# ApexPowers

ApexPowers 是一套私有 Codex skill 包，用来给项目初始化 agent 可读的上下文、规则文档、文件头注释和目录说明。

当前包含：

- `.codex/skills/apex-init-project-agent`：生成项目根 `AGENTS.md`、`CLAUDE.md` 和 `.claude/rules/*.md`
- `.codex/skills/apex-init-project-code`：为缺少说明的代码文件添加标准头部注释
- `.codex/skills/apex-init-project-file`：为项目目录生成轻量 `Agents.md`
- `.codex/skills/apex-sync-agent-mirrors`：把 `.agents/*.md` 源模板生成 Codex / Claude Code 官方子智能体镜像
- `.codex/skills/apex-init-project-hooks`：为目标项目安装 Codex / Claude Code loop hooks、共享 runtime 和 review gate 状态目录
- `.codex/skills/frontend-design`：Anthropic 官方前端设计 skill，用于生成更有设计感的生产级 Web UI
- `.codex/skills/gsap-core`：GreenSock 官方 GSAP core API skill
- `.codex/skills/gsap-scrolltrigger`：GreenSock 官方 ScrollTrigger / scroll animation skill
- `.codex/skills/gsap-performance`：GreenSock 官方 GSAP performance / smooth animation skill
- `.codex/skills/gsap-timeline`：GreenSock 官方 timeline / animation sequencing skill
- `.codex/skills/gsap-plugins`：GreenSock 官方 GSAP plugins skill
- `.codex/skills/gsap-utils`：GreenSock 官方 `gsap.utils` helper skill
- `.codex/skills/gsap-react`：GreenSock 官方 React / Next.js GSAP skill
- `.codex/skills/gsap-frameworks`：GreenSock 官方 Vue / Svelte / Nuxt / SvelteKit GSAP skill
- `.codex/skills/react-best-practices`：Vercel React / Next.js 性能与工程实践 skill（内部名称 `vercel-react-best-practices`）
- `.codex/skills/webapp-testing`：Anthropic 官方 Playwright Web 应用测试 skill
- `.codex/skills/web-design-guidelines`：Vercel Web UI / UX / accessibility 审查 skill
- `.codex/skills/next-best-practices`：Vercel Next.js App Router / RSC / 数据获取 / 资源优化实践 skill
- `.codex/skills/github-solution-research`：从 GitHub 开源项目、issues、PR、讨论和示例中查找可复用工程解法的 research skill
- `.codex/skills/apex-grill-with-docs`：Apex 需求烤问工作流，先确认用户最多接受多少个后续问题，再只追问会影响项目走向的关键问题，并维护 `CONTEXT.md` / ADR
- `.codex/skills/apex-to-prd`：Apex PRD 合成工作流，用于把已讨论上下文整理成正式 PRD 并发布到项目 issue tracker
- `.codex/skills/apex-to-issues`：Apex issue 拆分工作流，用于把 PRD / spec 拆成可独立实现的 vertical-slice issues
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
$SkillNames = @(
  "apex-init-project-agent",
  "apex-init-project-code",
  "apex-init-project-file",
  "apex-sync-agent-mirrors",
  "apex-init-project-hooks",
  "frontend-design",
  "gsap-core",
  "gsap-scrolltrigger",
  "gsap-performance",
  "gsap-timeline",
  "gsap-plugins",
  "gsap-utils",
  "gsap-react",
  "gsap-frameworks",
  "react-best-practices",
  "webapp-testing",
  "web-design-guidelines",
  "next-best-practices",
  "github-solution-research",
  "apex-grill-with-docs",
  "apex-to-prd",
  "apex-to-issues"
)

New-Item -ItemType Directory -Force "$Target\.codex\skills" | Out-Null
foreach ($SkillName in $SkillNames) {
  Copy-Item "$ApexRoot\.codex\skills\$SkillName" "$Target\.codex\skills\" -Recurse -Force
}

New-Item -ItemType Directory -Force "$Target\.agents" | Out-Null
Copy-Item "$ApexRoot\.agents\*.md" "$Target\.agents\" -Force
```

如果目标项目也是私有仓库，可以提交 `.codex/skills/` 中复制过去的 skills 和 `.agents/`。
其中 `frontend-design`、`gsap-*`、`react-best-practices`、`webapp-testing`、`web-design-guidelines`、`next-best-practices`、`github-solution-research`、`apex-grill-with-docs`、`apex-to-prd` 和 `apex-to-issues` 来自公开仓库，随 ApexPowers 一起 vendored，目标项目安装时不需要再联网下载。

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

如果公开项目也希望保留官方前端、research 和 engineering workflow skills，可以只忽略 `.codex/skills/apex-init-*` 与 `.codex/skills/apex-sync-*`，继续提交 `frontend-design`、`gsap-*`、`react-best-practices`、`webapp-testing`、`web-design-guidelines`、`next-best-practices`、`github-solution-research`、`apex-grill-with-docs`、`apex-to-prd`、`apex-to-issues`。

## 安装到本机 Codex 全局 skills

适合希望同一台机器上的所有 Codex 项目都能使用 Apex skills，但不想把它复制进每个项目仓库。

```powershell
$ApexRoot = "D:\gitdown\ApexPowers"
$CodexHome = "$env:USERPROFILE\.codex"
$SkillNames = @(
  "apex-init-project-agent",
  "apex-init-project-code",
  "apex-init-project-file",
  "apex-sync-agent-mirrors",
  "apex-init-project-hooks",
  "frontend-design",
  "gsap-core",
  "gsap-scrolltrigger",
  "gsap-performance",
  "gsap-timeline",
  "gsap-plugins",
  "gsap-utils",
  "gsap-react",
  "gsap-frameworks",
  "react-best-practices",
  "webapp-testing",
  "web-design-guidelines",
  "next-best-practices",
  "github-solution-research",
  "apex-grill-with-docs",
  "apex-to-prd",
  "apex-to-issues"
)

New-Item -ItemType Directory -Force "$CodexHome\skills" | Out-Null
foreach ($SkillName in $SkillNames) {
  Copy-Item "$ApexRoot\.codex\skills\$SkillName" "$CodexHome\skills\" -Recurse -Force
}
```

全局安装只放在当前机器的用户目录里，不会进入目标项目源码。

## 手动运行初始化脚本

下面命令可以直接从 ApexPowers checkout 运行。把 `$Target` 换成目标项目路径。

生成项目根 `AGENTS.md`、`CLAUDE.md` 和 `.claude/rules`：

```powershell
$ApexRoot = "D:\gitdown\ApexPowers"
$Target = "D:\path\to\your-project"

python "$ApexRoot\.codex\skills\apex-init-project-agent\scripts\init_project_agent.py" "$Target"
python "$ApexRoot\.codex\skills\apex-init-project-agent\scripts\init_project_agent.py" "$Target" --write
```

第一条是 dry run。确认将要创建的文件合理后，再运行带 `--write` 的命令。`AGENTS.md` 是 Codex 核心规则入口，主体等于 `CLAUDE.md` 去掉 `.claude/rules` 按需加载入口后的内容，再追加内联关键硬规则，并从 `api-design.md`、`backend.md`、`frontend.md` 各提炼最多 10 行项目专项硬规则；`CLAUDE.md` 保留 Claude Code 的 `.claude/rules` 分层入口。

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

安装 Codex / Claude Code loop hooks：

```powershell
$CodexHome = "$env:USERPROFILE\.codex"
$ClaudeHome = "$env:USERPROFILE\.claude"

python "$ApexRoot\.codex\skills\apex-init-project-hooks\scripts\init_project_hooks.py" "$Target"
python "$ApexRoot\.codex\skills\apex-init-project-hooks\scripts\init_project_hooks.py" "$Target" `
  --codex-home "$CodexHome" `
  --claude-home "$ClaudeHome" `
  --write
```

第一条是 dry run。默认布局是：hook 配置和 runtime 写到对应 agent 根目录，项目目录只写 loop 状态。

- Codex：`$CodexHome\hooks.json` 与 `$CodexHome\hooks\apex_loop.py`
- Claude Code：`$ClaudeHome\settings.json` 与 `$ClaudeHome\hooks\apex_loop.py`
- 目标项目：`$Target\tasks\loops`、`$Target\tasks\loops\workflow.md`、`$Target\tasks\reviews`、`$Target\tasks\lessons.md`
- Ownership manifest：`$Target\tasks\loops\.apex-manifest.json`、`$CodexHome\apex\manifest.json`、`$ClaudeHome\apex\manifest.json`

已有 `$CodexHome\hooks.json`、`$ClaudeHome\settings.json` 会保留用户 hook，并只替换 Apex 管理的 `apex_loop.py` 条目；既有 hook 脚本没有生成标记时默认跳过。用户明确要求覆盖/刷新时，加 `--force`。

重复安装是幂等的：再次运行同一条 `--write` 命令时，安装器会先移除旧的 Apex 管理条目，再写入当前版本，不会把同一组 hook 重复追加。
如果用户之前用旧版本安装过项目级 hooks，新的 agent-root 安装会迁移清理旧位置：删除项目 `.codex/hooks.json` / `.claude/settings.json` 里的 Apex 条目，并删除带生成标记的项目级 runtime 副本；如果旧配置里混有用户自己的 hook，会保留用户 hook。

安全更新和卸载都走 manifest 边界：

```powershell
python "$ApexRoot\.codex\skills\apex-init-project-hooks\scripts\init_project_hooks.py" "$Target" `
  --codex-home "$CodexHome" `
  --claude-home "$ClaudeHome" `
  --update

python "$ApexRoot\.codex\skills\apex-init-project-hooks\scripts\init_project_hooks.py" "$Target" `
  --codex-home "$CodexHome" `
  --claude-home "$ClaudeHome" `
  --uninstall

python "$ApexRoot\.codex\skills\apex-init-project-hooks\scripts\init_project_hooks.py" "$Target" `
  --codex-home "$CodexHome" `
  --claude-home "$ClaudeHome" `
  --uninstall `
  --write
```

`--update` 是 manifest-aware reinstall；默认 dry run，带 `--write` 才落盘。`--uninstall` 只处理 manifest 记录的 Apex-managed 文件：host JSON 会 scrub Apex hook 条目并保留用户 hook；runtime 文件必须 hash 匹配、带生成标记或显式 `--force` 才删除；`tasks/loops/workflow.md` 与 `tasks/lessons.md` 是用户可编辑状态文件，卸载时默认保留。

`tasks/loops/workflow.md` 使用 `[apex-state:*]...[/apex-state:*]` 状态块。当前 runtime 会推导并注入 `no_task`、`planning`、`implementing`、`review_required`、`validation_required`、`done`；项目可以直接编辑这些状态块来改变 Hook 注入给 agent 的流程提示。

如果你明确想使用旧的项目级 hook 布局，可以加 `--hook-scope project`：

```powershell
python "$ApexRoot\.codex\skills\apex-init-project-hooks\scripts\init_project_hooks.py" "$Target" `
  --hook-scope project `
  --write
```

安装后需要在 Codex 的 `/hooks` 或设置界面 review / trust 新 hook；Claude Code 侧需要确认 agent 根目录的 `settings.json` 被当前项目加载。Loop hooks 只做确定性门禁：危险命令、secrets、写入后行数检查、`.agents` 镜像漂移提醒、Stop review request 与验证证据检查，不会在 hook 脚本里递归启动 agent。

Loop hooks 是 AI 协作时的即时 guardrail，不替代 Git pre-commit、lint、type-check、test 或 CI。提交和合并前仍以项目自己的验证命令和 CI 结果为最终证据。

## 在 Codex 里使用

安装后，在目标项目中可以直接让 Codex 使用这些 skill：

```text
Use apex-init-project-agent to initialize this project.
Use apex-init-project-code to add missing code headers.
Use apex-init-project-file to create missing Agents.md files.
Use apex-sync-agent-mirrors to generate Codex and Claude Code agent mirrors.
Use apex-init-project-hooks to install Codex and Claude Code loop hooks.
Use frontend-design to build or polish web UI.
Use gsap-core for GSAP core animations.
Use gsap-scrolltrigger for scroll-linked GSAP animations.
Use gsap-performance to optimize GSAP animation performance.
Use gsap-timeline to sequence GSAP timelines.
Use gsap-plugins when working with GSAP plugins.
Use gsap-utils when working with gsap.utils helpers.
Use gsap-react when adding GSAP animations to React or Next.js.
Use gsap-frameworks when adding GSAP animations to Vue, Nuxt, Svelte, or SvelteKit.
Use vercel-react-best-practices to review React/Next.js performance patterns.
Use webapp-testing to test local web apps with Playwright.
Use web-design-guidelines to audit UI, UX, and accessibility.
When working in a Next.js project, the next-best-practices skill can be applied automatically from the installed skills.
Use github-solution-research when a concrete engineering problem may already have a proven GitHub solution.
Use apex-grill-with-docs 在实现前先确认最多可问几个后续问题，再只追问会影响项目走向的关键问题，并同步维护 CONTEXT.md / ADR。
Use apex-to-prd 在烤清楚后把对话上下文合成正式 PRD，并创建项目 issue。
Use apex-to-issues 在 PRD 就绪后拆成可独立实现、可验证、按依赖顺序发布的 vertical-slice issues。
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
  .codex\skills\apex-sync-agent-mirrors\scripts\sync_agent_mirrors.py `
  .codex\skills\apex-init-project-hooks\scripts\init_project_hooks.py `
  .codex\skills\apex-init-project-hooks\scripts\apex_loop.py `
  .codex\skills\apex-init-project-hooks\scripts\apex_loop_core.py `
  .codex\skills\apex-init-project-hooks\scripts\apex_loop_routes.py `
  .codex\skills\apex-init-project-hooks\scripts\apex_loop_runtime.py `
  .codex\skills\apex-init-project-hooks\scripts\apex_loop_utils.py
```

修改 hook runtime 后，再运行：

```powershell
python -m unittest tests.test_apex_loop_hooks tests.test_apex_loop_installer
```

提交前删除生成的 `__pycache__` 目录。
