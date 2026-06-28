---
name: apex-init-project-hooks
description: 为已有项目安装 ApexPowers loop hooks。默认把 hook 配置和 runtime 写入 Codex / Claude Code agent 根目录，把任务状态写入项目目录。
---

# Apex Init Project Hooks

## 工作流

运行 `scripts/init_project_hooks.py <project-root>`。默认只预览；确认范围合理后，传入 `--write` 写入 hook 配置、runtime 脚本和任务状态目录。

Hook 配置和 runtime 默认安装到对应 agent 根目录：Codex 使用 `CODEX_HOME` 或 `~/.codex`，Claude Code 使用 `CLAUDE_HOME` 或 `~/.claude`。项目目录只保留 `tasks/loops/`、`tasks/reviews/`、`tasks/lessons.md` 等 loop 状态。

只做确定性 loop 门禁：危险命令 / secrets、写入后行数检查、`.agents` 镜像漂移提醒、Stop review gate、SessionStart 状态摘要。不要在 hook 脚本里递归启动 Codex 或 Claude Code。

## 生成目标

- Codex agent root：`<codex-home>/config.toml` 中的 Apex 托管 `[[hooks.*]]` 块，与 `<codex-home>/hooks/apex_loop.py`
- Claude Code agent root：`<claude-home>/settings.json` 与 `<claude-home>/hooks/apex_loop.py`
- 项目目录：`tasks/loops/`、`tasks/loops/workflow.md`、`tasks/reviews/`、`tasks/lessons.md`
- Ownership manifest：`tasks/loops/.apex-manifest.json`、`<codex-home>/apex/manifest.json`、`<claude-home>/apex/manifest.json`

## 常用命令

```powershell
$CodexHome = "$env:USERPROFILE\.codex"
$ClaudeHome = "$env:USERPROFILE\.claude"
py -3 .codex\skills\apex-init-project-hooks\scripts\init_project_hooks.py .
py -3 .codex\skills\apex-init-project-hooks\scripts\init_project_hooks.py . --codex-home "$CodexHome" --claude-home "$ClaudeHome" --write
py -3 .codex\skills\apex-init-project-hooks\scripts\init_project_hooks.py . --codex-home "$CodexHome" --claude-home "$ClaudeHome" --write --force
py -3 .codex\skills\apex-init-project-hooks\scripts\init_project_hooks.py . --codex-home "$CodexHome" --claude-home "$ClaudeHome" --update
py -3 .codex\skills\apex-init-project-hooks\scripts\init_project_hooks.py . --codex-home "$CodexHome" --claude-home "$ClaudeHome" --uninstall
py -3 .codex\skills\apex-init-project-hooks\scripts\init_project_hooks.py . --codex-home "$CodexHome" --claude-home "$ClaudeHome" --uninstall --write
py -3 .codex\skills\apex-init-project-hooks\scripts\init_project_hooks.py . --hook-scope project --write
py -3 .codex\skills\apex-init-project-hooks\scripts\init_project_hooks.py . --codex-home "$CodexHome" --claude-home "$ClaudeHome" --codex-config-format json --write
py -3 .codex\skills\apex-init-project-hooks\scripts\apex_loop.py render-config codex --script-path "$CodexHome/hooks/apex_loop.py" --config-format toml
```

## 覆盖规则

- 不存在的文件会创建。
- 已有 `<codex-home>/config.toml` 会保留用户配置，只替换 Apex 托管块；非法 TOML 默认跳过，避免破坏用户文件。
- 已有 `<claude-home>/settings.json` 会做 JSON 合并：保留用户已有 hook，只替换 Apex 管理的 `apex_loop.py` 条目。
- 只有显式 `--codex-config-format json` 或旧项目级布局才写 Codex `hooks.json`。
- 已由 ApexPowers 生成且含有生成标记的 runtime 文件会自动覆盖。
- 没有生成标记的既有 hook 脚本默认跳过。
- 既有 JSON hook 配置不是合法 JSON 时默认跳过，避免破坏用户文件。
- `tasks/loops/workflow.md` 与 `tasks/lessons.md` 是用户可编辑状态文件；默认只创建，不覆盖已修改内容，卸载时保留。
- Manifest hash 使用 LF 归一化，Windows / Unix 换行差异不会误判为用户修改。
- 用户明确要求“重新生成 / 覆盖 / 刷新 / regenerate”时，使用 `--force` 或 `--regenerate`。
- 只有明确需要旧的项目级 hook 布局时，才使用 `--hook-scope project`。

## 重复安装与迁移

- 已经安装过 agent-root hooks 时，再次运行 `--write` 会先移除已有 Apex 管理的 `apex_loop.py` 条目，再写入新条目，不会重复追加。
- 已经安装过旧项目级 hooks 时，默认 agent-root 安装会清理项目 `.codex/hooks.json`、`.codex/config.toml`、`.claude/settings.json` 中的 Apex 条目，并删除带生成标记的项目级 runtime 副本。
- 如果旧项目级 host 配置里有用户自己的 hook，会保留用户 hook，只移除 Apex 管理的 legacy 条目。
- 没有生成标记的项目级 runtime 文件不会删除。
- `--update` 是 manifest-aware reinstall；默认 dry run，带 `--write` 才落盘。
- `--uninstall` 只处理 manifest 记录的 Apex-managed 文件；Codex TOML 使用托管块 scrubber，Claude Code JSON 使用 structured scrubber，runtime 文件必须 hash 匹配、带生成标记或使用 `--force` 才删除。

## Workflow-state

- Installer 会创建 `tasks/loops/workflow.md`，使用 `[apex-state:*]...[/apex-state:*]` 状态块。
- Runtime 当前支持 `no_task`、`planning`、`implementing`、`security_required`、`review_required`、`validation_required`、`done`。
- `SessionStart` 会注入当前 workflow state 摘要；`UserPromptSubmit` 会输出完整 `<apex-workflow-state>` block。
- 如果 `workflow.md` 缺失或状态块缺失，runtime 使用显式 fallback，不会静默失败。

## 运行时边界

- `UserPromptSubmit` 只输出 workflow-state 和 advisory route hint，不硬阻塞。
- `PreToolUse`、`PostToolUse`、`Stop` 才能在确定性证据足够时介入；PostToolUse 不能撤销已完成工具，只能反馈并标记后续清理要求。
- 每个 block / strong warning 都必须包含 `guard`、`reason`、`fix`、`failure_class`、`run_id`，并写入已忽略的 failure JSONL。
- PostToolUse 发现 secret-like 内容时写入 `tasks/loops/security-required.json`；Stop 会在该状态清理前阻塞完成。
- Stop review gate 读取 `tasks/reviews/<slug>.md` 的结构化 frontmatter；新 review request 使用 YAML，旧 TOML frontmatter 兼容读取。放行要求 `status: ready`、`validation: pass` 或 `automated-pass`、`reviewed_diff_hash` 覆盖当前 diff、`required_checks.exit_code = 0`，且 reviewer role / id 满足风险级别。
- `stop_hook_active=true` 时不递归创建 review request；state.json 记录 `last_block_reason_hash`、`block_count_for_same_reason`、`continuation_count`、`max_continuations`、`created_review_request`，相同 Stop blocker 会允许本轮以 blocked / follow-up-required 状态结束，而不是继续空转。
- `PostToolUse` 使用 diff-aware 路径、guard file-hash cache 和 failure dedupe；支持 `PostToolBatch/default` 复用同一检查逻辑，降低并发/批量工具调用时的重复扫描和重复 failures。

## 验证

修改脚本后至少运行：

```powershell
py -3 -m py_compile .codex\skills\apex-init-project-hooks\scripts\init_project_hooks.py .codex\skills\apex-init-project-hooks\scripts\apex_loop.py .codex\skills\apex-init-project-hooks\scripts\apex_loop_core.py .codex\skills\apex-init-project-hooks\scripts\apex_loop_routes.py .codex\skills\apex-init-project-hooks\scripts\apex_loop_runtime.py .codex\skills\apex-init-project-hooks\scripts\apex_loop_utils.py
py -3 -m unittest tests.test_apex_loop_hooks tests.test_apex_loop_installer
py -3 .codex\skills\apex-init-project-hooks\scripts\init_project_hooks.py . --json
```
