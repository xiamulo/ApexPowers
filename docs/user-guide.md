# ApexPowers 使用指南

这份文档写给“我已经有一个项目，想让 Codex / Claude Code 更懂这个项目、少犯低级错、需要时还能用专门 skill 干活”的用户。

ApexPowers 可以理解成三件事：

- 一包给 Codex / Claude Code 用的 skills：比如初始化项目规则、做需求烤问、拆 issue、审查过度工程、检查前端质量。
- 一套可同步的子智能体角色：比如 planner、researcher、developer、code-reviewer。
- 一组可选的 loop hooks：在 agent 工作时做即时提醒和门禁，比如危险命令、疑似 secret、review gate、验证证据。

它不是项目框架，也不是 CI 的替代品。它更像一套“让 AI 协作更守规矩”的工具箱。

## 先从哪个 profile 装起

如果你只想先用起来，推荐从 `core` 开始：

```powershell
.\apex.ps1 install D:\path\to\your-project --profile core --target codex,claude --write
.\apex.ps1 doctor D:\path\to\your-project
```

`core` 会安装最基础的一组能力：开工读规则、初始化项目规则、补代码头注释、补目录说明、同步 agent mirrors、健康检查。它不会安装 hooks，所以风险最低。

如果你确定要完整私有工作流，可以装 `full`：

```powershell
.\apex.ps1 install D:\path\to\your-project --profile full --target codex,claude --write
.\apex.ps1 doctor D:\path\to\your-project
```

`full` 包含 planning、research、frontend、quality、gsap、hooks 等全部能力。因为 hooks 会写入 Codex / Claude Code 的用户级配置，第一次用建议先 dry run：

```powershell
.\apex.ps1 install D:\path\to\your-project --profile full --target codex,claude
.\apex.ps1 install D:\path\to\your-project --profile full --target codex,claude --write
```

常用 profile 可以这样理解：

| Profile | 适合什么时候用 |
| --- | --- |
| `core` | 新项目接入 ApexPowers，先把项目规则、目录说明、agent 镜像和健康检查跑起来。 |
| `hooks` | 已经接入 core，想加 loop hooks 做安全提醒、review gate 和验证 gate。 |
| `planning` | 需求还没完全清楚，想先烤问、写 PRD、拆 issue。 |
| `research` | 遇到具体工程难题，想从 GitHub 项目、issue、PR 里找成熟做法。 |
| `frontend` | 做 Web UI、React / Next.js、浏览器验证、UI/UX 审查。 |
| `quality` | 做性能、可访问性、SEO、Web 质量、过度工程审查。 |
| `gsap` | 项目里有 GSAP 动画，尤其是时间线、滚动动画、React/Vue/Svelte 集成。 |
| `full` | 私有项目全量接入，想把 ApexPowers 当完整协作工具箱用。 |

查看当前有哪些 profile：

```powershell
.\apex.ps1 profile list
.\apex.ps1 profile show full
```

## 日常怎么喊它

安装后，在 Codex 里可以直接点名 skill，例如：

```text
Use apex-session-init-codex before starting work.
Use apex-doctor to check ApexPowers installation health.
Use apex-grill-with-docs 帮我把这个需求烤清楚。
Use apex-lean-review review 一下当前 diff 有没有过度工程。
```

在 Claude Code 里，开工初始化入口是：

```text
/apex-session-init-claude-code
```

更口语一点也可以。重点是把 skill 名字说出来，agent 就知道应该按对应工作流执行。

## 新项目第一次接入

新项目建议按这个顺序走：

1. 安装 `core`。
2. 跑 `apex doctor` 看安装是否完整。
3. 用 `apex-init-project-agent` 生成项目根规则。
4. 用 `apex-init-project-file` 给关键目录补 `Agents.md`。
5. 用 `apex-init-project-code` 给缺少说明的源码文件补标准头注释。
6. 用 `apex-sync-agent-mirrors` 生成 Codex / Claude Code 可识别的 agent 镜像。
7. 如果项目协作已经稳定，再考虑装 `hooks` 或 `full`。

对应可以这样对 Codex 说：

```text
Use apex-init-project-agent to initialize this project.
Use apex-init-project-file to create missing Agents.md files.
Use apex-init-project-code to add missing source file headers.
Use apex-sync-agent-mirrors to generate Codex and Claude Code agent mirrors.
Use apex-doctor to verify the installation.
```

这几个初始化 skill 都偏保守：默认会先看真实项目，不会随便覆盖已有手写规则。你如果明确想覆盖或强制刷新，要把“覆盖”“force”“重新生成”说清楚。

## 每次开工前

如果目标项目已经有 `AGENTS.md` / `CLAUDE.md`，开工前用：

```text
Use apex-session-init-codex before starting this task.
```

它做的事很简单：先读项目规则，再继续当前任务。适合这些场景：
- 新建了一个对话窗口
- 换了一个项目。
- 长时间没碰这个项目。
- 项目规则刚改过。
- 你觉得 agent 可能没读项目上下文。

Claude Code 侧用 `/apex-session-init-claude-code`，逻辑类似，只是优先读 `CLAUDE.md`。

## 需求还不清楚时

用 `apex-grill-with-docs`。

它适合“我有一个想法，但还没变成可实现需求”的阶段。它会先问你最多愿意回答几个后续问题，然后只追问会影响方向的关键问题，并把上下文沉淀到 `CONTEXT.md` 和 ADR。

可以这样说：

```text
Use apex-grill-with-docs 帮我梳理这个功能，我最多回答 5 个问题。
```

等需求聊清楚后，用 `apex-to-prd`：

```text
Use apex-to-prd 把刚才讨论整理成 PRD。
```

PRD 准备好后，用 `apex-to-issues`：

```text
Use apex-to-issues 把这个 PRD 拆成可以独立实现和验收的 issues。
```

简单判断：

- 还在想：`apex-grill-with-docs`
- 已经聊清楚，要形成正式产品文档：`apex-to-prd`
- 已经有 PRD/spec，要拆给实现：`apex-to-issues`

## 做实现时

小到中等规模的明确任务，通常不需要你手动指定子智能体，直接让 Codex 做就行。

如果你要显式分工，可以参考 `.agents` 里的角色：

| 角色 | 适合做什么 |
| --- | --- |
| `researcher` | 查代码、查文档、查第三方方案，只输出结论，不改代码。 |
| `planner` | 把非平凡任务拆成计划、风险和验证步骤。 |
| `developer` | 处理中小规模实现、bug fix、根据 review 反馈修正。 |
| `implementer` | 按已经批准的计划精确落代码，不重新规划。 |
| `code-reviewer` | 做代码审查，找 bug、风险、缺测试，不改代码。 |
| `perf-optimizer` | 查性能问题，比如 React 重渲染、Canvas/WebGL、大数组、大图片卡顿。 |

如果是一个 PR 级、多个 issue、多个 worktree 的交付，用 `apex-orchestrate-delivery`：

```text
Use apex-orchestrate-delivery to coordinate this PR-sized rollout.
```

它适合比较大的交付：先把 slice、依赖、负责人角色、worktree/branch、验证命令和 review gate 列清楚，再推进。不要拿它处理一行 bug fix，那会太重。

## 想减少“写复杂了”

用 `apex-lean-review`。

它不是普通代码审查，而是专门问这些问题：

- 有没有不必要的抽象？
- 有没有能删掉的层？
- 有没有为了未来假设写的 YAGNI 代码？
- 有没有可以用平台原生能力、标准库或已有项目工具替代的自定义实现？
- 有没有没必要引入的新依赖？

适合这样用：

```text
Use apex-lean-review review 当前 diff，重点看有没有过度工程和可以用平台原生能力替代的地方。
```

注意它不会建议你删掉安全、校验、可访问性、测试和明确需求需要的代码。它的目标是减复杂度，不是把质量门砍掉。

## Web / React / Next.js 项目

如果你在做前端，可以按目标选：

| 你要做什么 | 用哪个 skill |
| --- | --- |
| 从零做一个更像产品的页面或组件 | `frontend-design` |
| 测本地 Web 应用、看截图、查 console | `webapp-testing` |
| 审查 UI/UX/accessibility 是否靠谱 | `web-design-guidelines` |
| Next.js App Router、RSC、路由、metadata、图片字体优化 | `next-best-practices` |
| React / Next.js 性能、rerender、bundle、waterfall | `react-best-practices` |
| 整站质量审查，包含性能、SEO、a11y、best practices | `web-quality-audit` |
| 专门做可访问性 | `accessibility` |
| 专门做性能 / 加载速度 | `performance` 或 `core-web-vitals` |
| 专门做 SEO | `seo` |
| 安全、兼容性、现代 Web 最佳实践 | `best-practices` |

常见说法：

```text
Use frontend-design to polish this dashboard UI.
Use webapp-testing to verify the local app in browser.
Use web-design-guidelines to audit this page.
Use react-best-practices to review this React component for performance issues.
Use next-best-practices for this Next.js route handler and RSC boundary.
```

## GSAP 动画

GSAP 相关 skill 可以组合用：

| 场景 | 用哪个 skill |
| --- | --- |
| 普通 tween、stagger、easing | `gsap-core` |
| 滚动动画、pin、scrub、parallax | `gsap-scrolltrigger` |
| 动画卡顿、掉帧、layout thrash | `gsap-performance` |
| 多段动画编排、时间线、播放控制 | `gsap-timeline` |
| Flip、Draggable、ScrollTo、SplitText、SVG 等插件 | `gsap-plugins` |
| clamp、mapRange、snap、toArray 等工具函数 | `gsap-utils` |
| React / Next.js 里用 GSAP | `gsap-react` |
| Vue / Nuxt / Svelte / SvelteKit 里用 GSAP | `gsap-frameworks` |

比如：

```text
Use gsap-react and gsap-scrolltrigger to add a scroll animation to this Next.js page.
Use gsap-performance to review this animation jank.
```

## 遇到工程难题

用 `github-solution-research`。

它适合很具体的问题，比如：

- 某个库集成失败。
- 某个报错看起来很多人踩过。
- 你想参考开源项目怎么做同类功能。
- 你想确认某个方案是不是主流做法。

可以这样说：

```text
Use github-solution-research to find proven GitHub solutions for this Vite plugin error.
```

它的输出应该是可落地的工程结论，而不是泛泛搜索摘要。

## Hooks 什么时候装

先说结论：新项目不要一上来就装 hooks。建议先装 `core`，等项目规则、目录文档、agent mirrors 都稳定后再装。

hooks 适合这些场景：

- 你经常让 agent 连续改代码，希望它在危险动作前被拦一下。
- 你想强制要求 review/validation gate。
- 你想在 `.agents` 改了但 mirrors 没同步时收到提醒。
- 你想记录 loop 状态，让 agent 更清楚当前任务阶段。

安装：

```powershell
.\apex.ps1 hooks install D:\path\to\your-project
.\apex.ps1 hooks install D:\path\to\your-project --write
.\apex.ps1 doctor D:\path\to\your-project
```

第一条是预览，第二条才写入。默认会把 hook runtime 和配置写到 Codex / Claude Code 的用户级目录，把项目状态写到 `tasks/loops`。

hooks 不是 CI，也不是 pre-commit。提交前还是要跑项目自己的 lint、type-check、test。

## 健康检查和更新

装完、同步完、或者觉得哪里不对，先跑：

```powershell
.\apex.ps1 doctor D:\path\to\your-project
```

想看机器可读结果：

```powershell
.\apex.ps1 doctor D:\path\to\your-project --json
```

更新已安装 profile：

```powershell
.\apex.ps1 update D:\path\to\your-project --write
```

卸载 ApexPowers 管理的文件：

```powershell
.\apex.ps1 uninstall D:\path\to\your-project
.\apex.ps1 uninstall D:\path\to\your-project --write
```

默认仍然是先预览，带 `--write` 才落盘。

## 公开项目和私有项目的区别

ApexPowers 当前定位是私有工具箱。私有项目可以把复制进去的 `.codex/skills`、`.claude/skills`、`.agents`、`commands` 一起提交，方便团队复用。

如果目标项目会公开，建议谨慎：

- 优先用全局安装，不把 ApexPowers 私有内容复制进公开仓库。
- 或者把 `.codex/skills/apex-*`、`.claude/skills/apex-*`、`.agents/`、`.codex/agents/`、`.claude/agents/` 加进 `.gitignore`。
- 不要把 token、凭据、本机路径、`.env`、`.serena/` 提交进去。

公开项目如果只想保留公开来源的前端、GSAP、Next.js、测试类 skills，可以只提交那些 vendored public skills，不提交 Apex 自有的私有 workflow skills。

## 一个简单选择表

| 你现在想做的事 | 推荐入口 |
| --- | --- |
| 第一次接入项目 | `apex install --profile core` |
| 检查安装是否正常 | `apex doctor` / `apex-doctor` |
| 开工前让 agent 读项目规则 | `apex-session-init-codex` 或 `/apex-session-init-claude-code` |
| 生成项目根规则 | `apex-init-project-agent` |
| 补源码文件头说明 | `apex-init-project-code` |
| 补目录说明 | `apex-init-project-file` |
| 同步 Codex / Claude 子智能体 | `apex-sync-agent-mirrors` |
| 需求还没清楚 | `apex-grill-with-docs` |
| 把讨论整理成 PRD | `apex-to-prd` |
| 把 PRD 拆成 issues | `apex-to-issues` |
| 大型交付编排 | `apex-orchestrate-delivery` |
| 找 GitHub 上成熟解法 | `github-solution-research` |
| 做 Web UI | `frontend-design` |
| 测本地 Web 应用 | `webapp-testing` |
| 审查 UI/UX/a11y | `web-design-guidelines` |
| Next.js 最佳实践 | `next-best-practices` |
| React/Next 性能 | `react-best-practices` |
| 整站质量 | `web-quality-audit` |
| 反过度工程审查 | `apex-lean-review` |
| GSAP 动画 | `gsap-*` 系列 |
| 安装 loop hooks | `apex-init-project-hooks` 或 `apex hooks install` |

## 最推荐的使用方式

日常最稳的节奏是：

1. 新项目先 `core`，不要急着全量。
2. 先让 agent 读规则，再让它动手。
3. 需求不清楚时先烤问，不要直接实现。
4. 大功能先 PRD，再拆 issue，再实现。
5. 做完以后用 review / validation / doctor 收尾。
6. hooks 作为协作护栏，不要把它当最终质量证明。

一句话总结：ApexPowers 的价值不是“多装几个 skill”，而是把需求、计划、实现、审查、验证和项目规则串成一个更不容易跑偏的协作流程。
