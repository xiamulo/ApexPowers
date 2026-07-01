---
name: apex-init-project-agent
description: 初始化已有项目的项目级 AGENTS.md、CLAUDE.md 和 .claude/rules 规则文档。适用于用户希望同时支持 Codex 与 Claude Code 的项目协作规则，且不覆盖已有手写规则文件的场景。
---

# Apex Init Project Agent

## 工作流

运行 `scripts/init_project_agent.py <project-root>`。默认只预览；确认范围合理后，才传入 `--write` 真正写入固定的根 `AGENTS.md`、`CLAUDE.md`，并创建 `.claude/rules/` 目录。

项目根目录 `AGENTS.md` 是 Codex 稳定读取的核心入口，必须使用脚本里的 Codex 固定模板原文。它的主体必须等于当前 `CLAUDE.md` 固定模板去掉 `.claude/rules/ 入口（按需加载）` 后的内容；Codex 硬规则、验证要求、文件拆分阈值和安全边界追加在主体后面，用来替代 AGENTS.md 里的按需加载入口。不要替代、摘要或重写 `CLAUDE.md` 主体其他部分。

根 `AGENTS.md` / `CLAUDE.md` 固定模板必须内置“契约式小任务 + 运行时结构化分解 + 证据化验收”工作流。该规则属于根级硬规则，不放到 `.claude/rules/` 才生效，也不得由模型在生成 rules 时自由发挥。修改该工作流时，必须同步更新 `scripts/init_project_agent.py` 中的 `CLAUDE_TEMPLATE`；如需 Codex 额外强调，再同步更新 `CODEX_RULE_APPENDIX`。模板中的 YAML contract 示例使用中文 key，例如 `任务ID`、`目标`、`范围`、`允许路径`、`禁止路径`、`验收`、`必跑检查`、`交付证据`、`需要审查`；如果未来接入脚本解析，这些 key 必须保持稳定。

Subagent 派发规则也是根级硬规则：主 agent 不得用 `fork_turns: "all"` 把完整主上下文传给子智能体，必须手写最小子任务包，并列出该 Slice 需要阅读的 md 文档；子智能体必须被明确标注为叶子执行者，不能再 spawn / fork / 调度新的 Subagent。修改这条规则时，必须同步更新 `scripts/init_project_agent.py` 的 `CLAUDE_TEMPLATE` 与 `CODEX_RULE_APPENDIX`、`.agents/*.md` 源模板以及对应测试。

`AGENTS.md` 中追加的 `Codex 内联硬规则 / 项目专项硬规则` 下面的 API、Backend、Frontend 三个小节是唯一允许模型回填的 Codex 专项区块。生成或重写 `.claude/rules/api-design.md`、`.claude/rules/backend.md`、`.claude/rules/frontend.md` 后，必须分别把这三份文档中最有效、最硬性的规则压缩到对应小节，每组最多 10 行。只保留会直接影响代码结构、数据边界、错误处理、验证和安全的规则；不要搬运解释、背景或宽泛建议。

项目根目录 `CLAUDE.md` 是 Claude Code 入口，必须使用脚本里的 Claude 固定模板原文，不要总结、改写、删减或重新组织。它保持现有 `.claude/rules/` 分层入口和 Claude 协作风格。

`.claude/rules/*.md` 不能由脚本套模板硬写。脚本只列出缺失的规则文件；你必须读取项目源码、配置、目录结构、README/docs 和已有约定后，再由模型根据真实项目上下文写入 rules 内容。

需要生成的 rules 文件包括：project-structure、never-list、coding-style、api-design、backend、frontend、git-workflow 和 hooks。已有 rules 文件默认不覆盖；只有用户明确要求重写时，才可以改写已有文件。

如果用户明确要求“重新生成 / 重跑 / 覆盖 / 刷新 / regenerate”，就进入重新生成模式：根 `AGENTS.md`、`CLAUDE.md` 必须用固定模板重写，所有 rules 文件也必须重新读取源码后重写，不能因为文件已存在就跳过。使用脚本时传入 `--force`、`--all` 或 `--regenerate` 获取全量 rules 清单。

## rules 写法

每个 rules 文件都必须使用固定二级标题模板；二级标题只作为结构骨架。生成内容前必须先阅读真实源码、配置、目录结构、README/docs、CI/hook/linter 配置或用户明确约定，再把具体规则写到对应二级标题下的三级标题中。

不得把泛泛模板内容直接写在二级标题下面。每条规则必须来自项目事实或用户约定；没有证据时只写 `### 不适用 / Not applicable`，不得按经验、路径名、未来可能性或常见项目形态脑补规则。

路径相关 rules 文件必须优先使用 `.claude/rules` 的 `paths` frontmatter。正文中的 `何时加载 / When to load` 只解释触发语义，不能替代 frontmatter。

每条规则必须归类为以下之一：

- `Hard rule`: 来自用户明确约定、CI、linter、hook、配置、安全边界或真实架构约束。
- `Review trigger`: 启发式审查触发条件，例如文件过大、复杂度升高、职责混杂；不要求一次性重写历史代码。
- `Project fact`: 从源码、配置、目录结构或文档确认的事实；不得自动扩展成新需求。
- `Not applicable`: 当前项目未发现相关事实；不得补充建议或未来规划。

能标注来源时，规则句末使用 `(source: path)` 简短标明依据，例如 `(source: package.json, vite.config.ts, src/stores/)`。不得伪造来源。

生成任何 rules 文件前，必须完成最小证据扫描：

- 项目元数据：`package.json`、lockfile、`tsconfig`、Vite/Next/Nuxt 配置、ESLint/Biome/Prettier、README/docs。
- 目录结构：顶层目录、`src/`、`app/`、`packages/`、`services/`、`server/`、`api/`、`components/`、`stores/`、`hooks/`、`utils/` 等实际存在路径。
- 前端证据：React/Vue/Svelte/Next/Vite/Tailwind/Canvas/WebGL/store/router/import-save-load 相关文件。
- 后端证据：`go.mod`、`pyproject.toml`、`requirements.txt`、`Gemfile`、`pom.xml`、`server/`、`api/`、`internal/`、`cmd/`、`migrations/`、`repository/`、`service/`、`controller/` 等实际存在路径。
- hooks 证据：`.claude/settings.json`、`.codex/hooks.json`、`.claude/hooks/**`、`.codex/hooks/**`、`tasks/loops/**`。
- CI/验证证据：`.github/workflows/`、`Makefile`、`justfile`、`turbo`、`nx`、package scripts、pre-commit 配置。

写每个二级标题时，必须先补一个或多个三级标题，再写具体内容。优先使用：
```markdown
### 已确认事实
### 执行要求
### Review trigger
### 例外与不适用项
### 不适用 / Not applicable
```

```markdown
# project-structure.md

## 何时加载 / When to load（明确触发时机）
## 项目定位 / Project Overview
## 技术栈 / Tech Stack
## 目录结构 / Directory Structure（顶层目录）
## 文件放置原则 / File Placement Rules
## 分形文档纪律
```

生成要求：

- 只写影响 agent 决策的项目定位、技术栈、顶层目录、关键入口和禁止误放区域。
- 不生成完整文件树。
- 不把文件名列表伪装成架构规则。
- 目录职责、边界或关键入口变化时，才更新本文件。
- 分形文档纪律必须说明根 `AGENTS.md`、根 `CLAUDE.md`、目录级 `AGENTS.md`、`.claude/rules`、源码头部注释的职责边界。
- `AGENTS.md` 用于跨 agent 通用规则；`CLAUDE.md` 用于 Claude 专属补充或导入；`.claude/rules` 用于路径级规则；源码头部只放局部语义摘要和不变量。


# never-list.md
## 何时加载 / When to load（明确触发时机）
## 绝对不要做 / Never do / NEVER / Forbidden patterns（核心禁止清单）
## 高风险区域 / High-risk areas / Critical files（重点保护区）
## 不确定时的处理 / When in doubt / Escalation（兜底流程）
## 明确禁止 / Explicit Prohibitions
```
生成要求：
- 本文件可作为全局规则加载，但必须极短。
- 禁止清单优先来自用户明确约定、仓库安全边界、CI/hook/linter、README/docs。
- 不得把普通偏好写成绝对禁止。
- 高风险区域必须来自真实路径或真实配置，例如 auth、billing、db migration、secrets、hooks、CI、deployment、file upload、permission、payment、model weight、production config 等。
- 不确定时的处理必须具体，例如先读文件、先查配置、先运行最窄验证、先报告无法确认项；不得写空泛建议。
固定加入以下用户级禁止项：

```markdown
### 用户明确约定
- 不猜测需求。
- 不把未验证说成已验证。
- 不擅自增加功能、参数、抽象层或优化项。
- 不反复追加新的建议或后续方向。
- 交付结束直接收尾，不使用“如果你要”“如果你愿意”“我还可以继续……”这类引导式扩展语句。
- 不对自身行为做旁白或解释。做了什么就说什么，不评论自己是否合规。
- 不为不可能发生的场景做防御性处理。
```


# coding-style.md
## 何时加载 / When to load（明确触发时机）
## 基本风格 / Basic Style（命名、import、复用约定）
## 文件大小与拆分 / File Size & Splitting（单文件行数阈值、拆分原则与例外）
## 源码文件头注释 / Source File Header Comments（@tag 格式要求）
## 目录 claude.md / Directory AGENTS.md（分形文档纪律）
## React 约定 / React Conventions（hooks、render 优化）
## 状态更新约定 / State Update Conventions（store action 规则）
## 错误处理 / Error Handling（用户可见错误与日志）
## 注释原则 / Commenting Principles（保留与噪音控制）

# api-design.md
## 何时加载 / When to load（明确触发时机）
## 当前项目实际边界 / Current Project Boundaries（本仓库 API 范围）
## 接口分类 / Interface Classification（UI / Store / IO / 渲染 / 格式）
## Adapter 原则 / Adapter Principles（外部格式转换规则）
## Store action 设计 / Store Action Design（action 命名与批量规则）
## 错误返回 / Error Returns（错误格式与处理）
## 权限与鉴权 / Permissions & Auth（仅在已发现时填写）
## 兼容性 / Compatibility（schema 与格式兼容）
生成要求：
- 只写当前仓库真实存在的 API、adapter、store action、IO、渲染、格式转换、权限鉴权和兼容性规则。
- 不得假设项目存在后端 API、远程服务、鉴权系统或数据库。
- `当前项目实际边界` 必须明确：本仓库是否只有前端本地逻辑、是否有后端服务、是否有真实网络 API、是否有外部格式导入/导出。
- `Adapter 原则` 只在发现外部格式转换、第三方协议、导入/导出、schema 转换、DTO/domain mapping 时填写。
- `Store action 设计` 只在发现 store、state manager、action、mutation、reducer、zustand/redux/pinia 等证据时填写。
- `权限与鉴权` 仅在发现 auth、permission、token、session、role、policy、middleware 等真实证据时填写；否则写 `Not applicable`。
- `错误返回` 不得发明统一错误格式；只能来自现有代码、配置、测试或用户约定。


# backend.md
## 何时加载 / When to load（明确触发时机）
## 当前仓库状态 / Current Repository Status（前端本地编辑器边界）
## 文件大小与服务拆分 / File Size & Service Splitting（后端文件、函数、class/service/module 行数阈值）
## 如果未来新增 Go 后端 / If Future Go Backend Added（目录与集成规则）
## GORM 约定 / GORM Conventions（model / migration / repository 分层）
## JSON 与错误 / JSON & Error（返回结构与日志）
## 配置与日志 / Configuration & Logging（环境变量与隐私保护）
## 与当前前端集成 / Frontend Integration（离线能力与资产保护）
生成要求：

- 必须先判断当前仓库是否真实存在后端。
- 未发现后端时，`当前仓库状态` 写明“未发现后端服务证据”，其他后端专项标题写 `Not applicable`，不得生成 Go/GORM/ORM/API/鉴权规则。
- 不再写“如果未来新增 Go 后端”；未来规划必须来自用户明确要求。
- 检测到 `go.mod`、`gorm.io/gorm`、`cmd/`、`internal/`、`pkg/` 等证据后，才可写 Go/GORM 相关规则。
- 检测到 Python/Ruby/Java/Node 后端后，按真实技术栈写对应规则。
- 数据访问约定只在发现 ORM、repository、migration、query builder、model/schema 等证据时填写。

# frontend.md
## 何时加载 / When to load（明确触发时机）
## 当前前端栈 / Current Frontend Stack（技术栈与注意事项）
## UI 组件 / UI Components（组件放置、职责划分与前端文件拆分）
## Tailwind 与主题 / Tailwind & Theming（样式与主题约定）
## 状态分层 / State Layering（store 分层与持久 vs 运行态）
## Canvas / WebGL 交互 / Canvas & WebGL Interaction（画布交互与 GPU 管理）
## 动画 / Animation（动画模式、draft pose 与插值规则）
## 导入/保存/加载 / Import Save Load（PSD、.stretch 与资源重建）
## 请求与外部资源 / Requests & External Resources（本地优先与降级路径）
## 性能 / Performance（渲染优化与 selector 粒度）
生成要求：

- 必须先确认当前前端栈，例如 React/Vue/Svelte/Next/Vite/Tailwind/store/router/Canvas/WebGL。
- 未发现相关技术时，对应标题写 `Not applicable`，不得生成模板化规则。
- `Canvas / WebGL`、`动画`、`导入/保存/加载` 只有在项目真实存在相关文件、依赖、类型、函数或用户约定时填写。
- `请求与外部资源` 必须基于真实 fetch/axios/request/client/import/export/storage/file API 使用情况。
- `性能` 必须基于真实渲染路径、selector、memo、Canvas/WebGL、large list、asset rebuild 等证据。

# git-workflow.md
## 何时加载 / When to load（明确触发时机）
## 完成前验证清单 / Pre-Commit Validation Checklist（必检项）
## 推荐验证命令 / Recommended Validation Commands（lint/build/dev）
## 手动测试重点 / Manual Testing Focus（关键功能点）
## Git 操作边界 / Git Operation Boundaries（只读与禁止操作）
## 提交信息建议 / Commit Message Guidelines（格式建议）
## 汇报格式 / Reporting Format（完成时汇报模板）
生成要求：

- 本文件属于工作流参考规则，不应无条件塞入所有上下文。
- 推荐验证命令必须来自真实配置，例如 package scripts、Makefile、justfile、CI workflow、README。
- 没有证据时不得发明 `npm test`、`pnpm lint`、`go test`、`pytest` 等命令。
- Git 操作边界必须写清楚只读与禁止操作。
- 默认不得自动执行 commit、push、reset、rebase、checkout、clean、stash pop、force push 等可能破坏用户工作区的操作。
- 汇报格式只写必要内容：改了什么、验证了什么、未验证什么、风险或后续人工检查点。
- 不得在交付末尾追加引导式扩展话术。

# hooks.md
## 何时加载 / When to load（明确触发时机）
## 已安装 Hook / Installed Hooks（Codex 与 Claude Code 配置入口）
## Route Registry / Route Registry（事件、matcher、handler 的唯一事实源）
## Prompt / Edit / Stop 边界（advisory 与 hard gate 分层）
## 结构化失败输出 / Structured Failures（guard、reason、fix、failure_class、run_id）
## 行数门禁 / Line Length Guard（warning 与 hard block）
## Review Loop / Review Loop（tasks/reviews 与 Stop gate）
## 安全门禁 / Security Guard（危险命令、secrets、疑似 token）
## 与 pre-commit / CI 的关系（即时 guardrail 与最终验证）
生成要求：
- 必须先检查目标项目是否存在：
  - `.codex/hooks.json`
  - `.claude/settings.json`
  - `.codex/hooks/apex_loop.py`
  - `.claude/hooks/apex_loop.py`
  - `tasks/loops/`
  - `.github/workflows/`
  - `.pre-commit-config.yaml`
- 如果已安装 ApexPowers loop hooks，写明：
  - 当前 hook 入口。
  - route registry 位置。
  - 哪些事件只 advisory。
  - 哪些事件可作为 hard gate。
  - failure JSONL 位置。
  - review request 文件位置。
  - trust / `/hooks` review 步骤。
- 如果尚未安装，只写“未安装 / 未启用”及可运行的 `apex-init-project-hooks --dry-run` / `apex-init-project-hooks --write` 命令；不得假装 hook 已生效。
- `UserPromptSubmit` / Prompt 类 hook 只能写作提示注入、预检或 advisory。
- 只有能返回阻断信号、非零退出码或被 CI/pre-commit 强制执行的 hook，才能写成 hard gate。
- 未检测到 hook 配置文件或入口脚本时，必须写“未安装/未启用”，不得写“已保护/已拦截/已生效”。
- `Prompt / Edit / Stop 边界` 必须区分自然语言提醒、tool-level guard、Stop gate、pre-commit、CI。
- `结构化失败输出` 只有在发现真实 JSONL、schema、guard runner 或 hook 输出约定时填写。
- `行数门禁` 只有在发现真实 guard、lint rule、review loop 或用户约定时写 hard block；否则只能写 review trigger。
- `安全门禁` 必须基于真实 hook、secret scanner、CI、pre-commit 或用户约定；不得假装危险命令、secrets、疑似 token 已被自动拦截。

---
每个二级标题下面不得直接写正文，必须先写三级标题。优先使用：
- `### 已确认事实`
- `### 执行要求`
- `### Review trigger`
- `### 例外与不适用项`

没有真实证据时，只能写：
`### 不适用 / Not applicable`
- 未在当前项目源码、配置、README/docs 或用户约定中发现相关事实；不得补充建议或未来规划。

生成 `coding-style.md` 的 `文件大小与拆分 / File Size & Splitting` 时，不要重复前端或后端专项阈值，而要只写全项目通用的拆分原则、有效代码行计算口径和例外规则。默认按有效代码行计算，排除空行和纯注释。具体文件、组件、函数、class、service、controller、repository、module 等行数阈值，应分别写入 `frontend.md` 或 `backend.md`。`coding-style.md` 只负责说明：文件过大时必须触发 review；拆分应优先按职责、可测试性、依赖边界和可读性进行；生成文件、vendor、锁文件、快照、fixture、迁移文件和框架约定的大型配置文件可以列为例外，但不能把业务逻辑塞进例外文件逃避拆分。如果现有代码大面积超限，应把超限写成 warning / review trigger，并给出渐进收敛策略，不要求一次性重写。

生成 `frontend.md` 的 `UI 组件 / UI Components` 时，必须写出前端专项拆分规则。默认建议：组件文件（如 `.tsx`、`.jsx`、`.vue`、`.svelte`）目标 200-250 行；300 行作为 review trigger；超过 300 行应优先拆出子组件、custom hooks / composables、utils、constants、types 或样式/配置文件；超过 500 行必须视为高风险并说明为什么暂不拆分。组件文件过大时应优先检查是否混合了展示结构、状态管理、副作用、数据转换、交互策略、样式配置、类型定义或大型常量。Vue SFC 可以按 block 细分：template 目标 150 行以内，script 目标 250 行以内，style 目标 100 行以内。不要为了追求小文件把强耦合的 UI 流程机械拆碎；拆分后必须保持数据流清晰、props 数量可控、命名能表达业务意图。如果项目已有 ESLint、Biome、Sonar、review checklist 或 CI 规则，应优先复用现有阈值；如果现有代码大面积超限，先把超限作为 warning / review trigger，新代码和被修改代码优先向该规则收敛。

生成 `backend.md` 的 `文件大小与服务拆分 / File Size & Service Splitting` 时，必须写出后端专项拆分规则。默认建议：后端源码文件目标 300 行以内；400-500 行作为软上限；超过 500 行必须拆分或说明原因。函数和方法目标 25-40 行；超过 50 行必须优先拆出 helper、策略对象、validator、mapper、query builder 或独立 service。class、service、repository、controller、resolver、job 或 module 目标 100-200 行；超过 300 行必须优先拆分。拆分优先按业务能力、数据访问边界、事务边界、外部 API 边界和可测试性进行，不要把多个业务流程堆进同一个 service。Go、Python、Ruby、Java、Node 等项目应优先复用现有 linter 阈值；没有现成规则时，按 AI 编程默认阈值写入，并把复杂算法、协议生成代码、ORM migration、测试 fixture 和框架 glue code 列为可审查例外。

生成 `hooks.md` 时，必须先检查目标项目是否存在 `.codex/hooks.json`、`.claude/settings.json`、`.codex/hooks/apex_loop.py`、`.claude/hooks/apex_loop.py` 或 `tasks/loops/`。如果已安装 ApexPowers loop hooks，写明当前 hook 入口、route registry、Prompt 只 advisory、Pre/Post/Stop 才 hard gate、failure JSONL 位置、review request 文件和 trust / `/hooks` review 步骤。如果尚未安装，只写“未安装”及可运行的 `apex-init-project-hooks` dry-run / write 命令，不要假装 hook 已生效。

完成 `api-design.md`、`backend.md`、`frontend.md` 后，必须回写根 `AGENTS.md` 的三个专项小节：
回写要求：
- `API 规则` 最多 10 行，只能来自 `api-design.md`。
- `Backend 规则` 最多 10 行，只能来自 `backend.md`。
- `Frontend 规则` 最多 10 行，只能来自 `frontend.md`。
- 没有 marker 时，追加创建 marker 区块。
- 已有 marker 时，只替换 marker 内内容。
- 不得重写 marker 外人工维护内容。
- 不得把没有证据的 `Not applicable` 内容提升为根规则。
- 根摘要优先保留 hard rule，其次 review trigger；普通 project fact 只在影响 agent 决策时保留。
- 三个专项小节必须短、准、可执行，避免把专项 rules 文件全文搬运到根 `AGENTS.md`。

`API 规则` 优先保留：

- 当前仓库 API 边界。
- adapter 边界。
- store action 约定。
- 错误返回约定。
- 权限鉴权规则。
- schema / 格式兼容规则。

`Backend 规则` 优先保留：

- 后端存在性判断。
- 后端文件/服务拆分规则。
- 数据访问边界。
- JSON/error 约定。
- 配置与日志安全规则。
- 与前端集成边界。

`Frontend 规则` 优先保留：

- 组件拆分规则。
- 状态分层。
- Canvas/WebGL 规则。
- 动画规则。
- 导入/保存/加载规则。
- 请求与外部资源规则。
- 性能规则。

## 跳过与排除范围

生成 rules、目录摘要或源码头部注释时，默认跳过：

- `node_modules/`
- `vendor/`
- `dist/`
- `build/`
- `coverage/`
- `.next/`
- `.nuxt/`
- `.turbo/`
- `.cache/`
- generated 文件
- minified 文件
- lockfile
- snapshot
- fixture
- 自动生成类型文件
- 自动生成 migration
- 编译产物
- 第三方复制代码

不得为了满足模板覆盖率去修改生成文件、vendor 文件、构建产物或锁文件。

如果对应领域在项目中不存在，不要编造规则；在对应小节写一行 `- 不适用：<基于源码/配置/目录结构的依据>`。

只有在用户明确要求重新生成时，才使用 `--force` 覆盖根 `AGENTS.md`、`CLAUDE.md` 和已有 rules 文件。
