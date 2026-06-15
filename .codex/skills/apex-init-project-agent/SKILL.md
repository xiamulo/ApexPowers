---
name: apex-init-project-agent
description: 初始化已有项目的项目级 AGENTS.md、CLAUDE.md 和 .claude/rules 规则文档。适用于用户希望同时支持 Codex 与 Claude Code 的项目协作规则，且不覆盖已有手写规则文件的场景。
---

# Apex Init Project Agent

## 工作流

运行 `scripts/init_project_agent.py <project-root>`。默认只预览；确认范围合理后，才传入 `--write` 真正写入固定的根 `AGENTS.md`、`CLAUDE.md`，并创建 `.claude/rules/` 目录。

项目根目录 `AGENTS.md` 是 Codex 稳定读取的核心入口，必须使用脚本里的 Codex 固定模板原文。它的主体必须等于当前 `CLAUDE.md` 固定模板去掉 `.claude/rules/ 入口（按需加载）` 后的内容；Codex 硬规则、验证要求、文件拆分阈值和安全边界追加在主体后面，用来替代 AGENTS.md 里的按需加载入口。不要替代、摘要或重写 `CLAUDE.md` 主体其他部分。

`AGENTS.md` 中追加的 `Codex 内联硬规则 / 项目专项硬规则` 下面的 API、Backend、Frontend 三个小节是唯一允许模型回填的 Codex 专项区块。生成或重写 `.claude/rules/api-design.md`、`.claude/rules/backend.md`、`.claude/rules/frontend.md` 后，必须分别把这三份文档中最有效、最硬性的规则压缩到对应小节，每组最多 10 行。只保留会直接影响代码结构、数据边界、错误处理、验证和安全的规则；不要搬运解释、背景或宽泛建议。

项目根目录 `CLAUDE.md` 是 Claude Code 入口，必须使用脚本里的 Claude 固定模板原文，不要总结、改写、删减或重新组织。它保持现有 `.claude/rules/` 分层入口和 Claude 协作风格。

`.claude/rules/*.md` 不能由脚本套模板硬写。脚本只列出缺失的规则文件；你必须读取项目源码、配置、目录结构、README/docs 和已有约定后，再由模型根据真实项目上下文写入 rules 内容。

需要生成的 rules 文件包括：project-structure、never-list、coding-style、api-design、backend、frontend、git-workflow 和 hooks。已有 rules 文件默认不覆盖；只有用户明确要求重写时，才可以改写已有文件。

如果用户明确要求“重新生成 / 重跑 / 覆盖 / 刷新 / regenerate”，就进入重新生成模式：根 `AGENTS.md`、`CLAUDE.md` 必须用固定模板重写，所有 rules 文件也必须重新读取源码后重写，不能因为文件已存在就跳过。使用脚本时传入 `--force`、`--all` 或 `--regenerate` 获取全量 rules 清单。

## rules 写法

每个 rules 文件都必须使用固定的二级标题模板。二级标题只作为结构骨架；读取项目源码后，把具体规则写在对应二级标题下面的三级标题里。

不要把泛泛模板内容直接写在二级标题下面。每条规则都要来自项目真实源码、配置、目录结构、README/docs 或用户明确约定。

固定二级标题模板如下：

```markdown
# project-structure.md
## 何时加载 / When to load（明确触发时机）
## 项目定位 / Project Overview
## 技术栈 / Tech Stack
## 目录结构 / Directory Structure（顶层目录）
## 文件放置原则 / File Placement Rules
## 分形文档纪律

# never-list.md
## 何时加载 / When to load（明确触发时机）
## 绝对不要做 / Never do / NEVER / Forbidden patterns（核心禁止清单）
## 高风险区域 / High-risk areas / Critical files（重点保护区）
## 不确定时的处理 / When in doubt / Escalation（兜底流程）
## 还需要加上这些固定的,6. 明确禁止
"""
1. 不猜测需求。
2. 不把未验证说成已验证。
3. 不擅自增加功能、参数、抽象层或优化项。
4. 不反复追加新的建议或后续方向。
5. 交付结束直接收尾，不使用“如果你要”“如果你愿意”“我还可以继续……”这类引导式扩展语句。
6. 不对自身行为做旁白或解释。做了什么就说什么，不评论自己是否合规。
7. 不为不可能发生的场景做防御性处理。
"""

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
## 权限与鉴权 / Permissions & Auth（未来扩展）
## 兼容性 / Compatibility（schema 与格式兼容）

# backend.md
## 何时加载 / When to load（明确触发时机）
## 当前仓库状态 / Current Repository Status（前端本地编辑器边界）
## 文件大小与服务拆分 / File Size & Service Splitting（后端文件、函数、class/service/module 行数阈值）
## 如果未来新增 Go 后端 / If Future Go Backend Added（目录与集成规则）
## GORM 约定 / GORM Conventions（model / migration / repository 分层）
## JSON 与错误 / JSON & Error（返回结构与日志）
## 配置与日志 / Configuration & Logging（环境变量与隐私保护）
## 与当前前端集成 / Frontend Integration（离线能力与资产保护）

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

# git-workflow.md
## 何时加载 / When to load（明确触发时机）
## 完成前验证清单 / Pre-Commit Validation Checklist（必检项）
## 推荐验证命令 / Recommended Validation Commands（lint/build/dev）
## 手动测试重点 / Manual Testing Focus（关键功能点）
## Git 操作边界 / Git Operation Boundaries（只读与禁止操作）
## 提交信息建议 / Commit Message Guidelines（格式建议）
## 汇报格式 / Reporting Format（完成时汇报模板）

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
```

写每个二级标题时，先补一个或多个三级标题，例如 `### 当前项目约定`、`### 已确认事实`、`### 例外与不适用项`、`### 执行要求`，再把根据源码分析出的具体内容写进去。

生成 `coding-style.md` 的 `文件大小与拆分 / File Size & Splitting` 时，必须根据项目真实语言、框架和现有文件分布写出明确的 AI 编程行数阈值，而不是只写“保持文件短小”。默认按有效代码行计算（排除空行和纯注释）：普通源码文件目标 150-300 行；超过 300 行触发拆分评估；超过 400 行标为高风险；超过 500 行必须拆分或说明原因。函数、方法、hook 或组件主体目标 25-40 行；超过 50 行必须优先拆出 helper、策略对象、子组件或独立模块。class、service 或 module 目标 100-200 行；超过 300 行必须优先拆分。生成文件、vendor、锁文件、快照、fixture、迁移文件和框架约定的大型配置文件可以列为例外，但不能把业务逻辑塞进例外文件逃避拆分。

生成 `frontend.md` 的 `UI 组件 / UI Components` 时，必须写出前端专项拆分规则。默认建议：组件文件（如 `.tsx`、`.jsx`、`.vue`、`.svelte`）目标 200-250 行；300 行作为软上限；超过 300 行应拆出子组件、custom hooks / composables、utils、constants、types 或样式/配置文件；超过 500 行必须视为高风险并说明为什么暂不拆分。Vue SFC 可以按 block 细分：template 目标 150 行以内，script 目标 250 行以内，style 目标 100 行以内。若项目已有 ESLint、Biome、Sonar、review checklist 或 CI 规则，应优先复用现有阈值；如果现有代码大面积超限，先把阈值写成 warning / review trigger，并给出渐进收敛策略，不要要求一次性重写。

生成 `backend.md` 的 `文件大小与服务拆分 / File Size & Service Splitting` 时，必须写出后端专项拆分规则。默认建议：后端源码文件目标 300 行以内；400-500 行作为软上限；超过 500 行必须拆分或说明原因。函数和方法目标 25-40 行；超过 50 行必须优先拆分。class、service、repository、controller 或 module 目标 100-200 行；超过 300 行必须优先拆分。Go、Python、Ruby、Java、Node 等项目应优先复用现有 linter 阈值；没有现成规则时，按 AI 编程默认阈值写入，并把复杂算法、协议生成代码、ORM migration、测试 fixture 和框架 glue code 列为可审查例外。

生成 `hooks.md` 时，必须先检查目标项目是否存在 `.codex/hooks.json`、`.claude/settings.json`、`.codex/hooks/apex_loop.py`、`.claude/hooks/apex_loop.py` 或 `tasks/loops/`。如果已安装 ApexPowers loop hooks，写明当前 hook 入口、route registry、Prompt 只 advisory、Pre/Post/Stop 才 hard gate、failure JSONL 位置、review request 文件和 trust / `/hooks` review 步骤。如果尚未安装，只写“未安装”及可运行的 `apex-init-project-hooks` dry-run / write 命令，不要假装 hook 已生效。

完成 `api-design.md`、`backend.md`、`frontend.md` 后，必须回写根 `AGENTS.md` 的三个专项小节：

- `API 规则（最多 10 行）` 只能来自 `api-design.md`，优先保留接口边界、adapter、store action、错误返回、权限鉴权和兼容性硬规则。
- `Backend 规则（最多 10 行）` 只能来自 `backend.md`，优先保留后端存在性判断、文件拆分、数据访问、JSON/error、配置日志和前后端集成硬规则。
- `Frontend 规则（最多 10 行）` 只能来自 `frontend.md`，优先保留组件拆分、状态分层、Canvas/WebGL、动画、导入保存、请求资源和性能硬规则。

如果对应领域在项目中不存在，不要编造规则；在对应小节写一行 `- 不适用：<基于源码/配置/目录结构的依据>`。

只有在用户明确要求重新生成时，才使用 `--force` 覆盖根 `AGENTS.md`、`CLAUDE.md` 和已有 rules 文件。
