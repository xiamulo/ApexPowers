# Task: Ponytail Patterns Into ApexPowers Production Integration

## Purpose

把 `D:\gitdown\ponytail` 中值得借鉴的工程做法吸收到 ApexPowers，但不把 Ponytail 整包 vendored 进来。目标是生产可用的 ApexPowers 分发层，而不是概念验证。

本计划覆盖 8 个交付方向：

1. 跨宿主适配矩阵
2. 薄 plugin manifest
3. 反过度工程 skill
4. 平台原生能力清单
5. 规则 / 适配器漂移测试
6. benchmark 方法，不复用 benchmark 结论
7. supply-chain / trust / security 文档与 sha256 manifest
8. worktree / issue / PR 级并行交付 orchestration command

## Current Evidence

- `D:\gitdown\ponytail` 已同步到 `main` 最新提交 `0403c4d`。
- Ponytail 的核心价值是 `skills/` 中的行为规则、`docs/agent-portability.md` 的薄适配器原则、`docs/platform-native.md` 的平台能力清单、adapter smoke tests 和 agentic benchmark 方法。
- ApexPowers 当前核心是私有 Codex / Claude Code skill 包、`.agents` 源模板、Codex / Claude 镜像、manifest-managed loop hooks 和 doctor 检查。
- ApexPowers 当前 worktree 已有未提交 hook / doctor / README 改动；本计划优先新增独立文件，避免覆盖并行工作。

## Non-Goals

- 不复制 Ponytail 品牌、logo、README 营销文案或 benchmark 数字。
- 不把 Ponytail 的 Node hook runtime 直接接入 ApexPowers。
- 不让 plugin manifest 绕过 `apex-init-project-hooks` 的 manifest ownership、update 和 uninstall 边界。
- 不声称 ApexPowers 可以得到 Ponytail 的代码行数、token 或成本收益。
- 不把反过度工程模式设为 always-on；它必须是可显式调用的审查 skill。

## Architecture

### Source Of Truth

- Apex 自有 skills 仍在 `.codex/skills/apex-*`。
- Claude Code 专属 skill 仍在 `.claude/skills/`。
- 子智能体源仍是 `.agents/*.md`，镜像仍由 `apex-sync-agent-mirrors` 生成。
- Hook runtime 仍由 `apex-init-project-hooks` 安装；plugin manifest 只声明可安装能力，不直接声明 hook config。
- 分发一致性由 `scripts/check_apex_distribution.py` 检查。
- 性能 / 稳定性方法由 `benchmarks/apex_distribution_benchmark.py` 提供，只测 Apex 自己的离线路径。

### Host Adapter Rule

每个宿主只做薄适配：

- 能加载 skills 的宿主：指向现有 skill 目录。
- 能加载 commands 的宿主：指向 `commands/` 中的 prompt wrappers。
- 能加载 hooks 的宿主：必须走 `apex-init-project-hooks`，不由 plugin manifest 直接安装隐式 hook。
- 只能加载规则文件的宿主：后续由单独的 rule mirror 生成，不手写复制多个规则副本。

## Deliverables

### D1: Cross-Host Portability Matrix

Artifact:

- `docs/apex-agent-portability.md`

Requirements:

- 列出 Codex、Claude Code、OpenCode、Gemini / Antigravity、GitHub Copilot CLI、Cursor、Windsurf、Cline、Kiro、CodeWhale、generic MCP hosts。
- 每个宿主必须明确：当前支持级别、加载入口、Apex source of truth、安装方式、风险、下一步生产化要求。
- 必须区分 instruction-only、skill-capable、command-capable、lifecycle-hook-capable。

Acceptance:

- `scripts/check_apex_distribution.py` 能确认该文档存在并包含所有关键宿主。

### D2: Thin Plugin Manifests

Artifacts:

- `.codex-plugin/plugin.json`
- `.claude-plugin/plugin.json`

Requirements:

- manifest 只声明 skills / commands / interface metadata。
- 不直接声明 hooks，避免绕开现有 installer 和 trust 流程。
- version 必须是 pinned semver。
- Codex manifest 指向 `./.codex/skills/`。
- Claude manifest 指向 `./.claude/skills/` 和 `./commands/`。

Acceptance:

- 漂移检查确认两个 manifest 都是合法 JSON、name 为 `apexpowers`、version 为 semver、没有 `hooks` 字段。

### D3: Anti-Overengineering Skill

Artifact:

- `.codex/skills/apex-lean-review/SKILL.md`

Requirements:

- 作为显式调用 skill，不改变全局行为模式。
- 只审查 over-engineering，不替代 correctness/security review。
- 输出必须给出可删除项、stdlib/native 替代、保留条件和风险。
- 必须强调不能删除安全、信任边界输入校验、数据防丢失、accessibility 和用户明确要求。
- 必须引用平台原生能力清单。

Acceptance:

- 漂移检查确认 skill 存在并包含 safety carve-outs、native/platform 和 Apex 命名。

### D4: Platform-Native Capability List

Artifact:

- `docs/platform-native-solutions.md`

Requirements:

- 覆盖 HTML / CSS / Browser APIs / Node.js stdlib / Python stdlib / database capabilities。
- 目的不是“少写代码”宣传，而是给 reviewer 判断依赖和抽象是否必要的证据清单。
- 每条必须写“优先考虑”而不是“永远使用”，并标出何时库仍然合理。

Acceptance:

- 漂移检查确认文档存在并包含六个能力区域。

### D5: Drift Tests

Artifacts:

- `scripts/check_apex_distribution.py`
- `tests/test_apex_distribution.py`

Requirements:

- 检查新增分发文件是否存在。
- 检查 plugin manifests 是否合法、薄、路径指向存在目录。
- 检查 command TOML 是否包含 `description` 和 `prompt`。
- 检查 docs / skill 是否包含关键 invariants。
- JSON 输出可被 CI 或 doctor 后续复用。

Acceptance:

- `python scripts/check_apex_distribution.py --json` 返回 0。
- `python -m unittest tests.test_apex_distribution` 返回 0。

### D6: Benchmark Method

Artifacts:

- `benchmarks/README.md`
- `benchmarks/apex_distribution_benchmark.py`

Requirements:

- 只做离线 benchmark，不调用付费模型或外部 API。
- 测量当前 Apex 自己的关键路径：distribution check、doctor、installer dry-run、route config render。
- 输出原始耗时和中位数，不输出“节省百分比”。
- 明确禁止把 Ponytail benchmark 数字搬到 ApexPowers。

Acceptance:

- `python benchmarks/apex_distribution_benchmark.py --runs 1 --json` 返回 0，并输出每个 cell 的 elapsed_ms。

### D7: Supply-Chain / Trust / Security Documentation

Artifacts:

- `docs/supply-chain-trust-security.md`
- `docs/supply-chain-manifest.sha256`
- `NOTICE.md`

Requirements:

- 记录 vendored skills 来源、版本证据、license 和 NOTICE 处理方式。
- 写出每个 hook command 的威胁模型和缓解措施。
- 为 trust-critical plugin manifest、commands、hook installer/runtime 和供应链文档维护 SHA-256 manifest。
- 明确生成文件 marker、manifest provenance、update/uninstall 的破坏性测试边界。
- 明确 telemetry policy：默认无遥测。
- 明确 secret/path guard false-positive 测试要求。
- 继续保持 plugin manifest 不偷偷安装 hooks；未来 plugin-bundled hooks 也必须 opt-in 并走 review / trust flow。

Acceptance:

- `python scripts\check_apex_distribution.py --json` 覆盖 supply-chain 文档、NOTICE 和 SHA-256 manifest。
- `python -m unittest tests.test_apex_distribution tests.test_apex_loop_installer tests.test_apex_loop_hooks` 返回 0。

### D8: Parallel Delivery Orchestration Command

Artifacts:

- `commands/apex-orchestrate-delivery.toml`
- `docs/apex-parallel-delivery-orchestration.md`

Requirements:

- 显式说明 worktree / issue / PR 三个交付层级。
- 串起 6 个角色模板：planner、researcher、implementer、developer、code-reviewer、perf-optimizer。
- 要求检查官方 agent mirrors：`.codex/agents/*.toml` 和 `.claude/agents/*.md`。
- 对 PRD / spec / plan 输入，先走 `apex-to-issues` vertical-slice issue 拆分。
- 维护 orchestration ledger，记录 slice、依赖、owner role、worktree/branch、文件范围、验证命令和 review gate。
- 遇到重叠未提交改动时停止并报告，不覆盖其他任务输出。
- 完成前必须满足 Stop review request gate：`Status: Ready`、`Validation: Pass`、验证命令摘要，且 Ready 后没有新 code diff。

Acceptance:

- `python scripts\check_apex_distribution.py --json` 覆盖 orchestration command / protocol。
- `python -m unittest tests.test_apex_distribution` 返回 0。

## Implementation Phases

### Phase 1: Production Plan And Static Artifacts

- [x] 写本计划文档。
- [x] 写 `docs/apex-agent-portability.md`。
- [x] 写 `docs/platform-native-solutions.md`。
- [x] 写 `.codex-plugin/plugin.json` 和 `.claude-plugin/plugin.json`。
- [x] 写 `commands/*.toml` prompt wrappers。
- [x] 写 `.codex/skills/apex-lean-review/SKILL.md`。

### Phase 2: Verification Layer

- [x] 写 `scripts/check_apex_distribution.py`。
- [x] 写 `tests/test_apex_distribution.py`。
- [x] 写 `benchmarks/README.md`。
- [x] 写 `benchmarks/apex_distribution_benchmark.py`。

### Phase 3: Integration With Existing Apex Metadata

- [x] 在不覆盖并行改动的前提下，把 `apex-lean-review`、plugin manifests、benchmark 和 distribution check 纳入 README。
- [x] 把新增 artifacts 纳入 `docs/apexpowers-inventory.md`。
- [x] 让分发检查覆盖 README / inventory 元数据漂移。
- [x] 评估 `apex-doctor` 是否应该调用或复用 distribution check：暂不默认复用。doctor 面向安装后的目标项目，distribution check 面向 ApexPowers checkout 维护。
- [x] 评估 install copy list 是否应该包含 `apex-lean-review`：已纳入 README 的单项目和全局 Codex skill 复制清单，并加入 doctor core skill 检查。

### Phase 4: Supply-Chain Trust Hardening

- [x] 写 `docs/supply-chain-trust-security.md`。
- [x] 写 `NOTICE.md`。
- [x] 写 `docs/supply-chain-manifest.sha256` 并让 distribution checker 验证。
- [x] 把 supply-chain / trust / security 文档纳入 README、inventory 和分发测试。

### Phase 5: Parallel Delivery Orchestration Command

- [x] 写 `commands/apex-orchestrate-delivery.toml`。
- [x] 写 `docs/apex-parallel-delivery-orchestration.md`。
- [x] 把 orchestration command / protocol 纳入 README、inventory、distribution checker 和测试。

### Phase 6: Host Adapter Expansion

- [ ] OpenCode adapter：新增 `.opencode/command/` 或 plugin wrapper 时，必须先写结构测试。
- [ ] Gemini / Antigravity：只有确认 manifest schema 后再加，不复制 Claude / Codex hook map。
- [ ] Cursor / Windsurf / Cline / Kiro：只通过 generated rule mirror 支持，不手写长期副本。
- [ ] MCP：可选 `apex-mcp/` 只读工具，不能替代 lifecycle hooks。

## Validation Commands

```powershell
python scripts\check_apex_distribution.py --json
python -m unittest tests.test_apex_distribution
python benchmarks\apex_distribution_benchmark.py --runs 1 --json
python -m unittest tests.test_apex_doctor tests.test_apex_loop_hooks tests.test_apex_loop_installer
```

## Production Definition Of Done

- [ ] 6 个指定方向都有对应可维护 artifact。
- [ ] supply-chain / trust / security 文档和 NOTICE 覆盖社区分发边界。
- [ ] worktree / issue / PR 级并行交付有显式 orchestration command。
- [ ] 所有新增 artifacts 被 drift checker 覆盖。
- [ ] plugin manifests 是薄声明，不绕过 hook installer。
- [ ] anti-overengineering skill 可单独调用，不污染全局行为。
- [ ] platform-native 清单能被 reviewer 作为依据使用。
- [ ] benchmark harness 能离线运行并输出稳定 JSON。
- [ ] README / inventory / doctor / tests 对新增能力没有漂移。
- [ ] 全量相关单元测试通过。
