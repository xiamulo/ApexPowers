# Trellis 源码对照：ApexPowers 可借鉴模块

## 调研范围

- Trellis 源码：`D:\gitdown\Trellis`
- Trellis 仓库：`https://github.com/mindfold-ai/Trellis.git`
- Trellis HEAD：`caa4e310 chore(readme): update WeChat group QR to group 8 (#331)`
- ApexPowers 当前重点：`apex-init-project-hooks`、`.agents` 源模板、agent 镜像生成、`tasks/loops` / `tasks/reviews` 状态。

## 结论

是的，ApexPowers 当前逻辑已经和 Trellis 有明显相似性：两者都在用 hook 把“模型应该遵守的规则”落成可执行 guardrail，而不是只依赖 Markdown 提示词。

但两者重心不同：

| 维度 | ApexPowers 当前形态 | Trellis 当前形态 |
| --- | --- | --- |
| 核心定位 | 私有 skill / agent / hook 包 | AI coding workflow harness |
| hook 角色 | 即时门禁：安全、行数、mirror drift、review gate | 上下文注入 + workflow breadcrumb + sub-agent context |
| 任务模型 | `tasks/todo+*.md` + `tasks/loops/<slug>/state.json` | `.trellis/tasks/<task>/task.json` + `prd.md` + `implement.jsonl` + `check.jsonl` |
| 规则模型 | `AGENTS.md` / `CLAUDE.md` / `.claude/rules` / `.agents` | `.trellis/spec/` 分层 spec + per-task context manifest |
| 记忆模型 | `tasks/lessons.md` 摘要 | `.trellis/workspace/<developer>/journal-N.md` + index |
| 更新/卸载 | 生成标记 + JSON 合并 + legacy cleanup | `.template-hashes.json` manifest + update conflict flow + uninstall scrubbers |

所以，ApexPowers 已经像 Trellis 的“hook guardrail 子集”，但还没有 Trellis 的“项目生命周期 / 上下文持久化 / 安全更新”层。

## 最值得加入的模块

### 1. Template manifest + update / uninstall 机制

优先级：P0。

Trellis 关键源码：

- `packages/cli/src/utils/template-hash.ts`
- `packages/cli/src/commands/update.ts`
- `packages/cli/src/commands/uninstall.ts`
- `packages/cli/src/utils/uninstall-scrubbers.ts`

Trellis 做法：

- init 后写 `.trellis/.template-hashes.json`。
- hash key 使用 POSIX 路径，内容 hash 前统一 LF，避免 Windows / Linux 行尾差异。
- update 时区分：
  - 模板未变：跳过。
  - 用户没改但模板升级：自动更新。
  - 用户改过：提示冲突或要求显式 force。
  - `tasks/`、`workspace/`、`spec/` 等用户数据：永不自动覆盖。
- uninstall 时以 manifest 为唯一删除边界；对 `settings.json` / `hooks.json` / `config.toml` 这类结构化文件只 scrub Trellis 管理字段，保留用户字段。

ApexPowers 当前缺口：

- `init_project_hooks.py` 能合并 host JSON，也能用生成标记保护 runtime 文件，但没有全局 manifest。
- 已安装过哪些文件、哪些是 Apex 管理、哪些是用户新增，目前只能靠路径和标记推断。
- 后续一旦支持更多平台或更多生成物，仅靠生成标记会越来越脆。

建议 ApexPowers 加：

- `apex-init-project-hooks` 写入一个 manifest，例如：
  - agent-root 安装：`<codex-home>/apex/manifest.json`、`<claude-home>/apex/manifest.json`
  - project-scope 状态：`tasks/loops/.apex-manifest.json`
- manifest 记录：
  - `version`
  - `installer`
  - `scope`
  - `files[path] = { sha256, kind, owner, structured }`
  - `protected_paths`
- 新增 `--update` / `--uninstall` 或独立 `apex-update-project-hooks` 命令。
- 对 `hooks.json` / `settings.json` 用 structured scrubber，只移除 Apex 管理命令，不动用户 hook。

这是最有工程收益的一项：它不改变现有协作体验，却显著降低升级和卸载风险。

### 2. Workflow-state 文档作为 hook 的单一事实源

优先级：P0。

Trellis 关键源码：

- `packages/cli/src/templates/trellis/workflow.md`
- `packages/cli/src/templates/shared-hooks/inject-workflow-state.py`
- `packages/cli/src/templates/opencode/plugins/inject-workflow-state.js`
- `packages/cli/test/templates/trellis.test.ts`

Trellis 做法：

- `workflow.md` 内嵌 `[workflow-state:STATUS]...[/workflow-state:STATUS]`。
- hook 只解析这些块，不在脚本里硬编码完整流程文案。
- 测试约束 workflow 必填步骤和 workflow-state breadcrumb 不漂移。

ApexPowers 当前缺口：

- `UserPromptSubmit` 当前只有 `prompt_hint()`，基于关键词输出 plan / review / done 提示。
- Stop / PostToolUse 已经有硬门禁，但“当前应该处于什么协作阶段”还没有一个可编辑的 workflow source。

建议 ApexPowers 加：

- 新增 `tasks/loops/workflow.md` 或 `.apex/workflow.md`，不要直接引入 `.trellis/` 命名。
- 定义：
  - `[apex-state:no_task]`
  - `[apex-state:planning]`
  - `[apex-state:implementing]`
  - `[apex-state:review_required]`
  - `[apex-state:validation_required]`
  - `[apex-state:done]`
- `UserPromptSubmit` 从 workflow 文档解析当前状态块，输出 `<apex-workflow-state>`。
- `ReviewGate` / `ValidationGate` 更新 `tasks/loops/<slug>/state.json.phase`。
- 增加测试：每个状态块存在，关键 gate 状态都有对应文案。

这能让 ApexPowers 的 hook 从“关键词提醒”升级为“状态驱动协作提示”，同时保持文案可由用户项目自定义。

### 3. Task 目录 + context manifest

优先级：P1。

Trellis 关键源码：

- `packages/cli/src/templates/trellis/scripts/common/task_store.py`
- `packages/cli/src/templates/trellis/scripts/common/task_context.py`
- `packages/cli/src/templates/shared-hooks/inject-subagent-context.py`
- `packages/cli/src/templates/codex/agents/trellis-implement.toml`
- `packages/cli/src/templates/codex/agents/trellis-check.toml`

Trellis 做法：

- 每个任务有独立目录。
- `prd.md` 保存需求。
- `implement.jsonl` 和 `check.jsonl` 保存 sub-agent 必读的 spec / research 文件。
- hook 或 agent prelude 根据 JSONL 注入上下文。

ApexPowers 当前缺口：

- `tasks/todo+*.md` 很适合轻量计划，但不是机器友好的任务数据库。
- `tasks/loops/<slug>/state.json` 已经开始机器化，但缺少 PRD、context manifest、research 的结构化入口。
- code-reviewer / implementer 的上下文仍主要靠主 agent 提示和 todo 文本。

建议 ApexPowers 增量加，不要大改：

```text
tasks/
  todo+example.md                  # 保留现有轻量计划入口
  loops/
    example/
      state.json
      prd.md                       # 从 todo 提炼出的需求/验收
      implement.jsonl              # 实现前必读 spec/research
      review.jsonl                 # review 前必读 spec/research
      research/
```

第一版只做三件事：

- `Stop` / manual command 能校验 JSONL 里引用的文件是否存在。
- `SessionStart` 摘要显示 active loop 的 `prd.md` / context manifest 状态。
- `code-reviewer` 和 `implementer` 模板要求先读对应 JSONL。

不要一开始强制所有小任务都建完整目录。可以规定：只有存在代码 diff、review gate 或用户明确创建 task 时才升级为 loop task directory。

### 4. Session-scoped active task

优先级：P1。

Trellis 关键源码：

- `packages/cli/src/templates/trellis/scripts/common/active_task.py`
- `packages/cli/test/regression.test.ts`

Trellis 做法：

- active task 指针不是全局文件，而是 `.trellis/.runtime/sessions/<context-key>.json`。
- context key 来自 hook input、`TRELLIS_CONTEXT_ID`、平台 session env 或 transcript path。
- 多个 AI 窗口可以各自有 active task，互不覆盖。

ApexPowers 当前缺口：

- 当前 `ReviewGate` 用 newest `tasks/todo+*.md` 推断 slug。
- 这对单窗口足够快，但多窗口、多任务并行时可能把 review gate 绑定到错误 todo。

建议 ApexPowers 加：

- `tasks/loops/.runtime/sessions/<context-key>.json`
- 结构：

```json
{
  "slug": "example",
  "todo_path": "tasks/todo+example.md",
  "loop_dir": "tasks/loops/example",
  "updated_at": "..."
}
```

- `SessionStart` / `UserPromptSubmit` 优先读取 session active loop。
- 找不到 session 指针时再 fallback 到 newest todo，并在提示里标注 `source: fallback-newest-todo`。
- 新增 manual command：
  - `apex_loop.py start-task <slug>`
  - `apex_loop.py current-task --source`
  - `apex_loop.py finish-task`

这能直接解决未来并行窗口误判任务的问题。

### 5. Spec / lessons 的分层沉淀

优先级：P1。

Trellis 关键源码：

- `packages/cli/src/templates/trellis/workflow.md`
- `packages/cli/src/templates/codex/skills/update-spec/SKILL.md`
- `packages/cli/src/utils/template-fetcher.ts`
- `packages/cli/src/utils/registry-config.ts`

Trellis 做法：

- `.trellis/spec/` 是项目约定的长期事实源。
- `trellis-update-spec` 在任务完成后把新经验回写 spec。
- 支持 registry / marketplace 拉取 spec 模板。

ApexPowers 当前缺口：

- `tasks/lessons.md` 已经有雏形，但它更像流水账，不适合按前端、后端、测试、安全、Git 等主题检索。
- `apex-init-project-agent` 会生成 rules，但 rules 不是任务执行时的精确 context manifest。

建议 ApexPowers 加：

```text
tasks/spec/
  index.md
  frontend.md
  backend.md
  testing.md
  git.md
  hooks.md
```

- `tasks/lessons.md` 继续作为原始经验入口。
- 新增 `apex-update-spec` skill：任务完成后把可复用经验从 lessons / review 中提升到 `tasks/spec/*.md`。
- `implement.jsonl` / `review.jsonl` 只引用 `tasks/spec` 和 `tasks/loops/<slug>/research`，不要引用待修改代码文件。

这会让 ApexPowers 从“一次性生成 rules”变成“项目规则会随使用变聪明”。

### 6. Finish / record-session 收尾命令

优先级：P2。

Trellis 关键源码：

- `packages/cli/src/templates/codex/skills/finish-work/SKILL.md`
- `packages/cli/src/templates/codex/skills/record-session/SKILL.md`
- `packages/cli/src/templates/trellis/scripts/add_session.py`

Trellis 做法：

- 完成任务时先确认代码已提交，再归档任务，再记录 journal。
- journal 有 max line rotation 和 index。
- 记录 commit hash、branch、summary、testing。

ApexPowers 当前缺口：

- Stop gate 能要求 review 和 validation，但没有标准化“收工记录”。
- `tasks/reviews/<slug>.md` 通过后，经验如何归档、如何复用，仍靠人工。

建议 ApexPowers 加：

- 新 skill：`apex-finish-loop`
- 行为：
  - 检查 `tasks/reviews/<slug>.md` 已 Ready + Validation Pass。
  - 检查 dirty files 是否属于当前任务。
  - 把 `tasks/loops/<slug>/state.json` 标成 done。
  - 追加 `tasks/loops/<slug>/run.md` 或 `tasks/journal/<developer>.md`。
  - 提醒是否需要 `apex-update-spec`。

第一版不要自动 commit；ApexPowers 当前是私有协作包，自动提交容易踩用户的 Git 边界。可以先只生成记录和提示。

### 7. 平台 capability matrix

优先级：P2。

Trellis 关键源码：

- `packages/cli/src/types/ai-tools.ts`
- `packages/cli/src/configurators/index.ts`
- `packages/cli/src/templates/shared-hooks/index.ts`
- `packages/cli/test/templates/shared-hooks.test.ts`
- `packages/cli/test/templates/hook-timeouts.test.ts`

Trellis 做法：

- 平台能力集中到 registry。
- 哪个平台支持 agent、hook、Python hook、shared skill 都显式声明。
- shared hook 分发由 capability table 驱动，并有测试防止 dead template / 错配平台。

ApexPowers 当前缺口：

- 目前主要覆盖 Codex 和 Claude Code。
- route registry 已经有事件和 matcher 单一事实源，但还没有平台能力矩阵。

建议 ApexPowers 加：

- `PlatformProfile` dataclass：
  - `id`
  - `config_path`
  - `runtime_path`
  - `supports_session_start`
  - `supports_user_prompt_submit`
  - `supports_stop`
  - `supports_subagent_context_push`
  - `hook_schema`
- `HostConfigRenderer` 从 profile + route registry 渲染。
- 测试：
  - 每个平台 declared route 都能渲染。
  - 每个 shared runtime command 至少被一个平台使用。
  - timeout 不低于 Windows 冷启动阈值。

这为后续支持 Cursor、Gemini、OpenCode 等留出入口，但不会逼当前版本立刻铺开。

### 8. Config.yaml 本地扩展点

优先级：P2。

Trellis 关键源码：

- `packages/cli/src/templates/trellis/config.yaml`
- `packages/cli/src/templates/trellis/scripts/common/trellis_config.py`

Trellis 做法：

- `.trellis/config.yaml` 管 session journal、task lifecycle hooks、monorepo packages、Codex dispatch mode。

ApexPowers 当前缺口：

- 规则散在 README、skill、hook runtime 常量里。
- 用户想调阈值、review gate、是否启用某类 guard，目前需要改脚本。

建议 ApexPowers 加：

```yaml
version: 1
line_length:
  warning: 400
  hard: 500
review_gate:
  enabled: true
  max_attempts: 3
mirror_drift:
  stop_blocks: true
lifecycle_hooks:
  after_review_ready: []
```

路径建议：`tasks/loops/config.yaml` 或 `.apex/config.yaml`。如果强调“不污染业务项目根”，可以继续放在 `tasks/loops/config.yaml`。

第一版只读取配置，不提供复杂 YAML parser；可以用 Python 标准库外的依赖为零的简单 parser，或 JSON 配置。

## 不建议照搬的部分

### 不建议直接复制 Trellis 源码

Trellis 是 AGPL-3.0-only。ApexPowers 是你的私有包，直接复制 Trellis 实现会带来许可证边界问题。建议只借鉴架构思想，重新实现小而必要的子集。

### 不建议把 ApexPowers 改成完整 Trellis

ApexPowers 的价值在于轻量、私有、可复制到不同项目，且贴近 Codex / Claude 的实际协作规则。完整 Trellis 的 `.trellis/tasks`、workspace journal、registry、marketplace、multi-platform configurator 都很强，但一次性搬入会让项目复杂度跳太快。

### 不建议第一版自动派生/递归启动 agent

ApexPowers 当前“Stop 阻塞 + 生成 review request + 让主 agent 调用 reviewer”的边界是对的。Trellis 源码里也花了大量逻辑处理 sub-agent self-exemption、class-1/class-2 context injection 和递归调度防护。ApexPowers 没必要现在进入这个复杂区。

### 不建议强制所有任务都走重流程

ApexPowers 用户画像里“提问就是提问，明确要求才干活”非常重要。Trellis 的 workflow-state 对实现任务更强约束，但 ApexPowers 应保留轻量 direct answer / simple task escape hatch。

## 建议路线

### Phase A: 安全升级基础

目标：让 ApexPowers 安装物可追踪、可更新、可卸载。

- [x] 设计 Apex manifest schema。
- [x] `init_project_hooks.py` 写入 manifest。
- [x] 对 host JSON 增加 structured scrubber。
- [x] 增加 `--uninstall --dry-run`。
- [x] 增加 manifest 单测：LF/CRLF hash 一致、用户 hook 保留、Apex hook 移除。

落地边界：

- 项目 manifest：`tasks/loops/.apex-manifest.json`。
- Host manifest：`<codex-home>/apex/manifest.json`、`<claude-home>/apex/manifest.json`。
- `--update` 复用 manifest-aware install；默认 dry run。
- `--uninstall` 只处理 manifest 记录的 Apex-managed 文件；host JSON scrub Apex 条目，runtime 文件必须 hash 匹配、带生成标记或 `--force` 才删除。

### Phase B: Workflow-state

目标：让 hook 输出来自可编辑 workflow 文档。

- [x] 新增 `tasks/loops/workflow.md` 模板。
- [x] `UserPromptSubmit` 解析 `[apex-state:*]`。
- [x] `state.json.phase` 驱动当前状态。
- [x] 测试状态块存在、缺失时显式降级。

落地边界：

- 状态块命名为 `[apex-state:STATUS]...[/apex-state:STATUS]`，避免引入 `.trellis/` 命名。
- 当前支持 `no_task`、`planning`、`implementing`、`review_required`、`validation_required`、`done`。
- `SessionStart` 注入状态摘要；`UserPromptSubmit` 输出完整 `<apex-workflow-state>` block。

### Phase C: Loop task directory

目标：把 todo、review、validation、context 串起来。

- [ ] 为 active todo 创建 `tasks/loops/<slug>/prd.md`。
- [ ] 创建 `implement.jsonl` / `review.jsonl` seed 行。
- [ ] 增加 `validate-context` 命令。
- [ ] 更新 implementer / code-reviewer agent 模板，要求读取 JSONL。

### Phase D: Session-scoped active loop

目标：支持多窗口并行任务。

- [ ] 实现 `tasks/loops/.runtime/sessions/<context-key>.json`。
- [ ] 增加 `start-task/current-task/finish-task` 命令。
- [ ] Hook 优先使用 session active loop，fallback 才用 newest todo。
- [ ] 测试不同 `CODEX_THREAD_ID` / `CLAUDE_SESSION_ID` 不互相覆盖。

### Phase E: Spec / lessons promotion

目标：把 review 和 lessons 变成可复用项目规则。

- [ ] 初始化 `tasks/spec/index.md`。
- [ ] 新增 `apex-update-spec` skill。
- [ ] `apex-finish-loop` 提醒或执行 lessons -> spec 提炼。
- [ ] `SessionStart` 摘要显示相关 spec 文件，而不是只读 `tasks/lessons.md`。

## 我会优先做什么

如果下一步要动手，我建议先做 Phase A，再做 Phase B。

原因：

1. Manifest / update / uninstall 是基础设施，越早加越少背历史包袱。
2. Workflow-state 能立刻改善 hook 的可维护性，并让 ApexPowers 更接近 Trellis 的核心优势。
3. Task directory / spec / journal 是更大的体验变更，适合在前两项稳定后再增量引入。

## 参考路径清单

Trellis：

- `D:\gitdown\Trellis\README.md`
- `D:\gitdown\Trellis\packages\cli\src\commands\init.ts`
- `D:\gitdown\Trellis\packages\cli\src\commands\update.ts`
- `D:\gitdown\Trellis\packages\cli\src\commands\uninstall.ts`
- `D:\gitdown\Trellis\packages\cli\src\utils\template-hash.ts`
- `D:\gitdown\Trellis\packages\cli\src\templates\trellis\workflow.md`
- `D:\gitdown\Trellis\packages\cli\src\templates\shared-hooks\index.ts`
- `D:\gitdown\Trellis\packages\cli\src\templates\shared-hooks\inject-workflow-state.py`
- `D:\gitdown\Trellis\packages\cli\src\templates\shared-hooks\inject-subagent-context.py`
- `D:\gitdown\Trellis\packages\cli\src\templates\trellis\scripts\common\active_task.py`
- `D:\gitdown\Trellis\packages\cli\src\templates\trellis\scripts\common\task_store.py`
- `D:\gitdown\Trellis\packages\cli\src\templates\trellis\scripts\common\task_context.py`
- `D:\gitdown\Trellis\packages\cli\src\templates\trellis\scripts\add_session.py`
- `D:\gitdown\Trellis\packages\cli\test\templates\shared-hooks.test.ts`
- `D:\gitdown\Trellis\packages\cli\test\templates\hook-timeouts.test.ts`
- `D:\gitdown\Trellis\packages\cli\test\templates\trellis.test.ts`

ApexPowers：

- `D:\gitdown\ApexPowers\.codex\skills\apex-init-project-hooks\scripts\init_project_hooks.py`
- `D:\gitdown\ApexPowers\.codex\skills\apex-init-project-hooks\scripts\apex_loop_routes.py`
- `D:\gitdown\ApexPowers\.codex\skills\apex-init-project-hooks\scripts\apex_loop_runtime.py`
- `D:\gitdown\ApexPowers\.codex\skills\apex-init-project-hooks\scripts\apex_loop_utils.py`
- `D:\gitdown\ApexPowers\tasks\todo+apex-loop-hooks.md`
- `D:\gitdown\ApexPowers\tasks\reviews\apex-loop-hooks.md`
- `D:\gitdown\ApexPowers\tests\test_apex_loop_hooks.py`
- `D:\gitdown\ApexPowers\tests\test_apex_loop_installer.py`
