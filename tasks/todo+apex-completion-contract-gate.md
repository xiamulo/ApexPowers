# Task: Apex Completion Contract Gate

## Contract

```yaml
任务ID: apex-completion-contract-gate
目标: 补强 ApexPowers 的完成契约，避免按计划执行时只交 MVP、第一版或部分 Slice
风险等级: 中
范围:
  允许路径:
    - .codex/skills/apex-init-project-agent/SKILL.md
    - .codex/skills/apex-init-project-agent/agents/openai.yaml
    - .codex/skills/apex-init-project-agent/scripts/init_project_agent.py
    - .codex/skills/apex-init-project-hooks/SKILL.md
    - .codex/skills/apex-init-project-hooks/scripts/apex_loop_runtime.py
    - .agents/Agents.md
    - .agents/planner.md
    - .agents/implementer.md
    - .agents/developer.md
    - .codex/agents/**
    - .claude/agents/**
    - tests/test_init_project_agent.py
    - tests/test_apex_loop_hooks.py
    - docs/supply-chain-manifest.sha256
    - tasks/todo+apex-completion-contract-gate.md
    - tasks/reviews/apex-completion-contract-gate.md
  禁止路径:
    - tasks/loops/apex-loop-hooks/state.json
    - tasks/loops/apex-loop-hooks/.state.json.287900.tmp
    - scripts/check_apex_distribution.py
验收:
  - 最小交付规则明确不等于 MVP、第一版或部分 Slice
  - 执行计划被定义为本轮完成契约，final 前必须逐项核对 Slice、Step、验收、必跑检查和交付证据
  - Subagent 规则按真实系统优先级表达：环境允许且用户明确允许时优先拆分，否则主 agent 按同一 contract 自行执行
  - Stop hook 新增 ContractGate，active todo 存在未完成 `- [ ]` checklist 时阻塞完成
  - ContractGate 不阻塞纯 todo 规划变更
必跑检查:
  - py -3 -m py_compile .codex\skills\apex-init-project-agent\scripts\init_project_agent.py .codex\skills\apex-init-project-hooks\scripts\apex_loop.py .codex\skills\apex-init-project-hooks\scripts\apex_loop_runtime.py .codex\skills\apex-sync-agent-mirrors\scripts\sync_agent_mirrors.py
  - py -3 -m unittest tests.test_init_project_agent tests.test_apex_loop_hooks
  - py -3 .codex\skills\apex-sync-agent-mirrors\scripts\sync_agent_mirrors.py . --target all --write
  - py -3 scripts\check_apex_distribution.py --write-sha256-manifest
  - py -3 -m unittest tests.test_apex_distribution
  - git diff --check
交付证据:
  - 变更文件
  - ContractGate 测试输出摘要
  - 模板测试输出摘要
  - 已知限制
需要审查: true
```

## Runtime Decomposition

### Epic: Completion Contract Hardening

- [x] Slice 1: 创建本轮独立任务契约，避免复用禁止改 hooks 的旧任务。
- [x] Slice 2: 补硬 `apex-init-project-agent` 根模板里的最小交付、计划完成契约和 Subagent 环境兼容规则。
- [x] Slice 3: 同步 `.agents` 源模板与 Codex / Claude mirrors。
- [x] Slice 4: 在 Stop hook 加 `ContractGate`，阻塞 active todo 中未完成的 `- [ ]` checklist。
- [x] Slice 5: 增加并运行模板与 hook 回归测试。
- [x] Slice 6: 创建 review 请求并记录验证证据。

## Validation Evidence

- `py -3 -m py_compile .codex\skills\apex-init-project-agent\scripts\init_project_agent.py .codex\skills\apex-init-project-hooks\scripts\apex_loop.py .codex\skills\apex-init-project-hooks\scripts\apex_loop_runtime.py .codex\skills\apex-sync-agent-mirrors\scripts\sync_agent_mirrors.py` - pass.
- `py -3 .codex\skills\apex-sync-agent-mirrors\scripts\sync_agent_mirrors.py . --target all --write` - pass, 12 mirror files checked.
- `py -3 -m unittest tests.test_init_project_agent tests.test_apex_loop_hooks` - pass, 31 tests.
- `py -3 -m unittest tests.apex_hooks.test_stop_loop_safety` - pass, 2 tests.
- `py -3 -m unittest tests.test_apex_distribution` - initially failed because trust-critical hook file hashes drifted; contract updated to allow manifest refresh after diff review.
- `py -3 scripts\check_apex_distribution.py --write-sha256-manifest` - pass, 14 checks; refreshed trust-critical hashes.
- `py -3 -m unittest tests.test_init_project_agent tests.test_apex_loop_hooks tests.apex_hooks.test_stop_loop_safety tests.test_apex_distribution` - pass, 40 tests.
- `py -3 scripts\check_apex_distribution.py --json` - pass, 14 checks.
- `git diff --check` - pass.
- `rg -n "MVP|第一版|部分 Slice|本轮完成契约|ContractGate|系统规则禁止自动 spawn|main-agent-fallback|未完成项存在" ...` - pass, required text present.

## Known Limits

- ContractGate 第一版只做确定性 Markdown checkbox 检查，不解析自然语言验收完成度。
