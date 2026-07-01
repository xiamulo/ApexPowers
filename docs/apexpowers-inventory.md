# ApexPowers 详细功能清单

本文是 `docs/apexpowers-detailed-map.svg` 的文字版索引，说明每个主要 skill、Markdown 文档、脚本、模板和测试在项目流程里的作用。

## 根入口

| 文件 | 用途 |
| --- | --- |
| `README.md` | ApexPowers 的安装、复制、手动运行脚本、hook 安装、隐私和维护命令入口。 |
| `NOTICE.md` | 分发 NOTICE。记录 Apex 自有内容、vendored skills 来源组、版本/许可证据和公开发布前置条件。 |
| `.gitattributes` | 统一文本换行策略，降低跨平台 diff 噪音。 |
| `.gitignore` | 排除本地状态、缓存、凭据和 Python 生成文件。 |
| `.codex-plugin/plugin.json` | Codex 薄 plugin manifest。只声明 skills 和界面元数据，不直接安装 hooks。 |
| `.claude-plugin/plugin.json` | Claude Code 薄 plugin manifest。声明 Claude skills 与 command prompt wrappers，不直接安装 hooks。 |
| `.github/workflows/quality.yml` | GitHub Actions quality workflow。运行 Python hook tests、compileall、distribution check、apex-doctor 和 gitleaks secret scan。 |
| `.pre-commit-config.yaml` | 本地 pre-commit 配置。接入官方 `gitleaks` hook，作为提交前 secret 扫描层。 |
| `gitleaks.toml` | Gitleaks 配置。使用默认规则，并允许测试/文档中的假 token fixtures。 |

## Apex 自有 Skills

| Skill | 用途 |
| --- | --- |
| `.codex/skills/apex-session-init-codex/SKILL.md` | Codex 开工初始化。先读目标项目 `AGENTS.md`，再读 `CLAUDE.md`，确认规则后继续当前任务。 |
| `.claude/skills/apex-session-init-claude-code/SKILL.md` | Claude Code 开工初始化。先读 `CLAUDE.md`，再读 `AGENTS.md`，确保 Claude 侧也遵守项目规则。 |
| `.codex/skills/apex-init-project-agent/SKILL.md` | 初始化目标项目根规则。脚本写固定 `AGENTS.md` / `CLAUDE.md` 骨架，并列出 `.claude/rules/*.md` 目标；rules 正文必须由 agent 读真实源码后生成。 |
| `.codex/skills/apex-init-project-code/SKILL.md` | 扫描缺少标准头部注释的源码文件。最终 `@purpose/@scope/@deps/@exports/@invariants` 由 agent 根据真实代码写入。 |
| `.codex/skills/apex-init-project-file/SKILL.md` | 扫描缺少目录级 `FOLDER.md` 的文件夹。每个目录说明控制在极简范围，用来给 agent 快速定位目录职责。 |
| `.codex/skills/apex-sync-agent-mirrors/SKILL.md` | 从 `.agents/*.md` 源模板生成官方 Codex `.toml` 和 Claude Code `.md` 子智能体镜像。 |
| `.codex/skills/apex-init-project-hooks/SKILL.md` | 安装 Apex loop hooks。默认把 host 配置和 runtime 放进 Codex / Claude agent root，把 loop 状态留在目标项目。 |
| `.codex/skills/apex-doctor/SKILL.md` | 只读健康检查入口。检查 core skills、agent mirrors、hook manifests、runtime/config、workflow state 和 git status。 |
| `.codex/skills/apex-lean-review/SKILL.md` | 反过度工程审查入口。显式检查可删除代码、stdlib/native 替代、YAGNI 抽象和依赖收缩机会。 |
| `.codex/skills/apex-grill-with-docs/SKILL.md` | 需求烤问工作流。先确认用户最多愿意回答多少问题，再只追问影响项目走向的问题，并维护 `CONTEXT.md` / ADR。 |
| `.codex/skills/apex-to-prd/SKILL.md` | 把已讨论清楚的上下文、领域术语和架构决定整理成正式 PRD，并发布到 issue tracker。 |
| `.codex/skills/apex-to-issues/SKILL.md` | 把 PRD / spec / plan 拆成可独立实现、可验证、按依赖顺序发布的 vertical-slice issues。 |

## Apex 自有 Skill 附属文档

| 文件 | 用途 |
| --- | --- |
| `.codex/skills/apex-grill-with-docs/CONTEXT-FORMAT.md` | 需求烤问时维护 `CONTEXT.md` 的格式模板，用于沉淀领域术语、约束和已确认事实。 |
| `.codex/skills/apex-grill-with-docs/ADR-FORMAT.md` | 架构决策记录模板，用于记录重要方案选择、背景、取舍和影响范围。 |
| `.codex/skills/*/agents/openai.yaml` | 对应 skill 的 OpenAI agent 元配置，供 skill 安装/分发时保留调用面信息。 |

## 分发层与跨宿主文档

| 文件 | 用途 |
| --- | --- |
| `docs/apex-agent-portability.md` | ApexPowers 跨宿主适配矩阵。区分 skill-capable、command-capable、lifecycle-hook-capable 和 instruction-only 宿主。 |
| `docs/apex-parallel-delivery-orchestration.md` | worktree / issue / PR 级并行交付编排协议。串起 6 个角色模板、官方 agent 镜像、`apex-to-issues` 和显式 review gate。 |
| `docs/platform-native-solutions.md` | 平台原生能力清单。供 `apex-lean-review` 和 reviewer 判断是否需要依赖、抽象或自定义实现。 |
| `docs/supply-chain-trust-security.md` | 供应链、hook trust、威胁模型、生成文件 provenance、update/uninstall 破坏性边界、无遥测和 secret/path guard false-positive 策略。 |
| `docs/supply-chain-manifest.sha256` | trust-critical 分发文件的 byte-level SHA-256 manifest，用于 release review 漂移检测。 |
| `commands/apex-doctor.toml` | host command prompt wrapper，引导只读运行 apex-doctor。 |
| `commands/apex-init-project-hooks.toml` | host command prompt wrapper，引导 dry-run / install loop hooks。 |
| `commands/apex-sync-agent-mirrors.toml` | host command prompt wrapper，引导从 `.agents` 重新生成 Codex / Claude mirrors。 |
| `commands/apex-lean-review.toml` | host command prompt wrapper，引导过度工程审查。 |
| `commands/apex-orchestrate-delivery.toml` | host command prompt wrapper，引导显式编排 worktree / issue / PR 级并行交付。 |
| `scripts/check_apex_distribution.py` | 分发一致性检查。验证 plugin manifests、commands、portability 文档、platform-native 文档、lean skill、benchmark 方法和 trust-critical artifact hashes。 |
| `benchmarks/README.md` | ApexPowers 离线 benchmark 方法说明，明确不复用 Ponytail 结论。 |
| `benchmarks/apex_distribution_benchmark.py` | 离线测量 distribution check、doctor、installer dry-run 和 route config render 的耗时。 |

## 子智能体源模板与镜像

| 文件 | 用途 |
| --- | --- |
| `.agents/Agents.md` | `.agents` 目录说明。强调 `.agents/*.md` 是私有源模板，不是官方运行时自动加载路径。 |
| `.agents/planner.md` | 规划型子智能体。把非平凡任务拆成 `tasks/todo+任务名.md`，定义目标、步骤、风险和验证。 |
| `.agents/implementer.md` | 执行型子智能体。按已批准计划精确改代码，不重新规划、不做审查。 |
| `.agents/developer.md` | 综合开发型子智能体。处理明确的小到中等规模实现、bug 修复和 reviewer 反馈修正。 |
| `.agents/code-reviewer.md` | 审查型子智能体。只报告质量、安全、可维护性、性能和项目规则问题，不改代码。 |
| `.agents/perf-optimizer.md` | 性能分析子智能体。聚焦 React 重渲染、WebGL/Canvas、大数组、大图处理和卡顿问题。 |
| `.agents/researcher.md` | 研究型子智能体。负责代码、文档、第三方库和外部资料调研，只输出结论。 |
| `.codex/agents/*.toml` | 从 `.agents/*.md` 生成的 Codex custom agent 镜像，包含 `name`、`description`、`developer_instructions`、sandbox 和 reasoning 配置。 |
| `.claude/agents/*.md` | 从 `.agents/*.md` 生成的 Claude Code subagent 镜像，包含 YAML frontmatter、工具和 MCP 偏好。 |

## 初始化与同步脚本

| 脚本 | 用途 |
| --- | --- |
| `init_project_agent.py` | 写固定根 `AGENTS.md` / `CLAUDE.md`，创建 `.claude/rules` 目录，并输出需要 agent 生成的 rules 文件清单。 |
| `init_code_headers.py` | 扫描支持的源码文件，列出缺少标准头部注释的目标；默认不替用户写内容。 |
| `init_agents_md.py` | 扫描目标项目目录，列出缺少 `FOLDER.md` 的目录；默认只列缺失目录。 |
| `sync_agent_mirrors.py` | 解析 `.agents` frontmatter 和正文，渲染 Codex TOML / Claude Markdown 镜像；有生成标记才自动覆盖。 |
| `init_project_hooks.py` | 规划、安装、更新和卸载 hook runtime、host JSON、manifest、loop 状态目录；保护用户已有 hook。 |
| `apex_loop.py` | hook runtime 命令入口。把当前目录加入 `sys.path` 后调用核心 dispatcher。 |
| `apex_loop_core.py` | 兼容导出层。暴露 `HostConfigRenderer`、`RouteRegistry` 和 `main`。 |
| `apex_loop_routes.py` | Route registry 与 host config 渲染源头。定义 SessionStart、UserPromptSubmit、PreToolUse 分流、PostToolUse、PostToolBatch、PreCompact、Stop 路由。 |
| `apex_loop_runtime.py` | 运行时 guard 实现。包含写前安全门禁、PostToolUse security-required 反馈、行数门禁、secret 内容检查、镜像漂移检查、PreCompact snapshot，以及默认停用的 strict review/validation gate 实现。 |
| `apex_loop_utils.py` | HookInput、HookContext、路径规范化、workflow 状态推导、active.json 任务选择、结构化 review 文件读写、guard cache、失败日志去重和辅助函数。 |

## Hook 模板与安装产物

| 文件或目标 | 用途 |
| --- | --- |
| `.codex/skills/apex-init-project-hooks/templates/codex-hooks.json` | Codex hook 配置模板参考。实际安装时由 route registry 渲染。 |
| `.codex/skills/apex-init-project-hooks/templates/claude-settings.json` | Claude Code settings 模板参考。实际安装时由 route registry 渲染。 |
| `<codex-home>/config.toml` | Codex host hook 配置。安装器写入 Apex 托管 TOML block，并保留用户配置。 |
| `<codex-home>/hooks.json` | 旧 Codex JSON hook 配置兼容路径，仅在显式 `--codex-config-format json` 或旧项目级布局时使用。 |
| `<codex-home>/hooks/apex_loop*.py` | Codex 侧 runtime 副本。 |
| `<claude-home>/settings.json` | Claude Code host hook 配置，安装器合并 Apex 条目并保留用户 hook。 |
| `<claude-home>/hooks/apex_loop*.py` | Claude Code 侧 runtime 副本。 |
| `tasks/loops/workflow.md` | 可编辑 workflow 状态文档，定义 `[apex-state:no_task]`、`planning`、`implementing`、`security_required`、`review_required`、`validation_required`、`done`。 |
| `tasks/loops/.apex-manifest.json` | 项目侧 ownership manifest，记录 Apex 管理的文件、hash 和保护属性。 |
| `tasks/loops/active.json` | 可选 active task 索引。并行任务时用 `owned_paths` 选择 review slug，避免绑定“最新 todo”。 |
| `tasks/loops/security-required.json` | PostToolUse 发现已写入 secret-like 内容后的清理状态；存在时 Stop 阻塞完成。 |
| `tasks/loops/session-snapshot.json` | PreCompact 生成的会话快照，保存 workflow、active task、diff hash、review path 和 blockers。 |
| `<codex-home>/apex/manifest.json` | Codex host 侧 ownership manifest。 |
| `<claude-home>/apex/manifest.json` | Claude host 侧 ownership manifest。 |

## 需求与任务文档

| 文件 | 用途 |
| --- | --- |
| `tasks/todo+apex-loop-hooks.md` | 当前 Apex loop hooks 改造计划，记录目标、非目标、架构、hook 规则、阶段计划和 DoD。 |
| `tasks/todo+apex-ponytail-production.md` | 从 Ponytail 借鉴分发层做法的生产化计划，覆盖跨宿主、薄 manifest、lean review、平台原生清单、漂移测试和 benchmark 方法。 |
| `tasks/reviews/apex-loop-hooks.md` | 显式 review / strict workflow 的 review 文件。结构化 frontmatter 使用 YAML，旧 TOML 兼容读取；默认 Stop 不再读取它作为完成门禁。 |
| `tasks/research+trellis-apexpowers-opportunities.md` | 对 Trellis 方案的源码对照研究，记录 ApexPowers 可借鉴模块和不建议照搬的部分。 |
| `tasks/lessons.md` | loop hooks 注入的近期经验记录来源。 |
| `tasks/loops/apex-loop-hooks/state.json` | 机器可读 loop 状态，记录 phase、changed files/hash、Stop blocker hash 和 continuation 计数；review attempts 字段仅兼容旧 strict gate。 |

## Vendored 前端 / 动画 / 测试 Skills

| Skill | 用途 |
| --- | --- |
| `frontend-design` | 生成或打磨高质量 Web UI，强调视觉层次、真实可用界面和非模板化设计。 |
| `webapp-testing` | 用 Playwright 验证本地 Web 应用，支持截图、日志、元素定位和静态 HTML 自动化。 |
| `web-design-guidelines` | 审查 UI、UX、accessibility 和 Web interface guidelines。 |
| `next-best-practices` | Next.js App Router、RSC、路由、数据获取、资源优化和部署实践。 |
| `vercel-react-best-practices` | React / Next.js 性能优化规则，覆盖 waterfalls、bundle、server/client、rerender、rendering 和 JS 性能。 |
| `github-solution-research` | 从 GitHub 仓库、issues、PR、讨论和示例中找可复用工程解法。 |
| `gsap-core` | GSAP 基础 tween、easing、stagger、defaults 和 matchMedia。 |
| `gsap-scrolltrigger` | ScrollTrigger、pinning、scrub、parallax 和滚动驱动动画。 |
| `gsap-performance` | GSAP 动画性能优化，避免 layout thrash，优先 transform/opacity。 |
| `gsap-timeline` | GSAP timeline、position 参数、嵌套和播放控制。 |
| `gsap-plugins` | GSAP 插件注册和 ScrollTo、Flip、Draggable、SplitText、SVG、physics 等插件。 |
| `gsap-utils` | `gsap.utils` 工具，如 clamp、mapRange、random、snap、toArray、wrap。 |
| `gsap-react` | React / Next.js 中使用 `useGSAP`、refs、context 和 cleanup。 |
| `gsap-frameworks` | Vue、Nuxt、Svelte、SvelteKit 等非 React 框架中的 GSAP 生命周期和清理。 |

## GitHub Solution Research 文档

| 文件 | 用途 |
| --- | --- |
| `.codex/skills/github-solution-research/README.md` | 该 skill 的独立说明和使用入口。 |
| `.codex/skills/github-solution-research/references/extraction-playbook.md` | 从开源项目中提取可落地解法的操作手册。 |
| `.codex/skills/github-solution-research/references/research-rubric.md` | 判断问题证据和项目证据质量的评分/取舍标准。 |

## Next.js Best Practices 文档

| 文件 | 用途 |
| --- | --- |
| `async-patterns.md` | 异步、并发和避免 waterfall 的模式。 |
| `bundling.md` | bundle 大小、动态导入和依赖拆分。 |
| `data-patterns.md` | 数据获取、缓存和请求组织。 |
| `debug-tricks.md` | Next.js 调试技巧。 |
| `directives.md` | `use client`、`use server` 等指令边界。 |
| `error-handling.md` | error boundary、not-found 和异常处理。 |
| `file-conventions.md` | App Router 文件约定。 |
| `font.md` | 字体加载和优化。 |
| `functions.md` | Next.js 导航和框架函数。 |
| `hydration-error.md` | hydration mismatch 诊断和修复。 |
| `image.md` | 图片优化和 `next/image`。 |
| `metadata.md` | metadata、OG image 和 SEO 数据。 |
| `parallel-routes.md` | parallel routes 和 intercepting routes。 |
| `route-handlers.md` | route handlers 的设计与错误处理。 |
| `rsc-boundaries.md` | React Server Components 边界。 |
| `runtime-selection.md` | Node / Edge runtime 选择。 |
| `scripts.md` | script 加载策略。 |
| `self-hosting.md` | Next.js 自托管注意事项。 |
| `suspense-boundaries.md` | Suspense 边界放置和相关 hook 要求。 |

## React Best Practices 规则文档

`react-best-practices/rules/*.md` 每个文件是一条原子性能/工程规则。按前缀分组如下：

| 分组 | 文件 | 用途 |
| --- | --- | --- |
| advanced | `advanced-effect-event-deps.md`, `advanced-event-handler-refs.md`, `advanced-init-once.md`, `advanced-use-latest.md` | 高阶 hooks、effect event、稳定 callback 和一次性初始化。 |
| async | `async-api-routes.md`, `async-cheap-condition-before-await.md`, `async-defer-await.md`, `async-dependencies.md`, `async-parallel.md`, `async-suspense-boundaries.md` | 异步并发、避免 waterfall、延迟 await 和 Suspense 策略。 |
| bundle | `bundle-analyzable-paths.md`, `bundle-barrel-imports.md`, `bundle-conditional.md`, `bundle-defer-third-party.md`, `bundle-dynamic-imports.md`, `bundle-preload.md` | bundle 可分析性、barrel import、动态导入和第三方脚本推迟。 |
| client | `client-event-listeners.md`, `client-localstorage-schema.md`, `client-passive-event-listeners.md`, `client-swr-dedup.md` | 客户端事件监听、localStorage schema、滚动性能和 SWR 去重。 |
| js | `js-batch-dom-css.md`, `js-cache-function-results.md`, `js-cache-property-access.md`, `js-cache-storage.md`, `js-combine-iterations.md`, `js-early-exit.md`, `js-flatmap-filter.md`, `js-hoist-regexp.md`, `js-index-maps.md`, `js-length-check-first.md`, `js-min-max-loop.md`, `js-request-idle-callback.md`, `js-set-map-lookups.md`, `js-tosorted-immutable.md` | JavaScript 层面的循环、缓存、DOM 读写批处理、集合查找和非关键工作推迟。 |
| rendering | `rendering-activity.md`, `rendering-animate-svg-wrapper.md`, `rendering-conditional-render.md`, `rendering-content-visibility.md`, `rendering-hoist-jsx.md`, `rendering-hydration-no-flicker.md`, `rendering-hydration-suppress-warning.md`, `rendering-resource-hints.md`, `rendering-script-defer-async.md`, `rendering-svg-precision.md`, `rendering-usetransition-loading.md` | 渲染、hydration、SVG、resource hints、script 加载和 transition loading。 |
| rerender | `rerender-defer-reads.md`, `rerender-dependencies.md`, `rerender-derived-state-no-effect.md`, `rerender-derived-state.md`, `rerender-functional-setstate.md`, `rerender-lazy-state-init.md`, `rerender-memo-with-default-value.md`, `rerender-memo.md`, `rerender-move-effect-to-event.md`, `rerender-no-inline-components.md`, `rerender-simple-expression-in-memo.md`, `rerender-split-combined-hooks.md`, `rerender-transitions.md`, `rerender-use-deferred-value.md`, `rerender-use-ref-transient-values.md` | 降低 React rerender、收窄依赖、memo、derived state、transition 和 ref 使用。 |
| server | `server-after-nonblocking.md`, `server-auth-actions.md`, `server-cache-lru.md`, `server-cache-react.md`, `server-dedup-props.md`, `server-hoist-static-io.md`, `server-no-shared-module-state.md`, `server-parallel-fetching.md`, `server-parallel-nested-fetching.md`, `server-serialization.md` | Server Components、Server Actions、缓存、并行数据获取、序列化和 request 安全。 |
| authoring | `_sections.md`, `_template.md` | 规则文档分区和新增规则模板。 |

## Webapp Testing 附属文件

| 文件 | 用途 |
| --- | --- |
| `webapp-testing/scripts/with_server.py` | 启动一个或多个本地 server，等待端口就绪后执行测试命令。 |
| `webapp-testing/examples/static_html_automation.py` | 静态 HTML 自动化示例。 |
| `webapp-testing/examples/element_discovery.py` | 元素发现和定位示例。 |
| `webapp-testing/examples/console_logging.py` | 浏览器 console 日志采集示例。 |

## 测试

| 文件 | 用途 |
| --- | --- |
| `tests/test_apex_loop_hooks.py` | 验证 hook runtime 路由、上下文注入、安全门禁、行数门禁、secrets、镜像漂移和默认 Stop 不强制 review/validation。 |
| `tests/test_apex_loop_installer.py` | 验证 hook installer 的 agent-root 默认安装、项目级兼容、JSON 合并、幂等、update、uninstall、manifest 和 legacy migration。 |
| `tests/test_apex_doctor.py` | 验证 apex-doctor 的只读健康检查和 manifest/config/runtime 一致性判断。 |
| `tests/test_apex_distribution.py` | 验证 plugin manifests、commands、跨宿主文档、lean skill、platform-native 清单和 benchmark 方法没有漂移。 |
