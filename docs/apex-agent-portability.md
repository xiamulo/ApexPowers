# Apex Agent Portability

ApexPowers 的可移植性目标不是把同一份 hook 配置硬塞给所有宿主，而是把核心能力保持在少数 source of truth 中，再为每个宿主提供最薄的适配层。

## Source Of Truth

| Capability | Source |
| --- | --- |
| Apex skills | `.codex/skills/apex-*` and `.claude/skills/apex-session-init-claude-code` |
| Sub-agent role templates | `.agents/*.md` |
| Codex / Claude agent mirrors | Generated from `.agents/*.md` by `apex-sync-agent-mirrors` |
| Lifecycle hooks | Installed by `apex-init-project-hooks`; route registry lives in `apex_loop_routes.py` |
| Installation health | `apex-doctor` and `scripts/check_apex_distribution.py` |
| Distribution commands | `commands/*.toml` prompt wrappers |

## Host Matrix

| Host | Current Status | Adapter Type | Load Entry | Apex Source | Production Rule |
| --- | --- | --- | --- | --- | --- |
| Codex | Supported | Skills, custom agents, lifecycle hooks, plugin manifest | `.codex/skills/`, `.codex/agents/*.toml`, user `config.toml`, `.codex-plugin/plugin.json` | `.codex/skills`, `.agents`, `apex-init-project-hooks` | Hooks must be installed and trusted through the installer, not declared directly in the plugin manifest. |
| Claude Code | Supported | Skill, subagents, lifecycle hooks, plugin manifest | `.claude/skills/`, `.claude/agents/*.md`, user `settings.json`, `.claude-plugin/plugin.json` | `.claude/skills`, `.agents`, `apex-init-project-hooks` | Claude settings must be merged, not overwritten; user hooks are preserved. |
| OpenCode | Planned | Commands and optional server plugin | `.opencode/command/`, `opencode.json` plugin entry | `commands/`, future adapter | Do not reuse Claude/Codex lifecycle event names without an OpenCode-specific adapter. |
| Gemini / Antigravity CLI | Planned | Instruction and commands | `AGENTS.md`, `commands/*.toml`, extension manifest | Future generated rule mirror and `commands/` | Do not place Claude/Codex hook maps at Gemini auto-discovered hook paths. |
| GitHub Copilot CLI | Planned | Plugin commands and instruction fallback | plugin manifest, `AGENTS.md`, `.github/copilot-instructions.md` | Future generated rule mirror and `commands/` | Command namespace must be explicit; instruction fallback has no hook guarantees. |
| Cursor | Planned | Instruction-only rule | `.cursor/rules/*.mdc` | Future generated rule mirror | No lifecycle assumptions; keep rules short and generated. |
| Windsurf | Planned | Instruction-only rule | `.windsurf/rules/*.md` | Future generated rule mirror | No lifecycle assumptions; generated copy must drift-check against source. |
| Cline | Planned | Instruction-only rule | `.clinerules/*` | Future generated rule mirror | Instruction-only; no commands or hooks. |
| Kiro | Planned | Steering rule | `.kiro/steering/*.md` | Future generated rule mirror | Steering rules must stay compact and generated. |
| CodeWhale | Instruction fallback | Project instructions | `AGENTS.md`, `CLAUDE.md` | Target project rules from `apex-init-project-agent` | Use generated project rules; no Apex-specific runtime expectation. |
| Generic MCP host | Planned | Read-only tool / prompt | future `apex-mcp/` stdio server | Doctor, skill index, workflow state | MCP can expose context on demand but cannot replace always-on lifecycle hooks. |

## Adapter Classes

### Skill-Capable Hosts

Skill-capable hosts should load Apex skills from existing directories. They should not fork the skill text into host-specific copies unless a generator and drift test exist.

### Command-Capable Hosts

Command-capable hosts should load `commands/*.toml`. These files are prompt wrappers around existing skills and scripts; they must not become a second implementation of Apex behavior.

### Lifecycle-Hook Hosts

Lifecycle hooks are high-risk because they can block tools or session completion. ApexPowers only supports them through `apex-init-project-hooks`, which provides dry-run, manifest ownership, update, uninstall, and user hook preservation.

### Instruction-Only Hosts

Instruction-only hosts can receive generated rule files later. Those files must be short, generated, and tested for drift. They are advisory only and must not be documented as equivalent to loop hooks.

## Production Gates

- Every new adapter gets a smoke test before it is documented as supported.
- Every generated rule copy gets a drift check.
- Every plugin manifest must use pinned semver and valid JSON.
- Plugin manifests stay thin: no direct lifecycle hook declaration unless the installer ownership model supports that host.
- Unsupported hosts are documented as planned or instruction-only, not silently implied by copied files.
