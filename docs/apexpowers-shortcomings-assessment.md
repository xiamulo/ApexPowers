# ApexPowers Shortcomings Assessment

评估日期：2026-06-20

范围：本评估只核对当前仓库源码、文档、manifest、commands、tests 和 benchmark harness。没有重新核验外部 Codex 官方文档；用户给出的官方表述只作为评估背景，不作为本文件证据。

重要前提：当前工作区包含大量未提交和未跟踪的生产化改动。本文件把这些当前文件视为事实状态来评估，因为它们正是分发、doctor、benchmark 和跨宿主支持相关资产。

## 总结

一句话结论：这 5 个短板大多是真实的，但第 1 点和第 5 点需要拆开看。ApexPowers 已经从“零散脚本”推进到了“私有生产分发层”：有 thin plugin manifests、command wrappers、manifest-aware installer、doctor、distribution checker、离线 reliability benchmark 和对应测试。它还不是社区级产品分发，也没有 profile 化、MCP server、跨 host adapter、worktree/PR orchestration、真实任务效果 benchmark。

| # | 短板 | 判定 | 已经做了的部分 | 仍然真实的缺口 |
| --- | --- | --- | --- | --- |
| 1 | 安装和分发还不像产品 | 部分真实 | 已有 installer dry-run/write/update/uninstall、doctor、thin plugin manifests、commands、distribution checker、tests | 默认安装仍是复制 skills 和跑脚本；没有 npx/pipx/marketplace/plugin install/profile install/update channel/release artifact |
| 2 | 31 个 Codex skills 有膨胀风险 | 真实 | 仓库清楚记录当前 31 个 skills，也有 private/public 项目的提交建议 | 没有 profile manifest 或默认最小包；`.codex-plugin` 暴露整个 `./.codex/skills/` |
| 3 | MCP 和外部系统弱 | 真实 | agent 模板和镜像保留 MCP 使用规则；跨宿主矩阵已经标注状态 | Generic MCP host 是 Planned；Claude plugin `mcpServers` 为空；OpenCode/Gemini/Copilot/Cursor/Windsurf 多为 Planned 或 instruction fallback |
| 4 | 缺少 worktree/issue/PR 级并行交付协议 | 基本真实 | 有 6 个角色模板、官方 agent 镜像、`apex-to-issues` issue 拆分、显式 review gate | 没有显式 orchestration command；没有 worktree/branch/PR/merge/rollback 协议和测试 |
| 5 | benchmark 没证明“效果” | 真实，但这是当前 benchmark 的明确设计 | 已有 distribution reliability benchmark，且刻意避免虚假节省声明 | 没有 task pass rate、review catch rate、false positive、time-to-green、token cost、rollback rate 等 outcome 指标 |

## 1. 安装和分发

判定：部分真实。

已经做了：

- `README.md` 已记录 `apex-doctor` 只读检查，覆盖 core skills、agent mirrors、hook manifests、host runtime/config、workflow state 和 git status。
- `apex-init-project-hooks` 已支持 dry-run、`--write`、agent-root 默认安装、legacy project scope、Codex `config.toml`、Claude `settings.json`、manifest ownership、`--update` 和 `--uninstall`。
- `.codex-plugin/plugin.json` 和 `.claude-plugin/plugin.json` 已经是 thin manifests：声明 skills/commands/metadata，不直接声明 hooks。
- `commands/*.toml` 已经提供 `apex-doctor`、`apex-init-project-hooks`、`apex-sync-agent-mirrors`、`apex-lean-review` 四个 prompt wrapper。
- `scripts/check_apex_distribution.py` 会检查必需分发资产、plugin manifests、commands、portability doc、platform-native doc、lean skill、benchmark method 和 README/inventory drift。
- `tests/test_apex_loop_installer.py` 覆盖 dry-run JSON、agent-root 安装、manifest、update、uninstall、legacy migration、用户 hook 保留、modified managed file 保守处理。
- `tests/test_apex_distribution.py` 覆盖当前分发通过、缺资产失败、plugin manifests 不直接安装 hooks。

仍然真实的缺口：

- `README.md` 的主安装路径仍是 PowerShell `Copy-Item` 复制 `.codex/skills`、`.claude/skills`、`.agents`，再运行各类脚本。
- 当前没有社区用户期望的一条命令安装入口，例如 `npx apexpowers install`、`pipx install apexpowers`、marketplace install、Codex plugin install、Claude plugin install。
- 当前没有 profile install。无论核心 workflow、frontend、GSAP、SEO/performance/accessibility，默认仍在同一个 skill tree。
- 当前没有版本发布、升级通道、卸载入口的顶层 CLI 契约。hook installer 有 `--update`/`--uninstall`，但它只是 hook 层，不是整个 ApexPowers 包的 package manager。
- `.codex-plugin/plugin.json` 仍标注 `UNLICENSED`、`private` 语义，适合私有分发，不适合社区分发。

建议下一步：

- 增加一个顶层安装 CLI 或 plugin command 层，明确 `install`、`doctor`、`update`、`uninstall`、`profile install`。
- 把 hook installer 保持为低层实现，把顶层 CLI 作为用户入口。
- 发布最小 smoke test：全新空目录内一条命令安装、doctor 通过、卸载后只保留用户状态文件。

## 2. 31 个 Codex skills 膨胀风险

判定：真实。

已经做了：

- 当前 `.codex/skills` 实际存在 31 个 skill。
- `docs/apexpowers-skills-agents-hooks.md` 明确记录“当前实际存在 31 个 Codex skill”。
- `README.md` 已提醒公开项目或客户项目优先用全局安装，或把私有 Apex skills / agents 加进 `.gitignore`。

仍然真实的缺口：

- `.codex-plugin/plugin.json` 的 `skills` 字段指向整个 `./.codex/skills/`，没有默认最小 profile。
- 当前没有 `core`、`frontend`、`motion`、`web-quality`、`product-planning` 等 profile manifest。
- 当前没有 progressive disclosure 策略文档来说明默认只暴露哪些 skill，扩展包何时安装。
- Web quality、GSAP、frontend、Next/React 最佳实践和 Apex core 混在一个默认树里，确实适合离线私用，不适合默认社区分发。

建议 profile：

- `apexpowers-core`：session init、project agent/file/code init、agent mirror sync、hook installer、doctor、lean review。
- `apexpowers-product`：grill、to-prd、to-issues。
- `apexpowers-frontend`：frontend-design、react/next best practices、webapp-testing、web-design-guidelines。
- `apexpowers-motion`：gsap core/frameworks/react/scrolltrigger/timeline/plugins/performance/utils。
- `apexpowers-web-quality`：accessibility、best-practices、core-web-vitals、performance、seo、web-quality-audit。

## 3. MCP 和外部系统

判定：真实。

已经做了：

- `.agents/*.md` 和 `.codex/agents/*.toml` 里保留 MCP 使用规则和 MCP 偏好。
- `docs/apex-agent-portability.md` 已列出 Codex、Claude Code、OpenCode、Gemini / Antigravity CLI、GitHub Copilot CLI、Cursor、Windsurf、Cline、Kiro、CodeWhale、Generic MCP host 的支持矩阵。
- `scripts/check_apex_distribution.py` 会检查 portability doc 是否覆盖 OpenCode、Gemini、GitHub Copilot、Cursor、Windsurf、MCP 等 host 关键词。

仍然真实的缺口：

- `docs/apex-agent-portability.md` 把 Generic MCP host 标成 Planned，目标是未来 `apex-mcp/` stdio server。
- `docs/apexpowers-skills-agents-hooks.md` 也把 Generic MCP host 标成 Planned，只说未来可暴露 doctor、skill index、workflow state 等只读上下文。
- `.claude-plugin/plugin.json` 的 `mcpServers` 是空对象。
- `.codex/agents/*.toml` 里的 MCP 信息是 prompt-level preference，并注明需要在真实 `.codex/config.toml` 或 agent TOML 中配置 endpoint。
- OpenCode、Gemini / Antigravity CLI、GitHub Copilot CLI、Cursor、Windsurf、Cline、Kiro 大多仍是 Planned 或 instruction fallback。

建议下一步：

- 增加 `apex-mcp` 只读 stdio server，先暴露 `doctor`、`skill_index`、`workflow_state`、`agent_mirror_status`。
- 为 MCP server 写 contract tests：initialize、tools/list、tools/call、无写入副作用、错误 JSON。
- 把 OpenCode/Cursor/Windsurf 这类 host adapter 作为独立 profile，不和 Codex/Claude hook 生命周期混用。

## 4. Worktree / Issue / PR 并行交付协议

判定：基本真实。

已经做了：

- `.agents/Agents.md` 有调度原则：少量高质量 agent，主上下文负责分派和综合，子智能体只处理清晰窄范围任务并交回结构化摘要或文件产物。
- `.agents` 下已有 planner、implementer、developer、code-reviewer、perf-optimizer、researcher 等角色模板。
- `apex-sync-agent-mirrors` 可以把 `.agents` 源模板生成 Codex / Claude 官方 agent 镜像。
- `apex-to-issues` 能把 PRD/spec/计划拆成可独立实现、可验证、按依赖发布的 vertical-slice issues，并发布到 issue tracker。
- hook runtime 的 Stop gate 能创建 review request，并阻止缺少 review/validation evidence 的结束路径。

仍然真实的缺口：

- 没有 `commands/apex-orchestrate.toml`、`commands/apex-worktree-plan.toml` 或类似显式 orchestration command。
- 当前协议没有规定什么时候开 worktree、怎么命名 branch/worktree、派几个 agent、如何收集结果、如何处理冲突、怎样 merge、怎样回滚。
- `apex-to-issues` 只负责 issue 拆分和发布，不负责 issue -> worktree -> agent -> PR -> CI/review -> merge。
- 当前测试没有覆盖 worktree 创建、PR 创建、CI 回写、review feedback loop、rollback。

建议下一步：

- 写 `docs/apex-orchestration-protocol.md`，先把 issue/worktree/branch/PR/merge/rollback 的状态机定下来。
- 新增 `commands/apex-orchestrate.toml`，只做规划和显式用户确认，不隐式启动多个 agent。
- 后续再加脚本层：`plan`、`spawn`、`collect`、`validate`、`merge`、`rollback`。每一步都写 dry-run 和状态文件。

## 5. Benchmark 是否证明效果

判定：真实，但当前 benchmark 本来就没有声称证明效果。

已经做了：

- `benchmarks/README.md` 明确说当前只测 ApexPowers distribution 和 guardrail paths，不复用 Ponytail 结果，也不声称节省 lines、tokens、cost 或 time。
- 当前 benchmark cells 包括 `scripts/check_apex_distribution.py --json`、isolated `apex-doctor`、`apex-init-project-hooks` dry-run JSON、Codex TOML route config render、Claude JSON route config render。
- `benchmarks/apex_distribution_benchmark.py` 输出每个 cell 的 `elapsed_ms`、return code、min/median/max。
- `scripts/check_apex_distribution.py` 的 benchmark method check 只验证 benchmark 文件存在且 framing 是 Apex-only measurement。

仍然真实的缺口：

- 没有真实任务语料或 repo-level benchmark corpus。
- 没有 task pass rate。
- 没有 review catch rate。
- 没有 validation false positive / false negative 指标。
- 没有 time-to-green。
- 没有 token cost。
- 没有 rollback rate。
- 没有人审/自动混合 evaluation harness。

建议下一步：

- 把当前 benchmark 命名继续保持为 `distribution reliability benchmark`，不要扩大宣传。
- 新增独立 `benchmarks/task_effectiveness/`，用小型真实仓库任务集开始。
- 每个 task 至少记录：baseline、Apex route/profile、expected patch、tests、review oracle、time-to-green、tokens、是否 rollback。
- 先跑 5 到 10 个内部任务，不急着公开对比，只证明 measurement harness 能稳定复现。

## 已做资产清单

这些资产可以作为“不是零散脚本”的证据：

| 资产 | 当前作用 |
| --- | --- |
| `.codex-plugin/plugin.json` | Codex thin plugin manifest，指向 `.codex/skills/`，不声明 hooks |
| `.claude-plugin/plugin.json` | Claude Code thin plugin manifest，指向 `.claude/skills/` 和 `commands/`，`mcpServers` 为空 |
| `commands/*.toml` | command-capable host 的 prompt wrappers |
| `.codex/skills/apex-init-project-hooks/scripts/init_project_hooks.py` | manifest-aware hook installer，支持 dry-run/write/update/uninstall |
| `.codex/skills/apex-doctor/scripts/apex_doctor.py` | 目标项目安装健康检查 |
| `scripts/check_apex_distribution.py` | ApexPowers 源仓库分发一致性检查 |
| `benchmarks/apex_distribution_benchmark.py` | 离线 distribution reliability benchmark |
| `tests/test_apex_loop_installer.py` | hook installer contract tests |
| `tests/test_apex_doctor.py` | doctor contract tests |
| `tests/test_apex_distribution.py` | 分发资产 contract tests |
| `docs/apex-agent-portability.md` | 跨宿主能力矩阵和 adapter 原则 |
| `docs/apexpowers-skills-agents-hooks.md` | skills、agents、hooks 的当前架构说明 |

## 优先级建议

| 优先级 | 工作 | 原因 |
| --- | --- | --- |
| P0 | Profile 化默认分发 | 31 skills 膨胀风险会直接影响 Codex 初始上下文和社区安装体验 |
| P0 | 顶层安装/更新/卸载 CLI 或 plugin command | 这是从私有工具包到产品分发的最大缺口 |
| P1 | `apex-mcp` 只读 server | 能把 Apex 从本地 markdown 状态推进到可被外部工具按需查询的上下文系统 |
| P1 | Orchestration protocol 文档和 command wrapper | 先定义 issue/worktree/PR/merge/rollback 契约，再实现自动化 |
| P2 | Task effectiveness benchmark | 当前 reliability benchmark 先保留，效果评估另起一套，避免指标混淆 |

## 最终判断

用户列出的短板不是“你完全没做”，而是“当前已经做到私有生产可用的一部分，但还没做到社区顶级产品形态”。

最不真实的说法是“安装和分发只是脚本”：现在已经有 manifest、commands、doctor、distribution check、tests 和 reliability benchmark。

最真实的短板是 profile 化、MCP server、worktree/PR orchestration、task effectiveness benchmark。这四项目前在仓库里要么明确 Planned，要么只有角色/规则/文档方法，没有可运行产品闭环。
