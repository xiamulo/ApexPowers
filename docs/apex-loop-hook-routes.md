# Apex Loop Hook Routes

本文说明 ApexPowers loop hooks 的触发时机、执行内容、输出语义、阻塞边界和状态文件影响。它面向日常使用和排障：看到某个 hook 输出时，可以直接判断它为什么出现、是否会阻塞、下一步该做什么。

## 事实源

当前 hook 的事实源不是手写表格，而是 route registry 和 runtime：

| 内容 | 文件 |
| --- | --- |
| route、event、matcher、命令渲染 | `.codex/skills/apex-init-project-hooks/scripts/apex_loop_routes.py` |
| hook CLI dispatch 和 guard 编排 | `.codex/skills/apex-init-project-hooks/scripts/apex_loop_runtime.py` |
| workflow、review、state、diff hash、路径和 line count helper | `.codex/skills/apex-init-project-hooks/scripts/apex_loop_utils.py` |
| Codex JSON 参考模板 | `.codex/skills/apex-init-project-hooks/templates/codex-hooks.json` |
| Claude JSON 参考模板 | `.codex/skills/apex-init-project-hooks/templates/claude-settings.json` |

`HostConfigRenderer` 会把 route registry 渲染成 Codex / Claude hook 配置。Windows 默认命令形态是：

```powershell
py -3 "<hook-root>/apex_loop.py" <command> --host <codex|claude> --route <route-id>
```

非 Windows 默认使用 `python3`。安装后的真实 `<hook-root>` 取决于 `apex-init-project-hooks` 的安装 scope，通常在 Codex / Claude agent root 的 `hooks/` 目录下。

## 总览

| Hook event | Route | Matcher | 命令 | 生效后怎样 |
| --- | --- | --- | --- | --- |
| `SessionStart` | `default` | 无 | `session-start` | 会话开始时注入 Apex Loop Context，只提示，不阻塞。 |
| `UserPromptSubmit` | `default` | 无 | `user-prompt-submit` | 用户提交 prompt 后输出 `<apex-workflow-state>`；检测到 review / planning / done 语义时追加 route hint，只提示，不阻塞。 |
| `PreToolUse` | `safety-write` | `Edit|Write|MultiEdit|apply_patch` | `pre-tool-use` | 写入前检查路径越界、secret 路径、待写入内容里的疑似密钥；命中时阻止工具执行。 |
| `PreToolUse` | `safety-read` | `Read|Grep|Glob|mcp__.*` | `pre-tool-use` | 读取前检查路径越界和 secret 路径；命中时阻止工具执行。 |
| `PreToolUse` | `safety-shell` | `Bash|Shell|PowerShell` | `pre-tool-use` | shell 执行前拦截危险命令、破坏性 git、远程脚本管道执行、明显 shell 写入里的疑似密钥；命中时阻止工具执行。 |
| `PostToolUse` | `edit` | `Edit|Write|MultiEdit|apply_patch` | `post-tool-use` | 编辑后扫描相关路径，检查 secret 内容、源码有效行数和 agent mirror drift；secret 会要求跟进清理，行数和镜像漂移先 warn。 |
| `PostToolUse` | `bash` | `Bash|Shell|PowerShell` | `post-tool-use` | shell 后根据 redirect / PowerShell 写入目标或 git changed files 回看文件，做同一组后置检查。 |
| `PostToolUse` | `always` | 无 | `post-tool-use` | 每次工具后兜底观察 changed files，覆盖非 edit/bash 工具造成的文件变化。 |
| `PostToolBatch` | `default` | 无 | `post-tool-batch` | 批量工具调用后复用 `post-tool-use` 检查逻辑，配合 cache / dedupe 减少重复噪声。 |
| `PreCompact` | `default` | `auto|manual` | `pre-compact` | context compaction 前写入 `tasks/loops/session-snapshot.json`，并把快照位置注入上下文；只提示，不阻塞。 |
| `Stop` | `default` | 无 | `stop` | agent 准备结束时执行收口门禁；security、mirror drift、行数硬上限、review、validation、stale diff 等问题会阻止结束。 |

## SessionStart

`SessionStart` 在新会话开始时运行：

```powershell
py -3 "<hook-root>/apex_loop.py" session-start --host codex --route default
```

它输出 host 可识别的 `hookSpecificOutput.additionalContext`，把以下信息注入到会话上下文：

| 字段 | 来源 | 用途 |
| --- | --- | --- |
| Branch | `git branch --show-current` | 让 agent 知道当前分支。 |
| Changed files | git diff + untracked files | 提醒当前 worktree 是否已经有改动。 |
| Workflow state | `tasks/loops/workflow.md`、active task、review、validation、diff | 提醒当前处于 planning / review_required / validation_required / done 等状态。 |
| Active todo candidates | 最近修改的 `tasks/todo+*.md` | 帮助 agent 选择当前任务上下文。 |
| Review attention | `tasks/reviews/*.md` | 提醒 pending / invalid / validation-missing 的 review 文件。 |
| Recent lessons | `tasks/lessons.md` | 注入最近经验教训。 |

这个 hook 是 advisory。它不会阻止会话开始，也不会自动创建 review 或修改代码。

## UserPromptSubmit

`UserPromptSubmit` 在用户每次提交 prompt 后运行：

```powershell
py -3 "<hook-root>/apex_loop.py" user-prompt-submit --host codex --route default
```

它始终输出一个 XML-like 状态块：

```xml
<apex-workflow-state status="review_required" source="tasks/loops/workflow.md">
Code changes require review before completion.
</apex-workflow-state>
```

`status` 由当前仓库状态推导：

| Status | 触发条件 | 推荐动作 |
| --- | --- | --- |
| `no_task` | 没有 active todo 或可推导任务。 | 普通答疑可继续；实现前先建立 todo。 |
| `planning` | 有 active todo，但尚未进入实现或 review。 | 明确范围、验收和验证方式。 |
| `implementing` | loop state 标记实现中。 | 按 todo 小步推进并验证。 |
| `security_required` | `tasks/loops/security-required.json` 存在。 | 清理疑似密钥内容，真实凭据需要轮换。 |
| `review_required` | 有代码 diff 且 review 未 ready，或 review 已过期。 | 读取 diff 和 active todo，更新 `tasks/reviews/<slug>.md`。 |
| `validation_required` | review ready 但 validation 缺失或未通过。 | 运行验证，把证据写入 review frontmatter。 |
| `done` | review 和 validation 覆盖当前 diff。 | 可以结束任务或进入提交流程。 |

它还会根据 prompt 文本输出 route hint：

| Prompt 语义 | Hint |
| --- | --- |
| 包含 `review`、`审查`、`验收`、`检查` | 优先读取 active todo、diff 和 `tasks/reviews`，再调用 reviewer。 |
| 包含 `plan`、`计划`、`方案`、`todo` | 可以先写 `tasks/todo+任务名.md`，确认范围后再实现。 |
| 包含 `完成`、`收工`、`done`、`提交` | 提醒 Stop gate 会检查 diff、review 和验证证据。 |

这个 hook 只提示，不阻塞 prompt。

## PreToolUse

`PreToolUse` 是工具执行前门禁。它可以用 host 的 deny / exit code 2 阻止工具继续执行。

### safety-write

触发 matcher：

```text
Edit|Write|MultiEdit|apply_patch
```

检查内容：

| Guard | 检查什么 | 命中后 |
| --- | --- | --- |
| `PathGuard` | 工具 payload 中的路径是否在 repo 内，是否存在 traversal 或无法安全解析。 | deny，要求只读写仓库内路径。 |
| `SecretPathGuard` | `.env`、`.npmrc`、`.pypirc`、SSH key、credential、token、secret、private-key 等路径。 | deny，要求改用 example / sample / template 或由用户手动处理。 |
| `SecretContentGuard` | `content`、`new_string`、`edits[].new_string`、apply_patch added lines 中是否有 private key、OpenAI key、GitHub PAT、AWS key、Slack token 等。 | deny，工具不会执行。 |

### safety-read

触发 matcher：

```text
Read|Grep|Glob|mcp__.*
```

检查内容：

| Guard | 检查什么 | 命中后 |
| --- | --- | --- |
| `PathGuard` | 读取路径是否能安全归一化到 repo 内。 | deny。 |
| `SecretPathGuard` | 是否读取 secret-like 文件或路径模式。 | deny。 |

这个 route 主要防止 agent 通过 Read / Grep / Glob / MCP 工具意外打开真实凭据。

### safety-shell

触发 matcher：

```text
Bash|Shell|PowerShell
```

检查内容：

| Guard | 例子 | 命中后 |
| --- | --- | --- |
| `SecurityGuard` | `rm -rf /`、`rm -rf ~`、`git reset --hard`、`git checkout --`、`git push --force`。 | deny，要求用户明确授权或改用更小范围命令。 |
| `SecurityGuard` | `curl ... | bash`、`wget ... | sh`、`Invoke-WebRequest ... | iex`、`eval`。 | deny，避免远程脚本和动态执行。 |
| `SecretContentGuard` | shell command 明显写文件，且写入文本里出现疑似 key。 | deny，工具不会执行。 |

PreToolUse 的失败输出会包含：

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "[GuardName] reason Fix: ..."
  }
}
```

## PostToolUse

`PostToolUse` 在工具执行后运行。因为工具已经执行，它不能撤销写入；它负责快速反馈、记录 failure、把严重问题转成后续 Stop 阻塞条件。

路径来源按优先级合并：

1. host payload 中的 `file_path`、`path`、`target_file` 等字段。
2. apply_patch 文本里的 `*** Add File:`、`*** Update File:`、`*** Delete File:`、`*** Move to:`。
3. shell redirect、`Set-Content`、`Add-Content`、`Out-File` 等写入目标。
4. 如果没有明确路径，回退到 git changed files。

### edit

触发 matcher：

```text
Edit|Write|MultiEdit|apply_patch
```

执行检查：

| Guard | 行为 |
| --- | --- |
| `SecretContentGuard` | 扫描相关文件内容；命中后写 `tasks/loops/security-required.json`，返回 follow-up required。 |
| `LineLengthGuard` | 计算源码有效行数；超过 warning 线或 hard 线时输出 warning。PostToolUse 阶段不因行数直接阻断。 |
| `MirrorDriftGuard` | 如果 `.agents/<name>.md` 变了，但 `.codex/agents/<name>.toml` 或 `.claude/agents/<name>.md` 没一起变，输出 warning。 |

### bash

触发 matcher：

```text
Bash|Shell|PowerShell
```

它和 `edit` 走同一套后置检查，只是路径提取更依赖 shell 命令文本和 git fallback。设计原因是 shell 也可能通过 redirect、脚本、formatter、generator 修改文件。

### always

没有 matcher，作为兜底 route。它保证即使某个 host 的工具名没被 `edit` / `bash` matcher 覆盖，hook 仍会从 git changed files 观察当前 worktree。

### PostToolUse 输出语义

| 情况 | 输出 | 后续影响 |
| --- | --- | --- |
| 未发现问题 | exit 0，通常无输出。 | 继续。 |
| 行数超过 warning / hard | stderr 输出结构化 warning，并记录到 failures jsonl。 | Stop 阶段 hard limit 可能 block。 |
| agent mirror drift | stderr 输出 `MirrorDriftGuard` warning。 | Stop 阶段会 block。 |
| 疑似 secret 内容 | 输出 follow-up required，并写 `security-required.json`。 | workflow 进入 `security_required`，Stop 会 block。 |

## PostToolBatch

`PostToolBatch` 的 command 是：

```powershell
py -3 "<hook-root>/apex_loop.py" post-tool-batch --host codex --route default
```

runtime dispatch 会复用 `post_tool_use`。它适合 host 在一批工具调用结束后统一触发，配合 guard cache 和 failure dedupe 降低重复扫描。

## PreCompact

`PreCompact` 在上下文压缩前运行：

```powershell
py -3 "<hook-root>/apex_loop.py" pre-compact --host codex --route default
```

它写入：

```text
tasks/loops/session-snapshot.json
```

快照包含：

| 字段 | 含义 |
| --- | --- |
| `workflow_state` | 当前 workflow status。 |
| `workflow_source` | 状态提示来自 `workflow.md` 还是 fallback。 |
| `active_task` | 当前 active task slug。 |
| `todo_path` | 对应 todo 文件。 |
| `review_path` | 对应 review 文件。 |
| `changed_files` | 当前 git changed files。 |
| `current_diff_hash` | 当前 code diff fingerprint。 |
| `blockers` | compact-safe blocker 摘要。 |
| `security_required` | 是否存在 security-required 状态。 |

这个 hook 只保存上下文，不阻塞 compaction。

## Stop

`Stop` 是收口门禁。它在 agent 准备结束当前 turn 时运行：

```powershell
py -3 "<hook-root>/apex_loop.py" stop --host codex --route default
```

Stop 的检查顺序是：

1. `security_required_failure`：如果 PostToolUse 已经发现疑似 secret 内容，阻塞。
2. `MirrorDriftGuard`：如果 `.agents/*.md` 改了但 Codex / Claude 镜像没同步，阻塞。
3. `LineLengthGuard`：对 changed source files 做硬上限检查；本次新增或跨过 hard limit 的文件阻塞。
4. `ReviewGate`：有 reviewable code diff 时，要求 active todo 和 review 文件满足合约。
5. `ValidationGate`：review ready 后必须有通过的验证证据。

Stop 成功时 exit 0。失败时输出：

```json
{
  "decision": "block",
  "reason": "[ReviewGate] demo 有代码 diff，但还没有通过 code-reviewer review。 Fix: ..."
}
```

### ReviewGate 什么时候触发

`ReviewGate` 只关心 reviewable code path。文档、todo-only 改动通常不会触发 code review gate。

触发后会先找 active task：

| 情况 | 行为 |
| --- | --- |
| 存在 active task | 使用 task slug、todo path、review path。 |
| 存在多个 todo 但没有 active state | fail closed，报告 `ambiguous_task`。 |
| 没有 todo | 不创建 review request，允许普通无任务代码外场景继续。 |

如果 review 文件缺失，Stop 会创建：

```text
tasks/reviews/<slug>.md
tasks/loops/<slug>/state.json
```

然后阻塞结束，要求完成 review。

### Review 文件放行合约

`tasks/reviews/<slug>.md` 的 frontmatter 是放行事实源，正文 notes 不单独放行。

必须满足：

| 字段 | 要求 |
| --- | --- |
| `status` | `ready`。 |
| `validation` | `pass` 或 `automated-pass`。 |
| `reviewed_diff_hash` 或 `reviewed_file_hashes` | 必须覆盖当前 code diff。 |
| `validation_evidence.required_checks` | 每个 required check 都要记录 `exit_code: 0`。 |
| `reviewer.role` | 普通风险需要 `human`、`independent-agent` 或 `ci`；高风险需要 `human` 或 `ci`。 |
| findings | 不得保留 open critical / warning / blocker。 |
| reviewer / implementer | `reviewer.role: same-agent` 或 `reviewer.id == implementer.id` 会 fail closed。 |

如果 review Ready 后又修改了代码，`reviewed_diff_hash` / `reviewed_file_hashes` 会与当前 diff 不一致，Stop 会继续阻塞并要求重新 review。

### stop_hook_active 特殊情况

如果 host payload 里有：

```json
{"stop_hook_active": true}
```

runtime 不再发起新的 block decision，而是记录或复用当前 blocker，并输出 `decision: allow` 加 `status: blocked`。这是为了避免 Stop hook 自己造成重复递归阻塞，同时仍然告诉 agent 不要声称任务完成。

## Guard 细节

### SecurityGuard

只在 PreToolUse 阶段运行。它拦截高风险命令，不替代用户明确授权后的人工操作。

当前危险模式包括：

| 类别 | 示例 |
| --- | --- |
| 危险递归删除 | `rm -rf /`、`rm -rf ~`、`rm -rf $HOME`、`rm -rf C:\` |
| 破坏性 git | `git reset --hard`、`git checkout --` |
| 强推 | `git push --force` |
| 远程脚本管道 | `curl ... | bash`、`wget ... | sh`、`Invoke-WebRequest ... | iex` |
| 动态执行 | `eval`、`Invoke-Expression`、`iex` |

### SecretPathGuard

保护路径名中的 secret-like 文件：

| 默认保护 | 说明 |
| --- | --- |
| `.env`、`.env.*` | 环境变量文件。 |
| `.npmrc`、`.pypirc` | 包管理凭据文件。 |
| `id_rsa`、`id_dsa`、`id_ed25519` | SSH 私钥。 |
| `credentials`、`credential`、`token`、`secret`、`secrets` | 明确凭据语义路径段。 |
| `private-key` | 私钥路径段。 |

允许后缀：

```text
.example
.sample
.template
.md
```

所以 `.env.example`、secret 文档说明这类文件不会被当作真实 secret 路径直接阻断。

### SecretContentGuard

扫描内容中的 secret-like 模式：

| 模式 | 示例类型 |
| --- | --- |
| `-----BEGIN ... PRIVATE KEY-----` | 私钥。 |
| `sk-...` | OpenAI 风格 key。 |
| `ghp_...` | GitHub PAT。 |
| `AKIA...` | AWS access key id。 |
| `xox...` | Slack token。 |

PreToolUse 命中会直接 deny。PostToolUse 命中说明工具已经写入，hook 会要求清理并进入 `security_required`。

### LineLengthGuard

它统计有效代码行，而不是简单文件行数。空行、注释、generated/vendor/fixture 等路径会被处理或跳过。

当前分组：

| 文件类型 | 类别 |
| --- | --- |
| `.tsx`、`.jsx`、`.vue`、`.svelte` | frontend component |
| `.ts`、`.js` | script module |
| `.py`、`.go`、`.rs`、`.java`、`.cs` | backend module |

PostToolUse 阶段只 warning；Stop 阶段对本次新增或跨过 hard limit 的源码文件 block。已经在 HEAD 中超过 hard limit 的旧文件会记录 warning，review 仍需关注，但不会因为历史债务直接阻塞本次结束。

### MirrorDriftGuard

`.agents/*.md` 是 agent 源模板。修改源模板后，必须同步生成：

```text
.codex/agents/<name>.toml
.claude/agents/<name>.md
```

否则：

| 阶段 | 行为 |
| --- | --- |
| PostToolUse | warn。 |
| Stop | block。 |

修复命令：

```powershell
python .codex\skills\apex-sync-agent-mirrors\scripts\sync_agent_mirrors.py . --target all --write
```

## 状态文件

| 文件 | 写入者 | 用途 |
| --- | --- | --- |
| `tasks/loops/workflow.md` | installer / 用户 | 可编辑 workflow state 文案，按 `[apex-state:<state>]...[/apex-state:<state>]` 匹配。 |
| `tasks/loops/active.json` | 用户 / 编排器 / agent | 多 todo 或多任务时显式声明 active tasks、owned paths、review path、risk level。 |
| `tasks/loops/<slug>/state.json` | Stop / ReviewGate | 记录 review attempts、changed files、hash、last blocker、continuation count。 |
| `tasks/loops/security-required.json` | PostToolUse secret guard | 记录疑似 secret 写入后的清理要求。存在时 workflow 为 `security_required`。 |
| `tasks/loops/session-snapshot.json` | PreCompact | compaction 前保存可恢复上下文。 |
| `tasks/loops/failures.jsonl` | guards | 全局结构化 failure / warning 记录。 |
| `tasks/loops/<slug>/failures.jsonl` | guards | task 级结构化 failure / warning 记录。 |
| `tasks/reviews/<slug>.md` | Stop 创建，reviewer 更新 | review request、scope、review / validation 放行合约。 |
| `tasks/lessons.md` | 用户 / agent | SessionStart 注入最近 lessons。 |

## 典型流程

### 1. 正常实现任务

1. `SessionStart` 注入当前 branch、changed files、active todo 和 review 状态。
2. `UserPromptSubmit` 提示当前 workflow state。
3. agent 编辑文件时，`PreToolUse.safety-write` 先拦截明显危险路径或密钥内容。
4. 编辑完成后，`PostToolUse.edit` 扫描 secret、行数和 mirror drift。
5. agent 准备结束时，`Stop.default` 发现有 code diff 和 active todo，但 review 未 ready。
6. Stop 创建或更新 `tasks/reviews/<slug>.md` 和 `tasks/loops/<slug>/state.json`，然后 block。
7. reviewer 审查并把 review frontmatter 更新为 `status: ready`。
8. agent 运行验证，把 `validation: pass` 和 required checks `exit_code: 0` 写入 review。
9. 再次 Stop 时，如果 diff hash 仍覆盖当前代码，允许结束。

### 2. 修改 agent 模板

1. 修改 `.agents/developer.md`。
2. `PostToolUse.edit` 发现 `.codex/agents/developer.toml` 和 `.claude/agents/developer.md` 没同步，输出 warning。
3. 运行 `sync_agent_mirrors.py` 生成镜像。
4. `Stop.default` 再检查时，mirror drift 消失。

### 3. 工具写入疑似密钥

1. 如果密钥出现在待写入 payload 中，`PreToolUse` 直接 deny，文件不会被写。
2. 如果通过 shell / generator 等方式已经写入，`PostToolUse` 检测到后写 `tasks/loops/security-required.json`。
3. `UserPromptSubmit` 后续会显示 `security_required`。
4. `Stop.default` 会阻塞，直到清理内容并处理真实凭据轮换风险。

## 安装与信任边界

Hook 配置不能只靠文档生效，必须由 `apex-init-project-hooks` 安装到 host 会加载的位置：

| Host | 配置形态 |
| --- | --- |
| Codex | 由 installer 渲染到 Codex hook config；当前支持 JSON 和 Codex TOML managed block。 |
| Claude Code | 合并到 Claude settings hook 配置。 |

安装后仍需要 host 的 trust / review 流程。hook runtime 是本地脚本，不上传代码，不替代 lint、type-check、test、pre-commit 或 CI。它的职责是即时 guardrail 和 workflow 状态反馈。

## 排障速查

| 现象 | 可能原因 | 处理 |
| --- | --- | --- |
| 新会话没有 Apex Loop Context | hook 没装到 host 实际加载的配置，或未 trust。 | 重新 dry-run / install `apex-init-project-hooks`，检查 Codex / Claude 配置和 trust 状态。 |
| 每次 prompt 都出现 `review_required` | 有 code diff，且 active review 未 ready 或 diff hash 过期。 | 查看 `tasks/reviews/<slug>.md`，补 review / validation，或重新审查当前 diff。 |
| Stop 创建 review 后仍阻塞 | 这是预期行为；创建 request 不等于 review 通过。 | 调用 reviewer，更新 frontmatter。 |
| review ready 但 Stop 仍阻塞 | validation 缺失、required checks 没有 `exit_code: 0`、reviewer role 不合规、或代码又改了。 | 按 Stop 输出的 guard reason 修正 review frontmatter。 |
| 修改 `.agents/*.md` 后不能结束 | mirror drift。 | 运行 `sync_agent_mirrors.py . --target all --write`。 |
| PostToolUse 报 line length | 文件超过有效行数提醒线。 | 拆分职责；若跨过 hard limit，Stop 会阻塞。 |
| 出现 `security_required` | PostToolUse 发现疑似 secret 已写入。 | 移除内容，确认是否需要轮换真实凭据，再重新验证。 |
