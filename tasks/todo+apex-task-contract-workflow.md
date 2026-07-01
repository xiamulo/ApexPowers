# Task: Apex Task Contract Workflow

## Contract

```yaml
任务ID: apex-task-contract-workflow
目标: 将 apex-init-project-agent 生成的根 AGENTS/CLAUDE 工作流升级为中文 key 的任务契约模式
风险等级: 中
范围:
  允许路径:
    - .codex/skills/apex-init-project-agent/SKILL.md
    - .codex/skills/apex-init-project-agent/agents/openai.yaml
    - .codex/skills/apex-init-project-agent/scripts/init_project_agent.py
    - .agents/Agents.md
    - .agents/planner.md
    - .agents/implementer.md
    - .agents/developer.md
    - .codex/agents/**
    - .claude/agents/**
    - tests/test_init_project_agent.py
    - tasks/todo+apex-task-contract-workflow.md
    - tasks/reviews/apex-task-contract-workflow.md
  禁止路径:
    - .codex/skills/apex-init-project-hooks/**
    - scripts/check_apex_distribution.py
    - docs/supply-chain-manifest.sha256
验收:
  - 生成的 CLAUDE.md 包含契约式小任务、运行时结构化分解和证据化验收规则
  - 生成的 AGENTS.md 继承该工作流，并在 Codex 内联硬规则中再次强调任务契约
  - YAML contract 示例使用中文参数名
  - 规则说明明确 allowed/forbidden/checks 不能凭空编造
  - 主 agent 派发 Subagent 时禁止 `fork_turns: "all"`，必须手写最小子任务包和必须阅读的 md 文档清单
  - Subagent 被明确标注为叶子执行者，不能再 spawn/fork/调度新的 Subagent
必跑检查:
  - py -3 -m py_compile .codex\skills\apex-init-project-agent\scripts\init_project_agent.py
  - py -3 -m py_compile .codex\skills\apex-sync-agent-mirrors\scripts\sync_agent_mirrors.py
  - py -3 -m unittest tests.test_init_project_agent
交付证据:
  - 变更文件
  - 运行命令
  - 测试输出摘要
  - 已知限制
需要审查: true
```

## Current Evidence

- `apex-init-project-agent` 的 `SKILL.md` 要求根 `AGENTS.md` 必须使用脚本固定模板原文。
- `scripts/init_project_agent.py` 通过 `CLAUDE_TEMPLATE` + `CODEX_RULE_APPENDIX` 生成根 `AGENTS.md`。
- 现有模板已有“非平凡任务立即进入 Plan Mode”，但没有完整任务契约 schema、中文 YAML key、scope hard boundary 和证据化验收要求。

## Runtime Decomposition

### Epic: Contract-first root workflow

- [x] Slice 1: 更新 `CLAUDE_TEMPLATE` 的非平凡任务规则，把 Plan Mode 升级为任务契约。
- [x] Slice 2: 更新 `CODEX_RULE_APPENDIX`，给 Codex 内联最小硬约束。
- [x] Slice 3: 更新 skill 维护说明和 openai prompt，避免生成器维护时漏掉新工作流。
- [x] Slice 4: 增加最窄模板测试并运行验证。
- [x] Slice 5: 完成 review 记录。
- [x] Slice 6: 增加 Subagent 上下文隔离规则，禁止 `fork_turns: "all"` 并要求子智能体作为叶子执行者。

## Validation Evidence

- `py -3 -m py_compile .codex\skills\apex-init-project-agent\scripts\init_project_agent.py` - pass.
- `py -3 -m py_compile .codex\skills\apex-sync-agent-mirrors\scripts\sync_agent_mirrors.py` - pass.
- `py -3 -m unittest tests.test_init_project_agent` - pass, 1 test.
- `py -3 -m unittest tests.test_apex_distribution` - pass, 7 tests.
- `py -3 -m unittest tests.test_init_project_agent tests.test_apex_distribution` - pass, 8 tests.
- `py -3 scripts\check_apex_distribution.py --json` - pass, 14 checks.
- `git diff --check -- .codex/skills/apex-init-project-agent/SKILL.md .codex/skills/apex-init-project-agent/agents/openai.yaml .codex/skills/apex-init-project-agent/scripts/init_project_agent.py tests/test_init_project_agent.py tasks/todo+apex-task-contract-workflow.md` - pass.
- `py -3 .codex\skills\apex-sync-agent-mirrors\scripts\sync_agent_mirrors.py . --target all --write` - pass, planner/developer/implementer Codex and Claude mirrors overwritten from `.agents` source.
- `rg -n 'fork_turns: ""all""|叶子执行者|必须阅读的 md 文档|不能再 spawn / fork / 调度新的 Subagent' ...` - pass, required text present in generator template, source agents, generated mirrors, tests, and todo.
- `git diff --check -- .codex/skills/apex-init-project-agent/SKILL.md .codex/skills/apex-init-project-agent/agents/openai.yaml .codex/skills/apex-init-project-agent/scripts/init_project_agent.py .agents/Agents.md .agents/planner.md .agents/implementer.md .agents/developer.md .codex/agents/developer.toml .codex/agents/implementer.toml .codex/agents/planner.toml .claude/agents/developer.md .claude/agents/implementer.md .claude/agents/planner.md tests/test_init_project_agent.py tasks/todo+apex-task-contract-workflow.md` - pass.

## Known Limits

- 本次只修改生成模板和生成器说明，不重新生成当前仓库根 `AGENTS.md`。
- 中文 YAML key 可被 YAML 解析器接受；若未来接入自动解析，需要保持 key 稳定并补 schema 测试。
- 本次 review 文件仍标记 pending independent review；实现者不能把自己的自检冒充独立 review。
