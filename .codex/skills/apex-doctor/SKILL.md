---
name: apex-doctor
description: 检查 ApexPowers skills、agent mirrors、loop hooks、manifest 和 workflow state 的安装健康状态。适用于安装后验收、排查 hooks/镜像漂移、或提交前确认 ApexPowers 分发完整性。
---

# Apex Doctor

## 工作流

运行 `scripts/apex_doctor.py <project-root>`。这个脚本只读检查，不写入任何文件。

默认检查目标项目中的 ApexPowers 安装状态：核心 skills、`.agents` 源模板、Codex / Claude Code agent mirrors、loop hook manifest、host config、runtime 脚本和 workflow state。

ApexPowers checkout 自身的分发一致性检查由 `scripts/check_apex_distribution.py` 负责。不要把它默认塞进 doctor：doctor 面向安装后的目标项目，而 distribution check 面向 ApexPowers 仓库维护。

## 常用命令

```powershell
$CodexHome = "$env:USERPROFILE\.codex"
$ClaudeHome = "$env:USERPROFILE\.claude"
python .codex\skills\apex-doctor\scripts\apex_doctor.py .
python .codex\skills\apex-doctor\scripts\apex_doctor.py . --codex-home "$CodexHome" --claude-home "$ClaudeHome" --json
```

维护 ApexPowers 仓库本身时再单独运行：

```powershell
python scripts\check_apex_distribution.py --json
```

## 状态语义

- `pass`：检查项健康。
- `warn`：可修复或未安装状态，例如 hooks 尚未安装、agent mirrors 未同步。
- `fail`：结构损坏或不一致，例如核心 skill 缺失、manifest 非法、manifest 显示已安装但 runtime/config 缺失。

脚本在存在 `fail` 时返回退出码 1；只有 `pass` / `warn` 时返回退出码 0。

## 修复原则

- 缺少核心 skill：从 ApexPowers 重新复制 `.codex/skills`。
- agent mirror 漂移：运行 `apex-sync-agent-mirrors`。
- hook manifest/config/runtime 不一致：运行 `apex-init-project-hooks --update --write`。
- workflow state 缺失：运行 `apex-init-project-hooks --write` 或手动恢复 `tasks/loops/workflow.md`。

## 禁止事项

- 不要让 doctor 自动修复、覆盖或删除文件。
- 不要读取 `.env`、token、SSH key 或任何 secrets。
- 不要把 warn 包装成完成失败；warn 是需要关注但不阻断的健康信号。
