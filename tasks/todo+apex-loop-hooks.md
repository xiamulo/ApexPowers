# Task: ApexPowers Loop Hooks 改造计划

## 目标

把 ApexPowers 从“规则 / skill / agent 模板包”升级为“可安装的项目级 loop 门禁包”：在目标项目中同时生成 Claude Code 与 Codex 可识别的 hook 配置和脚本，把现有提示词规则中的硬约束落成可执行检查。

## 非目标

- 不替代现有 `apex-init-project-agent` / `apex-init-project-code` / `apex-init-project-file` / `apex-sync-agent-mirrors` 的职责。
- 不把模型判断类工作全部塞进 hook；hook 只做确定性检查、状态记录、触发 review loop。
- 不在第一版实现后台 daemon、长期调度器或无限自动修复循环。
- 不默认执行破坏性修复、提交、推送或外部付费操作。

## 当前代码事实

- `README.md` 当前定义 ApexPowers 是私有 Codex skill 包，用于初始化 agent 上下文、规则文档、文件头注释和目录说明。
- `.agents/*.md` 是 source templates；`.codex/agents/*.toml` 和 `.claude/agents/*.md` 是由 `apex-sync-agent-mirrors` 生成的官方镜像。
- `.agents/planner.md` 已要求输出 `tasks/todo+任务名.md`、验证命令、Definition of Done 和交接信息。
- `.agents/developer.md` 与 `.agents/implementer.md` 已要求按 todo 执行、更新 checklist、完成后验证。
- `.agents/code-reviewer.md` 已定义只读 review 角色，并允许拆分 security / test-quality / perf / maintainability 等多维审查。
- `apex-init-project-agent` 已把 `hooks.md` 列为目标 rules 文件，也已在 Codex 内联硬规则里写入文件大小、验证和禁止绕过 hook/CI 等要求。
- 当前仓库还没有 `.codex/hooks.json`、`.codex/config.toml`、`.codex/hooks/`、`.claude/settings.json`、`.claude/hooks/` 或 `tasks/` runtime 状态结构。

## 总体架构

### 新增能力分层

1. `apex-init-project-hooks` skill
   - 负责把 hook 配置、hook 脚本和共享 loop 脚本安装到目标项目。
   - 默认 dry-run；传入 `--write` 才写入。
   - 用户明确要求覆盖 / 重新生成时，才使用 `--force` 覆盖已有生成标记文件；已有 hook JSON 配置默认合并 Apex 条目。

2. 共享 loop 脚本
   - 放在 skill 内部：`.codex/skills/apex-init-project-hooks/scripts/`
   - 安装到目标项目后建议路径：
     - `.codex/hooks/apex_loop.py`
     - `.claude/hooks/apex_loop.py`
   - 两边 hook 配置都调用同一套语义：安全检查、行数检查、todo 状态、review gate、镜像漂移检查。

3. Route registry
   - 用一份 route registry 作为 hook 事件、matcher、命令和内部处理器的唯一事实源。
   - Claude Code 和 Codex 的 JSON 配置都从这份 registry 生成或校验，避免模板、runtime、文档三处漂移。
   - route key 建议稳定为：`SessionStart.default`、`PreToolUse.safety`、`PostToolUse.edit`、`PostToolUse.bash`、`PostToolUse.always`、`UserPromptSubmit.default`、`Stop.default`。
   - route 的公开 contract 是事件名、route id、matcher；具体脚本或 Python handler 名称属于内部实现，后续可替换但不能随意改公开 contract。

4. 项目状态目录
   - `tasks/loops/<slug>/state.json`
   - `tasks/loops/<slug>/run.md`
   - `tasks/reviews/<slug>.md`
   - `tasks/lessons.md`

### 平台配置

Claude Code:

- `.claude/settings.json`
- `.claude/hooks/*.py`

Codex:

- `.codex/hooks.json` 或 `.codex/config.toml`
- `.codex/hooks/*.py`

第一版建议优先生成 JSON 配置：

- Claude Code 本来使用 JSON settings。
- Codex 支持 `hooks.json` 和 `config.toml` inline hooks；为避免和用户本地 `.codex/config.toml` 冲突，优先生成 `.codex/hooks.json`。

## Hook 设计矩阵

| Hook | Claude Code 事件 | Codex 事件 | 第一版动作 | 阻塞策略 |
| --- | --- | --- | --- | --- |
| 会话上下文加载 | `SessionStart` | `SessionStart` | 汇总未完成 todo、最近 review、lessons 提示 | 不阻塞 |
| Prompt 路由提示 | `UserPromptSubmit` | `UserPromptSubmit` | 根据用户输入给出 plan / review / execute 路由建议 | 只建议，不硬拦 |
| 安全门禁 | `PreToolUse` | `PreToolUse` | 检查危险 Bash、secrets、`.env`、破坏性 git | 高风险阻塞 |
| 写入后快速检查 | `PostToolUse` | `PostToolUse` | 对 Edit/Write/apply_patch 后的文件做行数、secret、镜像漂移检查 | 超硬阈值阻塞或反馈 |
| 任务完成门禁 | `Stop` / `TaskCompleted` | `Stop` | 检查 todo + diff + review + 验证结果 | 未 review / 未验证时阻塞 |
| 配置变化提醒 | `ConfigChange` | 暂不覆盖 | `.claude/settings.json` 变化后提示复核 hook | 不阻塞 |

## 具体 Hook 规则

### 0. Route 与权限边界

Route registry:

- route registry 是 host adapter 配置和 runtime dispatch 的唯一事实源。
- 所有 hook 配置模板必须能从 registry 生成，或至少由测试校验与 registry 保持一致。
- 新增、删除或重排 route 都必须有迁移说明，因为 Codex / Claude Code 可能要求用户重新 trust hook。

Prompt / Edit / Stop 权限边界：

- `UserPromptSubmit` 只能做 advisory route hint，例如提示应先写 plan、调用 reviewer 或补充验证。
- 不在 Prompt 层根据自然语言猜测直接阻塞实现；自然语言意图识别只作为提示。
- 硬阻塞优先放在确定性边界：
  - `PreToolUse`：基于命令、路径、secrets、active task / plan 状态阻塞高风险操作。
  - `PostToolUse`：基于真实写入文件、行数、镜像漂移、疑似密钥给出 warning / block。
  - `Stop`：基于 diff、todo、review、验证证据决定是否允许完成。

统一失败输出：

- 每个阻塞或强 warning 都必须输出结构化字段：
  - `guard`：触发的门禁名，例如 `LineLengthGuard`、`MirrorDriftGuard`、`ReviewGate`。
  - `reason`：为什么触发。
  - `fix`：下一步可执行修复方式。
  - `failure_class`：`security_risk`、`state_violation`、`contract_failure`、`quality_gate`、`missing_artifact` 等分类。
  - `run_id`：本轮 hook / agent 执行标识；无法从 host 输入读取时由 runtime 生成。
- 失败记录写入 `tasks/loops/<slug>/failures.jsonl` 或全局 `tasks/loops/failures.jsonl`。
- Stop hook 返回平台可识别的 block JSON 时，只输出必要 JSON；详细说明写入 failure log 和 review 文件。

### 1. PreToolUse: 安全门禁

触发范围：

- Bash / shell 命令
- 文件读写工具
- MCP 写入类工具

检查项：

- 阻止 `rm -rf` 指向项目根、用户目录、磁盘根等高危路径。
- 阻止 `git reset --hard`、`git checkout --`、force push，除非用户明确授权。
- 阻止读取或输出 `.env`、token、SSH key、credential 文件。
- 阻止 `curl | bash`、`Invoke-WebRequest ... | iex`、`eval` 等高风险执行链。
- 对生产、付费、外部服务命令只做提醒或要求确认，不自动放行。

输出策略：

- 高风险：返回阻塞，并给出可执行替代建议。
- 中风险：返回 additional context，要求 agent 先说明风险再继续。

### 2. PostToolUse: 行数与快速质量门

触发范围：

- Claude Code: `Edit|Write|MultiEdit`
- Codex: `apply_patch|Edit|Write`，具体 matcher 以 Codex 实际工具名适配。

行数策略：

- 统计有效代码行：排除空行和纯注释。
- 普通源码：
  - 150-300 行：目标区间。
  - >300 行：提示需要拆分评估。
  - >400 行：高风险，要求说明拆分计划。
  - >500 行：默认阻塞，除非属于 generated / vendor / fixture / lock / migration / framework glue 例外。
- 前端组件：
  - 200-250 行：目标区间。
  - >300 行：要求拆出子组件、hooks、utils、constants、types 或样式。
  - >500 行：默认阻塞。
- 函数 / 方法 / hook / 组件主体：
  - 25-40 行：目标区间。
  - >50 行：提示拆 helper / strategy / 子组件。
- class / service / repository / controller / module：
  - 100-200 行：目标区间。
  - >300 行：要求拆分。

宽限策略：

- 第一版允许比规则线多约 100 行再硬阻塞。
- 也就是：
  - 普通源码 >400 行从强 warning 开始。
  - 普通源码 >500 行硬阻塞。
  - 前端组件 >400 行强 warning，>500 行硬阻塞。
- 这样符合用户提出的“可以比规定多 100 行左右，再多触发拆分”。

额外快速检查：

- 检测 `.agents/*.md` 是否被改动但 `.codex/agents` / `.claude/agents` 镜像未更新。
- 检测 `.codex/skills/apex-*` 代码脚本被改动后是否还没运行 `python -m py_compile`。
- 检测新写入文件是否疑似包含密钥。

### 3. Stop: Review / Repair Loop

触发条件：

- 当前 turn 存在代码 diff。
- 存在匹配的 `tasks/todo+*.md` 或 `tasks/loops/<slug>/state.json`。
- 当前任务未记录通过 review，或 review 结果包含未解决问题。

不要在以下情况触发完整 review：

- 仅创建或更新 todo 文件，没有代码 diff。
- 仅文档讨论或调研，没有实现变更。
- 用户明确要求“只写计划，不执行实现”。

第一版行为：

1. hook 读取 git diff 摘要。
2. hook 找到最近修改的 `tasks/todo+*.md` 或 loop state。
3. 如果未 review，写入 `tasks/reviews/<slug>.md` 初始 review 请求。
4. hook 阻塞 Stop，并把明确反馈交给 agent：
   - 需要调用 `code-reviewer` 审查本轮 diff。
   - 高风险时拆成 security / test-quality / maintainability / perf 维度。
   - review 问题修复后再次尝试完成。

第二版行为：

- Claude Code 下尝试用 agent hook 或 task/team 能力自动触发 reviewer。
- Codex 下优先通过 Stop feedback 让主 agent 调用 custom agents，而不是 hook 脚本递归启动 Codex。

防无限循环：

- `state.json` 记录 `review_attempts`。
- 同一 review gate 连续阻塞 3 次后，改为要求用户介入或降级为人工 review。
- 如果只有低置信 suggestion，不阻塞完成，只写入 review note。

### 4. SessionStart: 状态与记忆注入

加载内容：

- 未完成的 `tasks/todo+*.md`。
- 最近一次 `tasks/reviews/*.md` 的未解决问题。
- `tasks/lessons.md` 中与当前路径相关的条目。
- 当前 git branch、dirty 状态摘要。

输出策略：

- 只注入简短摘要。
- 不读取 secrets。
- 不把长 diff 或长日志塞进上下文。

## 新增文件范围

### 新增 skill

- `.codex/skills/apex-init-project-hooks/SKILL.md`
- `.codex/skills/apex-init-project-hooks/agents/openai.yaml`
- `.codex/skills/apex-init-project-hooks/scripts/init_project_hooks.py`
- `.codex/skills/apex-init-project-hooks/scripts/apex_loop.py`
- `.codex/skills/apex-init-project-hooks/templates/claude-settings.json`
- `.codex/skills/apex-init-project-hooks/templates/codex-hooks.json`

### 目标项目生成物

- `.claude/settings.json`
- `.claude/hooks/apex_loop.py`
- `.codex/hooks.json`
- `.codex/hooks/apex_loop.py`
- `tasks/loops/.gitkeep`
- `tasks/reviews/.gitkeep`
- `tasks/lessons.md`（不存在时创建）

### README 更新

- 在当前 `README.md` 的 skill 列表中加入 `apex-init-project-hooks`。
- 在安装到单个项目和全局 skills 的 `$SkillNames` 中加入 `apex-init-project-hooks`。
- 新增“启用 loop hooks”使用说明。
- 明确 Codex 需要 trust `.codex/` layer，并需要在 `/hooks` 中 review/trust 非 managed hooks。
- 明确 Claude Code 的 `.claude/settings.json` 可以提交，`.claude/settings.local.json` 不提交。

## 分阶段实施计划

### Phase 1: Hook skill 骨架

- [x] 新增 `apex-init-project-hooks` skill 目录。
- [x] 写 `SKILL.md`，说明默认 dry-run、`--write` 写入、`--force` 覆盖生成物。
- [x] 写 `init_project_hooks.py`：
  - [x] 解析 root、target、write、force、json 参数。
  - [x] 检查路径必须留在 project root 内。
  - [x] 生成计划清单，不直接覆盖无生成标记文件；host JSON 配置会保留用户 hook 并合并 Apex 条目。
  - [x] 支持 JSON 输出。
- [x] 写基础模板：
  - [x] `.claude/settings.json`
  - [x] `.codex/hooks.json`
- [x] 更新 README 安装链。

验证：

- [x] `python -m py_compile .codex\skills\apex-init-project-hooks\scripts\init_project_hooks.py`
- [x] dry-run 对当前仓库输出合理路径。
- [x] `--json` 输出可解析。

### Phase 2: 共享 hook runtime

- [x] 新增 `apex_loop.py`。
- [x] 新增 route registry：
  - [x] 定义事件名、route id、matcher、handler、阻塞策略。
  - [x] Claude Code / Codex 配置模板引用同一份 registry。
  - [x] route 顺序稳定，变更时必须更新迁移说明和测试。
- [x] 支持命令：
  - [x] `session-start`
  - [x] `user-prompt-submit`
  - [x] `pre-tool-use`
  - [x] `post-tool-use`
  - [x] `stop`
  - [x] `task-completed`
  - [x] `check-line-length`
  - [x] `check-agent-mirrors`
- [x] 解析 Claude Code hook JSON 输入。
- [x] 解析 Codex hook JSON 输入。
- [x] 输出平台可接受的 JSON / stderr / exit code。
- [x] 实现统一失败输出：
  - [x] `guard`
  - [x] `reason`
  - [x] `fix`
  - [x] `failure_class`
  - [x] `run_id`
- [x] 实现 failure JSONL 写入，至少覆盖 `tasks/loops/failures.jsonl`。
- [x] Prompt 层只返回 advisory route hint；不能在 `UserPromptSubmit` 里做实现阻塞。
- [x] Windows 优先支持 PowerShell / Python 调用路径。

验证：

- [x] 用 fixture JSON 覆盖 Claude `PostToolUse`。
- [x] 用 fixture JSON 覆盖 Codex `PostToolUse`。
- [x] 用 fixture JSON 覆盖 Claude / Codex `UserPromptSubmit`，确认只 advisory 不阻塞。
- [x] 用 fixture JSON 覆盖 Claude / Codex `Stop`，确认 block JSON 可被解析。
- [x] route registry 与 `.claude/settings.json`、`.codex/hooks.json` 模板保持一致。
- [x] 每个阻塞 fixture 都断言 `guard`、`reason`、`fix`、`failure_class`、`run_id`。
- [x] 无输入或未知事件时安全退出并给出诊断。

### Phase 3: 行数门禁

- [x] 实现有效代码行统计。
- [x] 支持扩展名分类：
  - [x] frontend component: `.tsx` `.jsx` `.vue` `.svelte`
  - [x] backend/source: `.py` `.go` `.rs` `.java` `.cs` `.ts` `.js`
  - [x] generated/vendor/fixture/lock/migration 例外。
- [x] 实现 warning / hard block 两档阈值。
- [x] 只检查本轮改动文件，不扫全仓库。
- [x] 输出精确文件、当前有效行数、阈值、建议拆分方向。

验证：

- [x] fixture: 299 行普通源码不阻塞。
- [x] fixture: 401 行普通源码 warning。
- [x] fixture: 501 行普通源码阻塞。
- [x] fixture: generated 文件超过阈值不阻塞但记录例外。

### Phase 4: Mirror drift 门禁

- [x] 检测 `.agents/*.md` 是否被修改。
- [x] 检测对应 `.codex/agents/*.toml` 和 `.claude/agents/*.md` 是否同步。
- [x] 如果未同步，在 `PostToolUse` 或 `Stop` 给出明确命令：
  - `python .codex\skills\apex-sync-agent-mirrors\scripts\sync_agent_mirrors.py . --target all --write`
- [x] 默认 warning；当用户正在提交或 Stop 时可阻塞。

验证：

- [x] 修改 `.agents/developer.md` 后能提示镜像过期。
- [x] 运行 sync 后提示消失。

### Phase 5: Review loop 门禁

- [x] 实现 `tasks/loops/<slug>/state.json` schema。
- [x] 从最近修改的 `tasks/todo+*.md` 推断 slug。
- [x] 判断本轮是否存在代码 diff。
- [x] 如果有 diff 且未 review，写入 `tasks/reviews/<slug>.md`。
- [x] Stop 返回阻塞反馈，要求调用 reviewer。
- [x] review 文件中存在 Critical / Warning 未处理时继续阻塞。
- [x] 连续阻塞 3 次后降级为人工介入提示。

验证：

- [x] 仅创建 todo，不触发 review。
- [x] 有 todo + 有代码 diff，Stop 阻塞并生成 review request。
- [x] review 为空或 Ready，Stop 放行。
- [x] review 有 Critical，Stop 阻塞。

### Phase 6: 安全门禁

- [x] 实现危险 Bash 正则。
- [x] 实现 secrets 路径保护。
- [x] 实现疑似 token 内容扫描。
- [x] 区分 block / ask / warn。

验证：

- [x] `rm -rf /` 阻塞。
- [x] `git reset --hard` 阻塞。
- [x] 读取 `.env` 阻塞。
- [x] 普通 `npm test` 放行。

### Phase 7: 文档与生成规则整合

- [x] 更新 `apex-init-project-agent` 中 `hooks.md` 生成要求，让目标项目 rules 能描述已安装 hook。
- [x] 更新 README 的安装到单项目和全局安装列表。
- [x] 增加手动启用说明：
  - Claude Code: 检查 `.claude/settings.json`。
  - Codex: trust 项目 `.codex/`，进入 `/hooks` review/trust hooks。
- [x] 说明 hook 与传统 Git pre-commit / CI 的关系。

验证：

- [x] README 中所有 `$SkillNames` 都包含新 skill。
- [x] `rg "apex-init-project-hooks" README.md .codex/skills` 能看到完整入口。

## 状态文件草案

```json
{
  "version": 1,
  "slug": "example-task",
  "goal": "简短目标",
  "todo_path": "tasks/todo+example-task.md",
  "phase": "implementing",
  "attempt": 1,
  "changed_files": [],
  "validation": {
    "commands": [],
    "last_result": "unknown",
    "last_run_at": null
  },
  "review": {
    "required": true,
    "status": "pending",
    "attempts": 0,
    "review_path": "tasks/reviews/example-task.md"
  },
  "gates": {
    "line_length": "pass",
    "security": "pass",
    "mirror_sync": "pass"
  },
  "last_failure": {
    "guard": null,
    "reason": null,
    "fix": null,
    "failure_class": null,
    "run_id": null
  }
}
```

## 风险点与防范

- 风险：hook 太吵，影响正常协作。
  - 防范：第一版只对硬风险阻塞，其他用 warning / additional context。
- 风险：Stop review loop 无限阻塞。
  - 防范：记录 attempts，连续 3 次同类阻塞后要求人工介入。
- 风险：Codex / Claude Code hook JSON schema 差异导致行为不一致。
  - 防范：共享 runtime 内部做平台适配，配置层保持最小。
- 风险：hook 脚本递归启动 agent，造成复杂进程树。
  - 防范：第一版不递归启动 agent，只生成 review request 并阻塞 Stop。
- 风险：项目级 hook 被用户或工具未 trust。
  - 防范：README 和安装输出明确提示 trust / `/hooks` review 步骤。
- 风险：已有用户 `.claude/settings.json` 或 `.codex/hooks.json` 被覆盖。
  - 防范：默认只替换 Apex 管理的 `apex_loop.py` 条目并保留用户 hook；需要 `--force` 才完整覆盖。

## Definition of Done

- [x] ApexPowers 新增 `apex-init-project-hooks` skill。
- [x] 可 dry-run / write 安装 Claude Code 与 Codex 项目级 hooks。
- [x] 安装过程不会覆盖无生成标记的用户脚本，已有 host JSON 配置会安全合并。
- [x] route registry 是 hook 事件、matcher、handler 和模板生成 / 校验的唯一事实源。
- [x] `UserPromptSubmit` 只做 advisory route hint，硬阻塞只发生在 `PreToolUse`、`PostToolUse` 或 `Stop` 的确定性边界。
- [x] 所有 block / strong warning 都包含 `guard`、`reason`、`fix`、`failure_class`、`run_id`，并写入 failure JSONL。
- [x] 行数门禁、mirror drift、review loop、安全门禁均有脚本级测试或 fixture 验证。
- [x] hook contract tests 覆盖 Claude / Codex 的 `UserPromptSubmit`、`PostToolUse`、`Stop` fixture。
- [x] README 包含安装、启用、trust、验证和隐私说明。
- [x] 修改 Python 脚本后通过 `python -m py_compile`。
- [x] 当前仓库 dirty worktree 中已有无关改动不被回滚、不被重排。

## 交接给 Implementer/Developer 的关键信息

优先实现 Phase 1 到 Phase 3。不要一开始就做自动多 agent review 的复杂版；先把项目级 hook 安装链、共享 runtime、行数门禁做稳。Review loop 第一版采用 Stop 阻塞 + 生成 review request 的方式，让主 agent 调用现有 `code-reviewer`，避免 hook 脚本递归启动 agent。
