# ApexPowers 对标 Trellis 的改进计划

日期：2026-06-28

范围：本文件评估 Claude 提出的 Trellis 借鉴建议，并基于当前 ApexPowers 源码、Trellis 源码、GrokSearch/社区最佳实践、OpenAI Codex Hooks 与 Claude Code Hooks 文档，给出分阶段改进路线。本文只做方案与计划，不复制 Trellis 源码，也不在本轮修改 hook runtime。

## 结论摘要

Claude 的方向基本正确：ApexPowers 不应该照搬 Trellis，但值得吸收 Trellis 的 5 类结构化能力：

1. 机器可读的 loop task package。
2. session-scoped active task。
3. context manifest 和 read-before-write gate。
4. spec / lessons promotion。
5. finish-loop / record-session 收工协议。

但 Claude 的计划有 4 个需要修正的地方：

1. Claude 把部分已经完成的基础设施当作未来 P0。ApexPowers 当前已经完成 manifest/update/uninstall、workflow-state、ReviewGate/ValidationGate、PreCompact snapshot 等关键基础，不应再把这些列为“大方向重做”。
2. `tasks/loops/<slug>/` 不能只加 `state.json`、`prd.md`、`implement.jsonl`、`review.jsonl`。还应该增加 canonical `task.json`，否则任务元数据会继续散落在 `state.json`、review frontmatter、`active.json` 和人工说明里。
3. “read-before-write gate”第一版不能宣称证明 agent 已读。第一版只能可靠做到 manifest 语法/路径校验、上下文注入、证据声明和 Stop 阶段校验；真正的读取证据需要 read log 或 subagent evidence。
4. `SubagentStart` / `SubagentStop` 现在应该列入 P1，但必须做 host capability matrix。Claude Code 与 Codex 文档都列出相关事件，不过不同客户端和版本的输入字段、决策边界可能不同，ApexPowers 不能假装完全一致。

更新后的优先级：

| 优先级 | 工作 | 结论 |
| --- | --- | --- |
| P0 | 固化当前 hook guardrail 基线，补 doctor 检查设计 | 已有基础不要重构，先把事实源写清楚 |
| P1 | `tasks/loops/<slug>/task.json` + `prd.md` + `implement.jsonl` + `review.jsonl` | 最高收益，补机器可读任务包 |
| P1 | `tasks/loops/.runtime/sessions/<context-key>.json` | 解决多窗口 active task 误判 |
| P1 | context manifest validation + 轻量 read-before-write gate | 先校验文件存在与 repo 内路径，再做读取证据 |
| P1 | `SubagentStart` / `SubagentStop` evidence | 给子 agent 注入契约并回收证据 |
| P2 | `tasks/spec/` + `apex-update-spec` | 把流水账 lessons 提升为长期项目知识 |
| P2 | `apex-finish-loop` + `run.md` | 补收工协议，第一版不自动 commit |
| P2 | `tasks/loops/config.json` | 外部化阈值，避免改 runtime 常量 |
| P3 | Trellis channel/worker/event-log/marketplace | 暂缓，复杂度不符合 ApexPowers 轻量定位 |

## 证据来源

### ApexPowers 源码核对

本轮重点核对：

- `.codex/skills/apex-init-project-hooks/scripts/apex_loop_routes.py`
- `.codex/skills/apex-init-project-hooks/scripts/apex_loop_runtime.py`
- `.codex/skills/apex-init-project-hooks/scripts/apex_loop_utils.py`
- `.codex/skills/apex-init-project-hooks/scripts/init_project_hooks.py`
- `tests/test_apex_loop_hooks.py`
- `tests/apex_hooks/test_pre_tool_use_security.py`
- `tests/apex_hooks/test_stop_loop_safety.py`
- `docs/apexpowers-inventory.md`
- `docs/apexpowers-skills-agents-hooks.md`
- `docs/subagent-hooks-contract-evidence.md`
- `tasks/research+trellis-apexpowers-opportunities.md`

代码图索引确认当前 ApexPowers 项目存在，但隐藏目录中的 hook runtime 结构化索引覆盖不完整，所以对 runtime 证据补充了精确文件读取和文本搜索。

当前 ApexPowers 已有能力：

- route registry 已稳定渲染 `SessionStart`、`UserPromptSubmit`、`PreToolUse`、`PostToolUse`、`PostToolBatch`、`PreCompact`、`Stop`。
- `PreToolUse` 已拆为 `safety-write`、`safety-read`、`safety-shell`。
- Claude matcher 已覆盖 `Read|Grep|Glob|mcp__.*` 一类读工具场景。
- `SecretContentGuard` 已前移到写前，覆盖 `Write.content`、`Edit.new_string`、`MultiEdit.edits[*].new_string`、Codex `apply_patch` added lines 和明显 shell 写入命令。
- `ReviewGate` 会解析结构化 frontmatter，校验 `reviewed_diff_hash`、`reviewed_file_hashes`、`validation_evidence.required_checks`、reviewer role 以及 reviewer/implementer 独立性。
- `ValidationGate` 会阻塞 ready review 但 validation missing 的情况。
- `Stop` 已处理 `stop_hook_active`，记录 block reason hash、continuation 计数和 review request 状态。
- `PostToolBatch`、guard cache、failure dedupe 已存在，PostToolUse 重复扫描已经有基础治理。
- `PreCompact` 已写 `tasks/loops/session-snapshot.json`，保存 workflow、active task、diff hash、review path、blockers。
- `LineLengthGuard` 已按文件类型分阈值，并区分 Post warning 与 Stop block。
- `tasks/loops/active.json` 已能用 `owned_paths` 在多 todo 场景下选择 review slug。

当前仍缺的 Trellis 类能力：

- 没有 canonical `tasks/loops/<slug>/task.json`。
- `tasks/loops/<slug>/prd.md` 不是任务包标准产物。
- 没有 `implement.jsonl` / `review.jsonl` 的上下文 manifest 校验。
- `tasks/loops/active.json` 仍是全局索引，不是 session-scoped。
- route registry 还没有 `SubagentStart` / `SubagentStop`。
- 没有子 agent evidence manifest。
- `tasks/lessons.md` 没有提升到分层 `tasks/spec/`。
- 没有 `apex-finish-loop` / `run.md` 收工协议。
- line length、review gate、mirror drift 等阈值仍主要在脚本常量中。

### Trellis 源码核对

Trellis 本地读取位置：

- `C:\Users\gin_n\AppData\Local\Temp\apex-trellis-research\Trellis`
- HEAD：`01ec8d6503b2338194e9bd2e9dbbcf22054c1bba`
- 提交时间：`2026-06-25T12:17:26+08:00`
- 版本：`@mindfoldhq/trellis 0.6.5`
- 许可证：`AGPL-3.0-only`

重点核对的 Trellis 文件：

- `README.md`
- `LICENSE`
- `packages/cli/package.json`
- `packages/core/src/task/schema.ts`
- `packages/core/src/task/records.ts`
- `packages/cli/src/templates/trellis/workflow.md`
- `packages/cli/src/templates/trellis/config.yaml`
- `packages/cli/src/templates/trellis/scripts/common/active_task.py`
- `packages/cli/src/templates/trellis/scripts/common/task_context.py`
- `packages/cli/src/templates/trellis/scripts/common/task_store.py`
- `packages/cli/src/templates/shared-hooks/inject-workflow-state.py`
- `packages/cli/src/templates/shared-hooks/inject-subagent-context.py`
- `packages/cli/src/templates/cursor/agents/trellis-implement.md`
- `packages/cli/src/templates/cursor/agents/trellis-check.md`

Trellis 值得借鉴的事实：

- Trellis 以 specs、tasks、memory 作为 repo 内持久化状态，而不是把上下文只放在对话里。
- `.trellis/tasks/<task>/` 使用 `task.json` 作为 canonical 任务记录，并配套 `prd.md`、可选 `design.md`、可选 `implement.md`、`implement.jsonl`、`check.jsonl`、`research/`。
- `task.json` 写入逻辑保留未知字段，避免升级时破坏用户或旧版本数据。
- `implement.jsonl` / `check.jsonl` 是 subagent context manifest，不是任意流水账。
- JSONL 校验会检查引用文件或目录是否存在。
- active task 指针是 session-scoped，存放于 `.trellis/.runtime/sessions/<context-key>.json`，而不是单一全局文件。
- workflow breadcrumb 从 workflow 文档解析，减少把完整流程文案硬编码到脚本中。
- finish / record-session 是单独收尾协议，并且 Trellis 明确把 dirty tree 分类、归档、journal 记录和 commit 边界拆开。

不应借鉴的部分：

- 不复制 Trellis 源码或模板正文。AGPL-3.0-only 对衍生实现有明确边界，ApexPowers 应只借鉴架构思想并重新实现小子集。
- 不迁移到完整 `.trellis/` 体系。ApexPowers 的优势是私有、轻量、Codex/Claude 贴合、中文任务契约、review/validation gate 清晰。
- 不急着实现 Trellis 的 channel/worker/marketplace/多平台全量 configurator。
- 不引入第一版自动 commit。ApexPowers 当前有强并行任务安全规则，自动 commit 容易污染其他窗口或其他 CLI 的工作。

### GrokSearch 与社区实践

本轮使用 `mcp__grok_search_rs` 做了社区实践检索：

- `doctor` 显示 Grok provider 可用；Tavily 与 Firecrawl 返回 401，因此 supplemental source fetch 不可靠。
- 查询 “top practices AI coding agents context engineering durable state human in the loop task manifests hooks community 12 factor agents” 成功返回综合结论和来源列表。
- 查询 Claude Code hooks / SubagentStart / SubagentStop 时 Grok provider 返回错误，fallback source 为 0。
- 因此，GrokSearch 结果只作为趋势扫描；关键结论用源码、官方文档或可打开网页交叉验证。

社区实践与 ApexPowers 的对应关系：

| 社区实践 | 代表来源 | 对 ApexPowers 的启发 |
| --- | --- | --- |
| own your context window | Anthropic context engineering、LangChain context engineering、12-Factor Agents | 用 `implement.jsonl` / `review.jsonl` 精确选择上下文，不把 repo 全塞给 agent |
| durable state | 12-Factor Agents、durable execution 讨论 | 用 `task.json`、`state.json`、session pointer、run.md 持久化，而不是依赖对话记忆 |
| human-in-the-loop | 12-Factor Agents、agent governance 讨论 | review gate、validation gate、finish-loop 都应保留人工或独立 reviewer 边界 |
| small focused agents | 12-Factor Agents、多 agent 架构实践 | implementer、code-reviewer、researcher 的上下文和证据分开 |
| hooks as guardrails | Codex Hooks、Claude Code Hooks、社区 hook 示例 | hook 做确定性校验、注入和证据收集，不把 hook 写成重型 agent 编排器 |
| context isolation | Anthropic/LangChain context engineering | subagent 只拿任务相关 spec/research，不继承整个主线程上下文 |
| resumability | durable execution / checkpointing 思路 | session-scoped active task 和 PreCompact snapshot 应变成同一套 runtime 状态 |

可验证参考链接见文末。

## 对 Claude 建议逐条判断

### 1. `tasks/loops/<slug>/` 任务目录升级

Claude 建议：

```text
tasks/loops/<slug>/
  state.json
  prd.md
  implement.jsonl
  review.jsonl
  research/
  run.md
```

判断：方向正确，但结构不完整。

建议目标结构：

```text
tasks/loops/<slug>/
  task.json                 # canonical task metadata，CLI/doctor/hook 共同读取
  state.json                # hook runtime 状态，phase/blockers/continuations
  prd.md                    # 需求、范围、验收
  design.md                 # 可选，复杂任务技术设计
  implement.md              # 可选，执行计划、验证命令、rollback 点
  implement.jsonl           # implementer 必读 spec/research/design manifest
  review.jsonl              # reviewer / ReviewGate 必读 spec/research/design manifest
  reads.jsonl               # P2 可选，工具读取证据
  research/
  subagents/
    manifest.json
    <agent-id>.json
  failures.jsonl
  run.md                    # 收工记录
```

为什么必须加 `task.json`：

- `state.json` 是 hook runtime 高频状态，适合记录 phase、blocker、continuation、diff hash。
- `task.json` 是稳定任务元数据，适合记录 title、status、priority、branch、worktree、owner、parent/children、owned_paths、review_path。
- 如果不加 `task.json`，未来 doctor、finish-loop、session pointer、subagent evidence 都会继续从多个文件拼装任务元数据，错误率会上升。
- Trellis 的 `task.json` 最值得借鉴的不是字段本身，而是“任务元数据有唯一机器事实源”。

不建议：

- 不要把所有 runtime 状态塞进 `task.json`。
- 不要把 review 结论塞进 `task.json`。
- 不要把 `tasks/todo+*.md` 删除；它仍然是轻量中文任务契约和人类入口。

### 2. Session-scoped active task

Claude 建议：

```text
tasks/loops/.runtime/sessions/<context-key>.json
```

判断：完全正确，应进入 P1。

当前 ApexPowers 的 `tasks/loops/active.json` 已解决一部分并行任务问题，但它仍是项目全局状态。多个 Codex 窗口、Claude session 或 transcript 同时运行时，谁是“当前任务”不能依赖一个全局 active 文件。

推荐解析顺序：

1. 明确环境变量：`APEX_CONTEXT_ID`。
2. Hook input：`turn_id`、`session_id`、`conversation_id`、`transcript_path`。
3. Claude：`session_id`、`transcript_path`。
4. Codex：`turn_id`、Codex desktop/thread 字段、`CODEX_THREAD_ID`、`CODEX_RUN_ID` 等可用字段。
5. 仍无法解析时，不写 session pointer，只 fallback。

目标文件：

```json
{
  "schema_version": 1,
  "context_key": "sha256:...",
  "host": "codex",
  "slug": "settings-usage-statistics",
  "task_path": "tasks/loops/settings-usage-statistics",
  "todo_path": "tasks/todo+settings-usage-statistics.md",
  "review_path": "tasks/reviews/settings-usage-statistics.md",
  "created_at": "2026-06-28T00:00:00Z",
  "updated_at": "2026-06-28T00:00:00Z",
  "source": "hook-input.session_id"
}
```

fallback 规则：

1. session pointer 存在且 task 仍存在：使用它。
2. session pointer stale：返回 stale 状态，要求清理或重新选择，不静默改绑。
3. 没有 session pointer：使用 `active.json` 的 `owned_paths`。
4. `active.json` 也不能唯一决定：尝试 loop state。
5. 仍不能唯一决定：fail closed，提示用户选择 slug。

### 3. Context manifest + read-before-write gate

Claude 建议：

- implementer 必须读 `implement.jsonl`。
- code-reviewer 必须读 `review.jsonl`。
- Stop gate 检查 JSONL 引用的文件是否存在。
- 后续再检查 agent 是否声明已读。

判断：正确，但第一版要避免过度承诺。

推荐 JSONL schema：

```jsonl
{"kind":"file","path":"tasks/spec/hooks.md","reason":"Hook lifecycle rules and loop safety","required":true}
{"kind":"file","path":"tasks/loops/settings-usage-statistics/research/api-shape.md","reason":"Endpoint behavior confirmed during planning","required":true}
{"kind":"directory","path":"tasks/loops/settings-usage-statistics/research","reason":"Task-local research notes","required":false}
```

字段约束：

- `kind`：`file` 或 `directory`，默认 `file`。
- `path`：repo 相对路径，必须 normalize 后仍在 repo 内。
- `reason`：必须有，避免无意义上下文堆积。
- `required`：布尔值，默认 true。
- `scope`：可选，`implement`、`review`、`both`。
- `_example` 或没有 `path` 的 seed row 可跳过，但不能算作 ready。

第一版可可靠做到：

- JSONL 逐行解析。
- seed row 跳过。
- repo traversal 拦截。
- secret path 拦截。
- 文件/目录存在性校验。
- 目录引用只允许 `tasks/spec/`、`tasks/loops/<slug>/research/` 等白名单。
- SessionStart / SubagentStart 注入 manifest 摘要。
- Stop gate 在 manifest 引用失效时阻塞或 warning。

第二版再做：

- 记录 `Read` / `Grep` / `Glob` / MCP read 事件到 `reads.jsonl`。
- `SubagentStop` 要求 evidence 中声明已读 required manifest。
- Stop gate 比对 required manifest 与 read log/evidence。
- 对同一 context key 维护 read evidence，避免其他窗口的读取记录污染当前任务。

不能宣称的内容：

- hook 不能证明模型理解了文件。
- 工具 read log 也只能证明“工具访问过”，不能证明认知吸收。
- 所以文案应写成 “context evidence / declared read / tool access evidence”，不要写成 “guaranteed read comprehension”。

### 4. Spec / lessons promotion

Claude 建议：

```text
tasks/spec/
  index.md
  frontend.md
  backend.md
  testing.md
  git.md
  hooks.md
```

判断：正确，但应放 P2。

建议结构：

```text
tasks/spec/
  index.md
  architecture.md
  frontend.md
  backend.md
  testing.md
  git.md
  hooks.md
  security.md
  performance.md
```

职责划分：

- `tasks/lessons.md`：原始经验流水账，允许粗糙。
- `tasks/spec/*.md`：长期规则，要求稳定、可引用、去重。
- `AGENTS.md` / `CLAUDE.md`：入口行为契约，不应无限膨胀。
- `implement.jsonl` / `review.jsonl`：按任务引用具体 spec，不默认读取全部 spec。

`apex-update-spec` skill 合约：

- 输入：active task、review findings、run.md、lessons.md、diff summary。
- 识别长期规则：重复错误、新技术约定、跨模块接口、验证命令、host/hook 行为、Git 安全边界。
- 只写入长期规则，不写一次性实现细节。
- 每条规则保留来源：task slug、review path、run path。
- 修改前显示候选 promotion，避免把偶发判断固化成规则。

### 5. Finish-loop / record-session

Claude 建议：

- 检查 review ready + validation pass。
- 写 `run.md`。
- 记录 branch、diff 摘要、验证命令、已知限制。
- 标记 state done。
- 提醒是否提升 lessons 到 spec。
- 第一版不要自动 commit。

判断：完全正确，应放 P2。

建议 `run.md` 模板：

```markdown
# Run: <slug>

## Summary

## Scope

## Changed Files

## Review

- Review file:
- Status:
- Validation:
- Reviewed diff hash:

## Validation Commands

| Command | Exit | Notes |
| --- | ---: | --- |

## Known Limits

## Follow-ups

## Spec Promotion

- [ ] No long-lived lesson
- [ ] Promoted to `tasks/spec/...`
```

第一版不要自动 commit：

- ApexPowers 的 Git 规则强调只暂存当前任务直接产物，不能 `git add .`。
- 多 CLI 共存时，自动 commit 很容易把其他工具的 dirty files 混进来。
- 收工协议的价值是记录状态、验证、限制和后续提升，不依赖 commit。

### 6. Config knobs

Claude 建议 `tasks/loops/config.yaml` 或 JSON 配置。

判断：正确，但放在 P2。第一版建议用 JSON，避免新增 YAML parser 依赖。

建议：

```json
{
  "schema_version": 1,
  "line_length": {
    "frontend": {"warning": 300, "hard": 500},
    "script": {"warning": 350, "hard": 600},
    "backend": {"warning": 450, "hard": 750}
  },
  "review_gate": {
    "enabled": true,
    "require_independent_reviewer": true,
    "allow_automated_pass": true
  },
  "mirror_drift": {
    "post_tool_warn": true,
    "stop_block": true
  },
  "context_manifest": {
    "require_for_complex_tasks": true,
    "allowed_roots": ["tasks/spec", "tasks/loops"]
  }
}
```

读取策略：

- 配置缺失：使用默认值，不报错。
- 配置损坏：doctor warn，runtime fail soft 到默认值。
- 安全类 gate 默认不允许 silent disable；如果配置禁用，输出必须说明风险。

## 目标架构

### 文件结构

```text
tasks/
  todo+<slug>.md
  spec/
    index.md
    architecture.md
    frontend.md
    backend.md
    testing.md
    git.md
    hooks.md
    security.md
    performance.md
  loops/
    workflow.md
    config.json
    active.json                         # legacy / fallback / manual multi-task index
    .runtime/
      sessions/
        <context-key>.json              # session-scoped active task pointer
        <context-key>.snapshot.json     # session-scoped compaction snapshot
    <slug>/
      task.json
      state.json
      prd.md
      design.md
      implement.md
      implement.jsonl
      review.jsonl
      reads.jsonl
      failures.jsonl
      research/
      subagents/
        manifest.json
        <agent-id>.json
      run.md
  reviews/
    <slug>.md
  lessons.md
```

### `task.json` 推荐字段

不要照搬 Trellis 字段，但要保留稳定顺序和升级兼容。

```json
{
  "schema_version": 1,
  "task_id": "settings-usage-statistics",
  "slug": "settings-usage-statistics",
  "title": "Settings usage statistics",
  "status": "planning",
  "phase": "planning",
  "risk_level": "medium",
  "priority": "P2",
  "creator": "",
  "assignee": "",
  "created_at": "",
  "updated_at": "",
  "completed_at": null,
  "todo_path": "tasks/todo+settings-usage-statistics.md",
  "loop_dir": "tasks/loops/settings-usage-statistics",
  "review_path": "tasks/reviews/settings-usage-statistics.md",
  "branch": null,
  "base_branch": null,
  "worktree_path": null,
  "commit": null,
  "pr_url": null,
  "parent": null,
  "children": [],
  "owned_paths": [],
  "related_files": [],
  "notes": "",
  "meta": {}
}
```

写入规则：

- 必须保留未知字段。
- JSON 损坏时 fail closed，不覆盖。
- 所有路径都存 repo 相对路径。
- `status` 与 `phase` 可短期重复，长期建议 `status` 面向任务生命周期，`phase` 面向 workflow gate。
- `owned_paths` 用于 active task disambiguation 和 dirty path 分类。

### `state.json` 推荐职责

`state.json` 只记录 hook runtime 状态：

```json
{
  "schema_version": 1,
  "phase": "review_required",
  "last_diff_hash": "sha256:...",
  "last_block_reason_hash": "sha256:...",
  "block_count_for_same_reason": 1,
  "continuation_count": 0,
  "created_review_request": true,
  "security_required": false,
  "validation_required": true,
  "updated_at": ""
}
```

边界：

- `task.json` 不应该被每次 Stop 高频改写。
- `state.json` 不应该承载 branch、PR、owner 等稳定元数据。
- review 证据仍在 `tasks/reviews/<slug>.md`。
- final run 证据在 `run.md`。

### Subagent evidence manifest

目标：`SubagentStart` 注入任务契约，`SubagentStop` 回收结构化证据。

建议文件：

```text
tasks/loops/<slug>/subagents/
  manifest.json
  <agent-id>.json
```

`<agent-id>.json` 示例：

```json
{
  "schema_version": 1,
  "task_id": "settings-usage-statistics",
  "agent_id": "agent-abc",
  "agent_type": "implementer",
  "started_at": "",
  "stopped_at": "",
  "contract_files": [
    "tasks/loops/settings-usage-statistics/prd.md",
    "tasks/loops/settings-usage-statistics/implement.jsonl"
  ],
  "declared_read_files": [],
  "changed_files": [],
  "validation": [
    {"command": "npm test", "exit_code": 0}
  ],
  "result": "completed",
  "blockers": [],
  "notes": ""
}
```

`SubagentStart` 做：

- 识别 session-scoped active task。
- 根据 agent type 选择 `implement.jsonl` 或 `review.jsonl`。
- 注入 `task.json`、`prd.md`、可选 `design.md`、可选 `implement.md`。
- 注入 evidence path 和交付格式要求。
- 创建 started evidence。

`SubagentStop` 做：

- 读取 `last_assistant_message` 或 transcript path。
- 检查是否报告 changed files、validation commands、open risks。
- 对 implementer：至少要求“改了什么、跑了什么、剩余风险”。
- 对 code-reviewer：至少要求更新或引用 `tasks/reviews/<slug>.md`，并记录 findings / validation evidence。
- 处理 `stop_hook_active`，避免子 agent 内部无限循环。
- 证据不足时可以 block 一次或两次，达到上限后转父流程 `review_required`，不要让子 agent 空转。

## Host capability matrix

| 能力 | Claude Code | Codex | ApexPowers 策略 |
| --- | --- | --- | --- |
| `SessionStart` context injection | 支持 | 支持 | 双 host 保持 |
| `UserPromptSubmit` workflow breadcrumb | 支持 | 支持 | 双 host 保持 |
| `PreToolUse` block | 支持 | 支持 | 作为 guardrail，不当 sandbox |
| `PostToolUse` observe/validate | 支持 | 支持 | 继续 diff-aware + cache |
| `PostToolBatch` | host 差异可能存在 | 支持/版本相关 | 保留 route registry 渲染能力 |
| `PreCompact` | 支持/版本相关 | 支持 | 改成 session-scoped snapshot |
| `Stop` block/continue | 支持 | 支持 | 主完成门禁 |
| `SubagentStart` | 支持 context-only | 文档列出，版本/字段需实测 | P1 增加 route，缺字段时降级 |
| `SubagentStop` | 支持 block | 文档列出，版本/字段需实测 | P1 增加 evidence，最终 Stop 兜底 |

设计原则：

- 对支持完整 lifecycle 的 host，使用 hook 注入和 evidence。
- 对字段不完整的 host，降级到 SessionStart/UserPromptSubmit/agent prompt prelude。
- 无论 host 是否支持 subagent lifecycle，最终完成仍由 Stop ReviewGate 和 ValidationGate 裁决。

## 分阶段实施计划

### P0：固化当前 hook 基线

目标：不改变 runtime 行为，先把已完成能力、未完成能力、doctor 检查边界写清楚。

工作项：

- 更新 inventory 或 architecture 文档：
  - manifest/update/uninstall 已完成。
  - workflow-state 已完成。
  - ReviewGate/ValidationGate 当前 schema。
  - PreCompact snapshot 当前是全局文件，下一步变 session-scoped。
- 设计 `apex-doctor` 未来检查项：
  - route registry 是否含 expected events。
  - `tasks/loops/workflow.md` 状态块完整。
  - review frontmatter schema 可解析。
  - active task 是否 ambiguous。
  - manifest/update/uninstall 状态是否 drift。
- 增加文档化非目标：
  - 不复制 Trellis。
  - 不自动 commit。
  - 不把 hook 当 sandbox。

验收：

- 不改 runtime 行为。
- 现有 hook tests 全部通过。
- 文档与当前代码一致，不再把已完成 Phase A/B 当未来 P0。

### P1A：Loop task package

目标：把进入实现/review 的任务升级成机器可读任务包。

工作项：

- 新增 helper：
  - `ensure_loop_task(slug, todo_path)`。
  - `read_task_record()`。
  - `write_task_record()`。
  - `validate_task_record()`。
- 对 active todo 生成：
  - `tasks/loops/<slug>/task.json`
  - `tasks/loops/<slug>/prd.md`
  - `tasks/loops/<slug>/implement.jsonl`
  - `tasks/loops/<slug>/review.jsonl`
  - `tasks/loops/<slug>/research/`
- 保持兼容：
  - `tasks/todo+*.md` 继续有效。
  - 没有 task package 时，ReviewGate 仍可创建 review request，但提示升级。
  - existing `state.json` 不迁移破坏。

测试：

- 单 todo 生成 loop task package。
- 多 todo ambiguous 时不生成错误 slug。
- 已存在 `task.json` 时保留未知字段。
- 损坏 `task.json` 时 fail closed，不覆盖。
- Windows / POSIX path normalization。
- `prd.md` 已存在时不覆盖用户内容。
- seed JSONL 行不算 curated context。

验收：

- 新任务目录可被 hook、doctor、agent 模板共同读取。
- 小任务仍可只用 `todo+*.md`。
- 进入 review 的代码任务会自动拥有 package。

### P1B：Context manifest validation

目标：让 implementer/reviewer 的必读上下文可声明、可校验、可注入。

工作项：

- 新增 `validate-context` 命令：
  - 校验 `implement.jsonl` / `review.jsonl`。
  - 跳过 seed row。
  - 阻止 repo 外路径。
  - 阻止 secret 路径。
  - 限制 directory 引用根。
- 更新 agent 源模板：
  - `.agents/implementer.md` 读取 `implement.jsonl`。
  - `.agents/code-reviewer.md` 读取 `review.jsonl` 和 `prd.md`。
  - 同步 `.codex/agents/*.toml` / `.claude/agents/*.md`。
- Stop gate：
  - active task 存在 manifest 且引用失效时阻塞。
  - seed-only manifest 对轻量任务 warning，对复杂任务 block。

测试：

- invalid JSONL -> fail。
- missing file -> fail。
- repo traversal -> fail。
- secret path -> fail。
- disallowed directory -> fail。
- seed row only -> warning / configurable。
- valid manifest -> pass。

验收：

- Reviewer 不再只靠主 agent prompt 获得上下文。
- Context manifest 错误能在 subagent 执行前暴露。

### P1C：Session-scoped active task

目标：多窗口、多线程、多 agent 时 active task 不互相抢。

工作项：

- 新增 `resolve_context_key(hook_input, host)`。
- 新增：
  - `set_session_active_task()`。
  - `get_session_active_task()`。
  - `clear_session_active_task()`。
- active task 解析顺序改为：
  1. session runtime pointer。
  2. `tasks/loops/active.json` owned_paths。
  3. loop state。
  4. single todo。
  5. fail closed。
- `PreCompact` snapshot 改为 session-scoped：
  - `tasks/loops/.runtime/sessions/<context-key>.snapshot.json`
  - 旧 `tasks/loops/session-snapshot.json` 保留兼容。

测试：

- 两个 context key 指向不同 slug，互不覆盖。
- 缺 context key 时 fallback 行为不变。
- session pointer 指向 missing task 时标记 stale，不能错误绑定。
- finish/done 后清理 session pointer。
- PreCompact 写入当前 session snapshot。

验收：

- 并行任务场景不再依赖全局 `active.json`。
- ReviewGate 绑定 slug 的来源可解释。

### P1D：SubagentStart / SubagentStop evidence

目标：给子 agent 明确 task contract，并在子 agent 结束时验证证据。

工作项：

- Route registry 增加：
  - `SubagentStart`。
  - `SubagentStop`。
- matcher 先覆盖：
  - `implementer`
  - `developer`
  - `code-reviewer`
  - `researcher`
  - `perf-optimizer`
  - host 对应 agent names。
- Runtime 增加：
  - `subagent_start(context)`。
  - `subagent_stop(context)`。
- `SubagentStart`：
  - 根据 agent type 注入 contract。
  - 指向 `task.json`、`prd.md`、manifest。
  - 创建 started evidence。
- `SubagentStop`：
  - 检查 last assistant message / transcript 摘要。
  - 缺 modified files / validation / review output 时要求补证据。
  - 处理 `stop_hook_active`。
- Codex 降级：
  - 如果没有完整 lifecycle 字段，就只在 SessionStart/UserPromptSubmit/agent prompt 中注入 contract，最终由 Stop gate 兜底。

测试：

- Claude-style SubagentStart input 注入 context。
- Codex-style SubagentStart input 注入 context。
- 缺 active task 时 SubagentStart 输出轻量 fallback contract。
- SubagentStop missing evidence -> block/continue。
- `stop_hook_active: true` -> 不重复 block。
- agent_type matcher 不匹配 -> no-op。
- 并发 subagent evidence 写入不损坏 manifest。

验收：

- 子 agent 不能只说 “done” 就结束。
- 子 agent evidence 不替代独立 review。
- 主 Stop gate 仍是最终完成门禁。

### P2A：Spec promotion

目标：把 review/lessons/run 中的长期知识提升到 `tasks/spec/`。

工作项：

- 初始化 `tasks/spec/index.md` 和主题文件。
- 新增 `apex-update-spec` skill。
- `SessionStart` 从 `tasks/spec/index.md` 提示可用 spec。
- `implement.jsonl` / `review.jsonl` 优先引用 `tasks/spec`。

测试：

- `tasks/spec` 缺失时 doctor warn。
- index 引用的 spec 文件不存在时 doctor warn/fail。
- `apex-update-spec` 不覆盖已有规则，只追加或更新指定 section。
- 一次性实现细节不会被提升。

验收：

- `tasks/lessons.md` 不再是唯一经验入口。
- 复用规则能被 manifest 精确引用。

### P2B：Finish loop and run journal

目标：形成标准收工协议。

工作项：

- 新增 skill：`apex-finish-loop`。
- 新增 runtime/manual command：`finish-loop <slug>` 可选。
- 生成或更新 `run.md`。
- 标记 `task.json.status = done`，`state.json.phase = done`。
- 提醒 spec promotion。
- 不自动 commit。

测试：

- review missing -> fail。
- validation missing -> fail。
- stale review diff -> fail。
- all pass -> writes run.md and marks done。
- dirty unrelated files -> warn and do not include。
- dirty current-task files -> fail，提示先完成 review/validation。

验收：

- Stop gate 通过后还有清晰的记录、归档、提升经验路径。
- 不破坏当前 Git 边界规则。

### P2C：Config externalization

目标：让阈值可调，但不把系统变成配置迷宫。

工作项：

- 新增 `tasks/loops/config.json`。
- 读取配置时 fail soft。
- 可配置范围先限制在：
  - line length thresholds。
  - review gate enabled / reviewer role policy。
  - mirror drift Stop block。
  - context manifest required policy。
  - subagent evidence continuation limit。

测试：

- 缺配置 -> defaults。
- 损坏配置 -> warn + defaults。
- frontend/backend thresholds override 生效。
- 禁用某 gate 时输出风险说明。

验收：

- 团队项目可以调阈值，不需要改 Apex runtime 源码。

### P3：暂缓的 Trellis 重模块

暂不做：

- channel / worker event-log。
- marketplace / registry。
- 自动 archive commit / journal commit。
- 多平台全量 configurator。
- 自动递归 agent 编排。
- 类 Temporal 的 durable execution runtime。

理由：

- ApexPowers 当前优势是轻量、私有、中文任务契约和 Codex/Claude 双 host 贴合。
- 重型 channel/worker 系统会提高 onboarding 成本。
- 当前最大风险是 active task 绑定和 context manifest 缺失，不是缺少大型平台能力。

## 查缺补漏清单

Claude 原建议之外，还应补这些点：

1. `task.json` / `state.json` 职责分离。
2. Host capability matrix 和版本探测。
3. `reads.jsonl` 作为 P2 读取证据，不在 P1 过度承诺。
4. session-scoped PreCompact snapshot，避免全局 `session-snapshot.json` 被多窗口覆盖。
5. `owned_paths` 从 `active.json` 迁移到 `task.json`，保留 `active.json` 作为 fallback。
6. context manifest 目录引用白名单和大小限制，避免把整个 repo 注入。
7. `apex-doctor` 对 task package、manifest、session pointer、spec index 的检查。
8. subagent evidence 并发写入需要锁或原子 rename。
9. finish-loop 必须分类 dirty files，但不自动 stage/commit。
10. AGPL 风险要写入开发规则，避免未来 agent 直接复制 Trellis 源码。

## 风险与防护

| 风险 | 防护 |
| --- | --- |
| AGPL 许可证风险 | 只借鉴架构，不复制 Trellis 源码、模板正文或实现细节 |
| 复杂度膨胀 | 小任务保持 `todo+*.md` 轻流程，只有实现/review 任务升级 package |
| “读过文件”的虚假保证 | 第一版只做 manifest 校验和 context 注入，读证明等 read log/evidence |
| 多窗口覆盖 | P1 做 session-scoped active task，全局 `active.json` 变 fallback |
| hook 性能 | manifest 校验放 Stop/SubagentStart，PostToolUse 继续 diff-aware + cache |
| Codex / Claude 能力差异 | 做 capability matrix 和 runtime feature detection |
| 自动提交误伤 | 第一版 finish-loop 不自动 commit，只生成 `run.md` 和状态 |
| ReviewGate 过强误伤 | config 外部化，但默认 fail closed |
| 子 agent 空转 | `SubagentStop` block 次数上限，之后转父流程 `review_required` |
| context bloat | JSONL 必须写 `reason`，directory 引用受限，seed row 不算 ready |

## 最小可行实现切片

如果只做一轮，建议做 3 个切片：

1. P1A：`task.json` + `prd.md` + JSONL seed + backward compatibility。
2. P1C：session-scoped active task。
3. P1B 轻量版：`validate-context` 只检查 JSONL 语法、repo 内路径和文件存在；Stop gate 先 warning，复杂任务再 block。

这一轮能解决 ApexPowers 与 Trellis 差距最大的两个问题：任务不是机器可读包、active task 不是会话级。同时不会把 hook runtime 推成复杂编排系统。

第二轮再做：

1. P1D：SubagentStart/SubagentStop evidence。
2. P2A：tasks/spec + apex-update-spec。
3. P2B：apex-finish-loop + run.md。

## 建议 issue 拆分

### Issue 1：Loop task package schema

交付：

- `task.json` schema。
- helper read/write/validate。
- `prd.md` seed。
- `implement.jsonl` / `review.jsonl` seed。
- tests。

不做：

- 不做 session pointer。
- 不做 subagent hook。

### Issue 2：Context manifest validator

交付：

- JSONL parser。
- repo path validator。
- allowed roots。
- seed row handling。
- `validate-context` command。
- tests。

不做：

- 不做 read log。
- 不做强制理解证明。

### Issue 3：Session-scoped active task

交付：

- context key resolver。
- `.runtime/sessions/<context-key>.json`。
- active task resolver 顺序改造。
- session snapshot 改造。
- tests。

不做：

- 不删除 `active.json`。

### Issue 4：Subagent lifecycle evidence

交付：

- route registry 加 `SubagentStart` / `SubagentStop`。
- evidence schema。
- SubagentStart contract 注入。
- SubagentStop evidence 校验。
- host fallback。
- tests。

不做：

- 不做重型验证。
- 不让 subagent evidence 代替独立 review。

### Issue 5：Spec promotion

交付：

- `tasks/spec/` 初始结构。
- `apex-update-spec` skill。
- manifest 引用 spec 的规则。
- doctor 检查。

不做：

- 不自动把所有 lessons 提升。

### Issue 6：Finish loop

交付：

- `apex-finish-loop` skill。
- `run.md` 模板。
- dirty file 分类。
- review/validation/diff hash 检查。
- state done 标记。

不做：

- 不自动 commit。
- 不自动 archive unrelated tasks。

### Issue 7：Config externalization

交付：

- `tasks/loops/config.json`。
- defaults。
- damaged config warning。
- limited knobs。
- tests。

不做：

- 不把所有行为都配置化。

## 成功标准

短期成功：

- 一个实现任务能从 `todo+*.md` 升级到 `tasks/loops/<slug>/` 任务包。
- 多窗口不会互相抢 active task。
- reviewer 能看到明确的 `review.jsonl` 上下文 manifest。
- Stop gate 对 stale/missing context 给出可执行错误。

中期成功：

- 子 agent 有 contract 和 evidence。
- review/validation/run 形成闭环。
- lessons 能提升为 `tasks/spec/`。
- doctor 能发现 task package、session pointer、spec index、manifest 的 drift。

长期成功：

- ApexPowers 仍保持轻量，不变成完整 Trellis 克隆。
- Agent 上下文越来越精确，规则能随项目演化。
- 并行 Codex/Claude 窗口可以安全共存。
- 用户能从 `run.md`、review、spec 中追溯每次任务的需求、实现、审查和验证。

## 参考链接

- OpenAI Codex Hooks 官方文档：https://developers.openai.com/codex/hooks
- Claude Code Hooks 官方文档：https://code.claude.com/docs/en/hooks
- Anthropic context engineering：https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- LangChain context engineering：https://www.langchain.com/blog/context-engineering-for-agents
- 12-Factor Agents：https://github.com/humanlayer/12-factor-agents
- Trellis GitHub：https://github.com/mindfold-ai/Trellis
- Trellis Docs：https://docs.trytrellis.app/
- `disler/claude-code-hooks-mastery`：https://github.com/disler/claude-code-hooks-mastery
- OpenAI Developer Community Codex hooks framework 讨论：https://community.openai.com/t/codex-hooks-framework-letting-codex-extend-local-workflows-from-user-policy/1381486
- Codex subagent hook metadata issue：https://github.com/openai/codex/issues/16226
