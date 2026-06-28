# Subagent Hooks Contract Evidence

日期：2026-06-28

## 结论

当前 ApexPowers hook 体系缺少 `SubagentStart` / `SubagentStop` 两个边界 hook。

这不是现有 `Stop` ReviewGate 的 bug。现有 ReviewGate 解决的是“主任务最终能否结束”的问题；`SubagentStart` / `SubagentStop` 解决的是“子代理被派出去时是否拿到了明确契约，以及子代理回来时是否交付了结构化证据”的问题。两者应当叠加，而不是互相替代。

如果后续 ApexPowers 继续强化 subagent / loop 工作流，建议补这一层，但不要把它做成重型 review。更稳的边界是：

- `SubagentStart`：给子代理注入当前 task contract、slice 范围、允许/禁止路径、必须产出的 evidence artifact 路径。
- `SubagentStop`：只做快速结构校验和证据收集；缺证据时把原因反馈给子代理继续工作，或标记父流程 `review_required`。
- 主 `Stop` ReviewGate：仍然是最终完成门禁，只信独立 review frontmatter、验证证据和当前 diff hash。

## 检索与证据边界

本轮按用户要求先尝试 groksearch：

- 查询 `Claude Code SubagentStart SubagentStop hooks task contract evidence validation best practices`
- 查询 `Claude Code hooks SubagentStart SubagentStop agent_transcript_path ...`
- 结果：groksearch 返回 `grok_provider_error`，source fallback 为 0，不能作为可验证证据。

随后用官方文档和公开 GitHub 仓库做交叉核对：

- 官方 hooks 文档：[Hooks reference](https://code.claude.com/docs/en/hooks)
- 官方 subagents 文档：[Create custom subagents](https://code.claude.com/docs/en/sub-agents)
- 社区示例仓库：[disler/claude-code-hooks-mastery](https://github.com/disler/claude-code-hooks-mastery)
- 社区平台适配仓库：[mksglu/context-mode](https://github.com/mksglu/context-mode)
- 资源索引仓库：[hesreallyhim/awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code)

证据强度判断：

- 强证据：Claude Code 官方文档明确列出 `SubagentStart`、`SubagentStop`，并说明 `SubagentStop` 可以用与 `Stop` 相同的 decision control。
- 中等证据：`claude-code-hooks-mastery` 把 `SubagentStop` 作为可阻止子代理停止的 hook，并给出并行 subagent 测试思路。
- 弱证据：公开社区仓库更多是演示、资源列表或平台适配说明，尚未看到成熟统一的“task contract artifact + evidence schema + ReviewGate 集成”的事实标准。

## 当前项目状态

当前 route registry 只注册这些事件：

- `SessionStart`
- `UserPromptSubmit`
- `PreToolUse`
- `PostToolUse`
- `PostToolBatch`
- `PreCompact`
- `Stop`

证据位置：

- `.codex/skills/apex-init-project-hooks/scripts/apex_loop_routes.py`
- `.codex/skills/apex-init-project-hooks/templates/codex-hooks.json`
- `.codex/skills/apex-init-project-hooks/templates/claude-settings.json`

`rg` 未发现当前 hook runtime 或模板中存在 `SubagentStart` / `SubagentStop` 注册。

当前已有的相关能力：

- `apex-init-project-agent` 的根规则已经包含“契约式小任务 + 运行时结构化分解 + 证据化验收”。
- 同一模板也要求“多文件/并行任务使用 Subagent 隔离”。
- Stop ReviewGate 已经要求 review frontmatter、`reviewed_diff_hash`、`validation_evidence` 和 reviewer role。

缺口是：这些约束现在主要靠根规则和最终 Stop gate，并没有在子代理生命周期边界上被 hook 强制执行。

## 官方语义要点

官方 hooks 文档中，`SubagentStart` 在子代理被 Agent tool 生成时触发，matcher 匹配 `agent_type`。它接收 `agent_id` 和 `agent_type`，但属于 context-only 事件，不能 block，只适合注入 context 或记录状态。

`SubagentStop` 在子代理结束响应时触发，matcher 同样匹配 `agent_type`。它接收：

- `stop_hook_active`
- `agent_id`
- `agent_type`
- `agent_transcript_path`
- `last_assistant_message`
- 父 session 的 `transcript_path`

官方语义里，`SubagentStop` 与 `Stop` 使用同类 decision control。返回 `decision: "block"` 和 `reason` 会让子代理继续，并把原因作为下一条指令交给子代理。

重要边界：官方同时说明，如果想把 context 注入父会话，应该用 `Agent` 工具的 `PostToolUse` hook，而不是指望 `SubagentStop` 直接改父上下文。

## 是否应该补

建议补，但只在以下目标成立时补：

- 你确实会频繁使用 subagent / loop / 并行任务。
- 你希望每个子代理都有明确 slice contract。
- 你希望子代理不能只返回一段自然语言总结就被认为完成。
- 你希望最终 ReviewGate 能知道“哪些子代理参与过、各自交付了什么证据”。

不建议把它补成：

- 每个子代理结束都跑完整 test suite。
- 每个子代理结束都做全量 diff review。
- 在 `SubagentStart` 里尝试阻止子代理启动。
- 在 `SubagentStop` 里递归生成更多 agent 做复杂验证。

理由很简单：hook 要快，尤其是频繁触发的生命周期 hook。重逻辑应该放到主 Stop gate、独立 reviewer、CI 或显式验证步骤。

## 推荐目标设计

### SubagentStart

目标：让子代理一开始就拿到可执行的小任务契约，而不是只收到一句泛泛委托。

建议注入内容：

```xml
<apex-subagent-contract schema_version="1">
  <task_id>...</task_id>
  <task_slug>...</task_slug>
  <slice_id>...</slice_id>
  <parent_session_id>...</parent_session_id>
  <agent_id>...</agent_id>
  <agent_type>...</agent_type>
  <allowed_paths>
    <path>src/settings/**</path>
  </allowed_paths>
  <forbidden_paths>
    <path>auth/**</path>
  </forbidden_paths>
  <required_checks>
    <check>npm run typecheck</check>
  </required_checks>
  <evidence_path>tasks/loops/subagents/<task_slug>/<agent_id>.json</evidence_path>
</apex-subagent-contract>
```

如果找不到 active todo 或 slice，`SubagentStart` 不应该硬失败。更好的行为是注入一段短 context：当前没有明确 slice contract，子代理必须在最终输出里声明 scope、assumptions、evidence 和 blockers。

### SubagentStop

目标：验证子代理是否交付了机器可读证据，而不是验证它的代码一定正确。

建议要求 evidence JSON：

```json
{
  "schema_version": 1,
  "task_id": "settings-usage-statistics",
  "task_slug": "settings-usage-statistics",
  "slice_id": "settings-ui",
  "agent_id": "agent-abc123",
  "agent_type": "developer",
  "status": "done",
  "owned_paths": ["src/settings/**"],
  "changed_files": ["src/settings/page.tsx"],
  "validation_evidence": [
    {
      "command": "npm run typecheck",
      "exit_code": 0,
      "summary": "typecheck passed"
    }
  ],
  "artifacts": ["tasks/todo+settings-usage-statistics.md"],
  "blockers": [],
  "handoff_summary": "Implemented settings toggle UI and persistence wiring."
}
```

最低校验：

- JSON 可解析。
- `schema_version` 支持。
- `task_id` / `slice_id` / `agent_id` 与当前状态匹配。
- `status` 只能是 `done`、`partial`、`blocked`。
- `changed_files` 不越过 `allowed_paths`，不触碰 `forbidden_paths`。
- 如果 `status = done`，至少有一条 validation evidence 或明确说明为什么无需运行命令。
- 如果 `status = blocked`，必须有 blocker 描述，不应反复 block 同一原因。

`SubagentStop` 的输出策略：

- 证据缺失且可由子代理补齐：返回 `decision: "block"`，给出精确补交要求。
- 证据表明需要人工/主线程处理：记录 state，允许子代理停止，把父流程标记为 `review_required`。
- 证据完整：写入 subagent manifest，允许停止。

## 与现有 ReviewGate 的关系

不要让子代理证据直接等价于最终 Ready/Pass。

推荐关系：

- 子代理 evidence 是“交付材料”和“trace”。
- Stop ReviewGate 是最终完成门禁。
- ReviewGate 可以要求：如果本轮有 subagent 参与，则必须存在对应 evidence manifest。
- ReviewGate 不应因为子代理写了 `status: done` 就跳过独立 review。
- 独立 reviewer 的 frontmatter 仍然必须包含 `reviewed_diff_hash` 和 `validation_evidence`。

这与当前 `init_project_agent.py` 里的“契约式小任务 + 运行时结构化分解 + 证据化验收”不冲突。相反，Subagent hooks 是把这套文字契约从“行为规范”提升到“运行时证据收集”的自然延伸。

## 推荐状态文件

建议新增状态面，不污染现有 review 文档：

```text
tasks/loops/subagents/
  <task_slug>/
    manifest.json
    <agent_id>.json
```

`manifest.json` 示例：

```json
{
  "schema_version": 1,
  "task_slug": "settings-usage-statistics",
  "parent_session_id": "abc123",
  "subagents": [
    {
      "agent_id": "agent-abc123",
      "agent_type": "developer",
      "slice_id": "settings-ui",
      "status": "done",
      "evidence_path": "tasks/loops/subagents/settings-usage-statistics/agent-abc123.json"
    }
  ]
}
```

后续 `tasks/reviews/<slug>.md` 可以只链接 evidence manifest，不要把所有子代理输出复制进去。

## 防循环与并发

`SubagentStop` 和 `Stop` 一样需要防循环。建议状态里记录：

```json
{
  "last_subagent_block_reason_hash": "",
  "subagent_block_count_for_same_reason": 0,
  "max_subagent_continuations": 2,
  "seen_agent_ids": [],
  "evidence_dedupe_keys": []
}
```

同一个 `agent_id + reason_hash` 重复出现时，不要无限 `decision: "block"`。达到上限后应转成父流程 `review_required` 或 `blocked`，让主线程汇报而不是让子代理空转。

并行子代理结束时，要避免多进程同时写 manifest 造成竞争。社区示例里常见做法是文件锁或队列；ApexPowers 可以沿用现有 `failures.jsonl` / state 写入的去重思路，写入时使用短锁文件或原子 rename。

## 建议优先级

1. 文档和测试先行：先把 `SubagentStart` / `SubagentStop` route 渲染、输入 fixture、输出 JSON 契约写成 tests。
2. 轻量 runtime：只实现 active todo 查找、contract 注入、evidence JSON 校验、manifest 记录。
3. Stop 集成：如果 manifest 显示本轮有 subagent，但缺 evidence，Stop 阻止最终完成。
4. 再考虑 agent-type hook：复杂验证可以后续接入 `type: "agent"`，但不建议第一版就上。

## 对 Codex 的可移植性判断

Claude Code 官方已经支持 `SubagentStart` / `SubagentStop`。

Codex 侧是否有完全同名事件，需要按当前 Codex hook 文档和 runtime 实测确认。ApexPowers 是双 host 项目，因此实现时应该：

- Claude host：直接注册 `SubagentStart` / `SubagentStop`。
- Codex host：如果没有等价事件，不要假装支持；可以通过 `PostToolUse` 监听 agent 工具输出、或在 Stop gate 检查 subagent evidence manifest 作为降级路径。
- 文档中明确：这是 guardrail，不是完整 enforcement boundary。

## 最终建议

补 `SubagentStart` / `SubagentStop` 是合理的，尤其与你现有“契约式小任务 + 运行时结构化分解 + 证据化验收”方向一致。

第一版不要追求“社区顶级复杂编排”。更稳的是做成窄而硬的证据门：

- 开始时注入 contract。
- 结束时验证 evidence。
- 父 Stop gate 做最终裁决。
- 重验证留给独立 reviewer / CI / 显式命令。

这样既能补上 subagent/loop 的关键缺口，又不会让 hook runtime 变成复杂、慢、容易死循环的代理编排器。
