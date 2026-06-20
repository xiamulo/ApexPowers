# ECC hook 对比与 ApexPowers 修改方案

## 结论

ECC 的 hook 不是因为脚本本身更特殊才会生效，而是因为它把入口放到了宿主会加载的位置：

- Claude Code: 通过插件约定加载 `hooks/hooks.json`，或者安装器写到 `~/.claude/hooks/hooks.json`。
- Cursor: 项目内有 `.cursor/hooks.json`，命令直接指向 `.cursor/hooks/*.js`。
- OpenCode: `.opencode/opencode.json` 加载 `./plugins`，插件注册 `file.edited`、`tool.execute.before/after`、`session.created/idle` 等事件。
- Codex: ECC 没有 Codex agent lifecycle hook，主要是 MCP/agent/config 指令和可选 Git hooks。

ApexPowers 原先不生效的主要原因是：本机没有安装 Apex runtime 到实际宿主配置里，并且 ApexPowers 的 Codex 安装目标仍是 `~/.codex/hooks.json`，但本机当前 Codex hook 配置实际在 `~/.codex/config.toml` 的 `[[hooks.*]]` 段里。换句话说，ApexPowers 当时“有 runtime 和 installer”，但还没有把 runtime 接到当前 Codex/Claude 会执行的配置入口。

本仓库现已按本文 P0 的方向调整：默认 agent-root 安装会把 Codex hook 写入 `<codex-home>/config.toml` 的 Apex 托管 TOML block，把 Claude Code hook 合并到 `<claude-home>/settings.json`，并保留 `--codex-config-format json` 作为旧 Codex 兼容路径。

## 本次核查范围

- 已克隆 ECC 到 `D:\gitdown\ECC`。
- 已索引并检查 `D:\gitdown\ApexPowers` 与 `D:\gitdown\ECC`。
- 已检查本机当前用户级配置：
  - `C:\Users\gin_n\.codex\config.toml`
  - `C:\Users\gin_n\.codex\hooks.json`
  - `C:\Users\gin_n\.claude\settings.json`
  - `C:\Users\gin_n\.codex\hooks\apex_loop.py`
  - `C:\Users\gin_n\.claude\hooks\apex_loop.py`
- 未修改全局 Codex/Claude 配置，未安装 hook。

## ECC hook 为什么能生效

### Claude Code

ECC 的主 hook 图谱在 `D:\gitdown\ECC\hooks\hooks.json`，覆盖 `PreToolUse`、`PreCompact`、`SessionStart`、`PostToolUse`、`PostToolUseFailure`、`Stop`、`SessionEnd`。

它的关键不是单个 hook 脚本，而是完整加载链：

1. Claude 插件安装后，宿主按插件约定发现 `hooks/hooks.json`。
2. hook 命令先解析 `CLAUDE_PLUGIN_ROOT` 或 `~/.claude/plugins/...`。
3. `scripts/hooks/plugin-hook-bootstrap.js` 找到真实插件根目录。
4. `scripts/hooks/run-with-flags.js` 根据 `ECC_HOOK_PROFILE`、`ECC_DISABLED_HOOKS` 决定是否执行具体脚本。
5. 阻塞类 hook 用 exit code `2` 向宿主反馈。

这条链路的强点是：配置入口、runtime、profile gate、错误反馈都在同一个安装面里。

### Cursor

ECC 直接提供 `.cursor/hooks.json`，例如：

- `sessionStart` -> `node .cursor/hooks/session-start.js`
- `beforeShellExecution` -> `node .cursor/hooks/before-shell-execution*.js`
- `afterFileEdit` -> `node .cursor/hooks/after-file-edit.js`
- `stop` -> `node .cursor/hooks/stop.js`

`.cursor/hooks/adapter.js` 会把 Cursor 的 stdin 转成 Claude 风格输入，再复用 `scripts/hooks/*.js`。这能生效的原因是 Cursor 会识别 `.cursor/hooks.json` 这个项目级入口。

### OpenCode

ECC 的 OpenCode 入口是 `.opencode/opencode.json`：

```json
"plugin": ["./plugins"]
```

`.opencode/plugins/ecc-hooks.ts` 导出 `ECCHooksPlugin`，不是通过 JSON 命令执行，而是直接注册 OpenCode 事件：

- `file.edited`
- `tool.execute.before`
- `tool.execute.after`
- `session.created`
- `session.idle`
- `session.deleted`
- `shell.env`
- `permission.ask`

这能生效的原因是 OpenCode 插件系统会加载 `./plugins` 并调用导出的事件处理器。

### Codex

ECC 仓库自身的 `.codex/AGENTS.md` 明确把 Codex 的安全约束定义为 instruction-based，并写到 “Hooks: Not yet supported”。ECC 的 Codex 侧主要做：

- `.codex/config.toml` 的 MCP / features / agents 基线。
- `scripts/codex/install-global-git-hooks.sh` 安装 Git `pre-commit` / `pre-push`。

因此，ECC 的 Codex “hook”不能直接类比 ApexPowers 的 Codex lifecycle hook。更准确地说，ECC 在 Codex 上主要靠说明、MCP、agent 配置和 Git hooks，而不是 Codex agent 事件 hook。

## ApexPowers 原始 hook 是怎么做的

ApexPowers 的 hook 实现在：

- `.codex/skills/apex-init-project-hooks/SKILL.md`
- `.codex/skills/apex-init-project-hooks/scripts/init_project_hooks.py`
- `.codex/skills/apex-init-project-hooks/scripts/apex_loop.py`
- `.codex/skills/apex-init-project-hooks/scripts/apex_loop_core.py`
- `.codex/skills/apex-init-project-hooks/scripts/apex_loop_routes.py`
- `.codex/skills/apex-init-project-hooks/scripts/apex_loop_runtime.py`
- `.codex/skills/apex-init-project-hooks/scripts/apex_loop_utils.py`

当前 route registry 渲染这些事件：

| 事件 | route | 作用 |
| --- | --- | --- |
| `SessionStart` | `default` | 注入 workflow state、todo、review、lessons 摘要 |
| `UserPromptSubmit` | `default` | 输出 `<apex-workflow-state>` 和路由提示，只 advisory |
| `PreToolUse` | `safety` | 阻塞危险命令、破坏性 git、secret 路径 |
| `PostToolUse` | `edit` | 检查写入文件、secrets、行数、agent 镜像漂移 |
| `PostToolUse` | `bash` | 基于 shell 后变更做后置检查 |
| `PostToolUse` | `always` | 通用后置检查 |
| `Stop` | `default` | review gate、validation gate、镜像同步 gate |

整改前，安装器默认 `--hook-scope agent`，计划写入：

- `C:\Users\gin_n\.codex\hooks.json`
- `C:\Users\gin_n\.codex\hooks\apex_loop*.py`
- `C:\Users\gin_n\.claude\settings.json`
- `C:\Users\gin_n\.claude\hooks\apex_loop*.py`
- `D:\gitdown\ApexPowers\tasks\loops\workflow.md`
- `D:\gitdown\ApexPowers\tasks\loops\.apex-manifest.json`
- `C:\Users\gin_n\.codex\apex\manifest.json`
- `C:\Users\gin_n\.claude\apex\manifest.json`

## 关键差异

| 维度 | ECC | ApexPowers 整改前 |
| --- | --- | --- |
| 宿主入口 | Claude/Cursor/OpenCode 都有各自会被加载的入口 | 有 installer/runtime，但本机未安装到实际入口 |
| Codex 侧 | 主要是 instruction/MCP/Git hooks | 试图生成 Codex lifecycle hook |
| 本机 Codex 配置 | 不适用 ECC lifecycle hook | 当前真实配置在 `~/.codex/config.toml`，不是 `~/.codex/hooks.json` |
| Runtime 依赖 | Node 为主，另有 Bash/Python/PowerShell/Git | Python + Git 为主 |
| Windows 风险 | 依赖面宽，已有很多兼容补丁 | 更窄，但写死 `python` 命令名 |
| 安装证据 | 需要插件/installer 后才真正启用 | 本机缺 `apex_loop.py`、manifest、Codex trust 记录 |

## ApexPowers 为什么不能生效

### 1. 本机没有安装 Apex hook runtime

诊断时缺失：

- `C:\Users\gin_n\.codex\hooks.json`
- `C:\Users\gin_n\.codex\hooks\apex_loop.py`
- `C:\Users\gin_n\.codex\apex\manifest.json`
- `C:\Users\gin_n\.claude\hooks\apex_loop.py`
- `C:\Users\gin_n\.claude\apex\manifest.json`
- `D:\gitdown\ApexPowers\.codex\hooks.json`
- `D:\gitdown\ApexPowers\.claude\settings.json`

`C:\Users\gin_n\.claude\settings.json` 存在，但里面只有 `cbm-*` hook，没有 Apex `apex_loop.py`。

### 2. Codex 目标文件和本机真实加载方式不一致

整改前，ApexPowers installer 计划创建 `C:\Users\gin_n\.codex\hooks.json`。但本机当前 Codex 的已启用 hook 写在：

```text
C:\Users\gin_n\.codex\config.toml
[[hooks.SessionStart]]
[[hooks.UserPromptSubmit]]
[[hooks.PermissionRequest]]
[[hooks.PostToolUse]]
[[hooks.Stop]]
[[hooks.SubagentStop]]
```

并且已有 `hooks.state` 信任记录也在 `config.toml`。如果当前 Codex 不自动读取 `~/.codex/hooks.json`，ApexPowers 即使写出 `hooks.json` 也不会触发。

### 3. 缺少 Codex trust

README 已说明安装后需要在 Codex 的 `/hooks` 或设置界面 review / trust。当前 `hooks.state` 里只有已有 hook 的信任记录，没有 Apex `apex_loop.py` 的记录。

### 4. `python` 命令名有 Windows 风险

当前渲染命令类似：

```text
python "C:/Users/gin_n/.codex/hooks/apex_loop.py" stop --host codex --route default
```

本机 `where python` 能找到多个 Python，但这仍然有风险：

- 可能落到非预期环境。
- 可能被 WindowsApps alias 截获。
- 不同 host 启动环境的 PATH 可能不同。

### 5. 状态文件尚未初始化

`tasks/loops/workflow.md` 和 `.apex-manifest.json` 当前未创建。runtime 即使被手动触发，也会走 fallback workflow state，缺少 manifest-aware update/uninstall 的所有权依据。

## 修改方案

### P0: 修正 Codex 安装目标

目标：让 ApexPowers 写入当前 Codex 真正加载的配置位置。

建议改法：

1. 保留现有 `hooks.json` 渲染能力，但不要把它作为 Windows/Codex 默认唯一目标。
2. 在 `init_project_hooks.py` 增加 Codex TOML 合并能力：
   - 读取 `~/.codex/config.toml`。
   - 在带有 Apex 管理标记的 block 内写入 `[[hooks.*]]`。
   - 不改用户已有 hook。
   - 重复安装时先移除旧 Apex block，再写入新 block。
   - `--uninstall` 只移除 Apex block。
3. Codex host config 默认从 `hooks.json` 改成 `config.toml` inline hooks，并增加参数：
   - `--codex-config-format toml`
   - `--codex-config-format json`
   - 默认 `auto` 在 agent-root 安装时用 TOML，在旧项目级布局时继续用 JSON。

推荐写入形态：

```toml
# >>> apex-managed-hooks-begin (Generated by ApexPowers apex-init-project-hooks) >>>
[[hooks.SessionStart]]
[[hooks.SessionStart.hooks]]
type = "command"
command = "python \"C:/Users/gin_n/.codex/hooks/apex_loop.py\" session-start --host codex --route default"
timeout = 30

[[hooks.UserPromptSubmit]]
[[hooks.UserPromptSubmit.hooks]]
type = "command"
command = "python \"C:/Users/gin_n/.codex/hooks/apex_loop.py\" user-prompt-submit --host codex --route default"
timeout = 30

[[hooks.PreToolUse]]
matcher = "Bash|Shell|PowerShell|Edit|Write|MultiEdit|apply_patch"
[[hooks.PreToolUse.hooks]]
type = "command"
command = "python \"C:/Users/gin_n/.codex/hooks/apex_loop.py\" pre-tool-use --host codex --route safety"
timeout = 30

[[hooks.PostToolUse]]
matcher = "Edit|Write|MultiEdit|apply_patch"
[[hooks.PostToolUse.hooks]]
type = "command"
command = "python \"C:/Users/gin_n/.codex/hooks/apex_loop.py\" post-tool-use --host codex --route edit"
timeout = 30

[[hooks.Stop]]
[[hooks.Stop.hooks]]
type = "command"
command = "python \"C:/Users/gin_n/.codex/hooks/apex_loop.py\" stop --host codex --route default"
timeout = 30
# <<< apex-managed-hooks-end <<<
```

注意：`PermissionRequest`、`SubagentStop` 是否接入要单独设计，不要照搬已有 Nezha hook。

### P1: 安装 runtime 后建立 trust 流程

目标：安装后能被当前 Codex/Claude 接受，而不是只写文件。

当前状态：README 与 skill 文档已明确 Codex 安装后需要 `/hooks` 或设置界面 review / trust；安装器 JSON 输出已包含 `codex_config_format`。自动写入 Codex `hooks.state.trusted_hash` 尚未实现，也不建议在没有确认 Codex hash 规则和用户授权语义前绕过 review。

建议：

1. installer `--write` 后输出明确的后续动作：
   - Codex: 打开 `/hooks` 或设置界面 trust Apex hooks。
   - Claude: 确认 `~/.claude/settings.json` 已加载，重启会话。
2. dry-run 输出必须显示：
   - 将写入 `config.toml` 还是 `hooks.json`。
   - 是否发现已有 Apex block。
   - 是否发现 trust state。
3. README 和 SKILL.md 更新为当前 Codex TOML 事实，不再只写 `$CodexHome\hooks.json`。

### P2: 固定 Python 解释器

目标：降低 Windows PATH 差异导致的静默失败。

建议：

1. 安装时记录当前 `sys.executable`。
2. 渲染命令默认使用绝对 Python 路径：

```text
"C:/ProgramData/anaconda3/python.exe" "C:/Users/gin_n/.codex/hooks/apex_loop.py" ...
```

3. 增加参数允许覆盖：
   - `--python-exe <path>`
   - `--python-launcher py`
4. dry-run 检测 Python 可用性：
   - `python --version`
   - 绝对路径是否存在
   - hook 进程是否能 import runtime sibling modules

### P3: 明确 host-specific adapter

目标：学习 ECC 的正确部分，不照搬复杂度。

建议保留 ApexPowers “窄 runtime” 设计，但把 host adapter 分清：

- `CodexTomlRenderer`
- `CodexJsonRenderer`，仅作为兼容路径
- `ClaudeSettingsRenderer`
- 后续如果支持 Cursor/OpenCode，再新增独立 adapter，不塞到同一份 JSON 模板里。

这样能获得 ECC 的核心优点：每个宿主都有自己能识别的入口；同时避免复制 ECC 过宽的 Node/Bash/Python/PowerShell 混合链路。

## 建议执行顺序

1. 先只改 installer，不改 runtime guard 逻辑。
2. 加 TOML block 合并与 scrub 测试：
   - 保留用户已有 `[[hooks.*]]`。
   - 重复安装不重复追加。
   - uninstall 只删除 Apex managed block。
   - 非法 TOML 时 fail closed，不破坏配置。
3. 改 route renderer 支持 `toml` 输出。
4. 改 README / SKILL.md 安装说明。
5. 运行：

```powershell
python -m py_compile .codex\skills\apex-init-project-hooks\scripts\init_project_hooks.py .codex\skills\apex-init-project-hooks\scripts\apex_loop.py .codex\skills\apex-init-project-hooks\scripts\apex_loop_core.py .codex\skills\apex-init-project-hooks\scripts\apex_loop_routes.py .codex\skills\apex-init-project-hooks\scripts\apex_loop_runtime.py .codex\skills\apex-init-project-hooks\scripts\apex_loop_utils.py
python -m unittest tests.test_apex_loop_hooks tests.test_apex_loop_installer
python .codex\skills\apex-init-project-hooks\scripts\init_project_hooks.py . --json
```

6. 最后再对当前机器做一次真实 dry-run：

```powershell
$CodexHome = "$env:USERPROFILE\.codex"
$ClaudeHome = "$env:USERPROFILE\.claude"
python .codex\skills\apex-init-project-hooks\scripts\init_project_hooks.py . --codex-home "$CodexHome" --claude-home "$ClaudeHome" --json
```

## 验收标准

- `--json` dry-run 能显示 Codex 将写入 `config.toml` managed block。
- `--write` 后出现：
  - `C:\Users\gin_n\.codex\hooks\apex_loop.py`
  - `C:\Users\gin_n\.codex\config.toml` Apex managed hooks block
  - `C:\Users\gin_n\.claude\hooks\apex_loop.py`
  - `C:\Users\gin_n\.claude\settings.json` Apex hook entries
  - `tasks/loops/workflow.md`
  - 三份 manifest
- 重复安装不重复追加 hook。
- uninstall 能保留用户 hook，只移除 Apex managed block 和 hash 匹配 runtime。
- Codex `/hooks` trust 后，新会话能触发 `SessionStart`。
- 执行危险命令模拟时，`PreToolUse.safety` 能返回阻塞。
- 修改 `.agents/*.md` 但不同步镜像时，`Stop.default` 能阻塞或强提醒。

## 不建议做的事

- 不要直接复制 ECC 的 `hooks/hooks.json` 到 ApexPowers。ECC 的 hook 面过宽，且许多逻辑依赖 Node/Bash/plugin root。
- 不要在 hook 里递归启动 Codex/Claude agent。ApexPowers 现有边界是正确的：hook 只做确定性门禁和状态反馈。
- 不要默认修改用户已有 hook 或整个 `config.toml`。必须用 managed block，且支持 dry-run。
- 不要把 Git hooks 和 Codex lifecycle hooks 混为一谈。ECC 的 Codex 侧 Git hooks 可以借鉴，但不能解释 Apex agent hook 不触发的问题。
