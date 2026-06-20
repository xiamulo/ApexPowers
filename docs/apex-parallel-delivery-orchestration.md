# Apex Parallel Delivery Orchestration

This document is the explicit orchestration protocol for worktree-level, issue-level, and PR-level parallel delivery.

## Purpose

ApexPowers already has role templates, generated agent mirrors, `apex-to-issues` issue splitting, and the Stop review request gate. The missing layer is an explicit command that tells the operator how to compose those pieces into one delivery run.

The command entrypoint is:

```text
apex-orchestrate-delivery
```

## Delivery Levels

| Level | Use when | Required output |
| --- | --- | --- |
| Worktree-level | Multiple agents or CLIs may touch the same repository checkout or sibling worktrees. | Worktree map, dirty-state check, non-overlap file scope, validation owner per worktree. |
| Issue-level | A PRD, spec, or plan needs independent vertical slices. | `apex-to-issues` breakdown, dependency order, HITL/AFK marking, issue owner role. |
| PR-level | A branch or PR aggregates multiple slices. | PR readiness ledger, review status, validation summary, unresolved risk list. |

## Role Source Of Truth

Private role templates live in `.agents/*.md`.

The official agent mirrors are generated artifacts:

- Codex: `.codex/agents/*.toml`
- Claude Code: `.claude/agents/*.md`

Before dispatching parallel work, the orchestrator must check mirror freshness. If `.agents/*.md` changed or mirrors are missing, run or ask for:

```powershell
python .codex\skills\apex-sync-agent-mirrors\scripts\sync_agent_mirrors.py . --target all
python .codex\skills\apex-sync-agent-mirrors\scripts\sync_agent_mirrors.py . --target all --write
```

## Six Role Templates

| Role | Dispatch purpose | Do not use for |
| --- | --- | --- |
| `planner` | Turn fuzzy work into `tasks/todo+*.md`, dependencies, file scope, validation gates. | Direct implementation. |
| `researcher` | Source-backed code, docs, compatibility, or external ecosystem research. | Writing production code. |
| `implementer` | Execute an approved plan exactly. | Replanning or widening scope. |
| `developer` | Handle clear small/medium fixes with limited local judgment. | Large architecture or unclear acceptance. |
| `code-reviewer` | Review completed diffs and produce Ready / Needs Attention / Needs Work verdicts. | Modifying files. |
| `perf-optimizer` | Investigate and improve performance-sensitive paths. | General feature work. |

## Orchestration Ledger

Every run must maintain a concise ledger in the conversation, a plan file, or a PR comment.

Required fields:

| Field | Requirement |
| --- | --- |
| Slice / issue | One vertical slice or PR subtask. |
| Level | `worktree`, `issue`, or `PR`. |
| Dependencies | Blocking slices or "None". |
| Owner role | One of the six role templates. |
| Worktree / branch | Concrete checkout or branch name, when known. |
| File scope | Expected files or directories; flag overlapping dirty files. |
| Validation | Commands that prove the slice. |
| Review gate | Required reviewer and expected Stop gate status. |

## Required Flow

1. Intake the request, current repo state, active worktrees, open issue/PR references, and relevant project rules.
2. Decide the delivery level: worktree, issue, PR, or a combination.
3. If input is a PRD/spec/plan, run the `apex-to-issues` process before implementation and publish or draft vertical-slice issues in dependency order.
4. Check `.agents` templates and official mirrors. Regenerate mirrors only when requested or when the user approved write mode.
5. Build the orchestration ledger before dispatching work.
6. Stop immediately if the current worktree has overlapping uncommitted changes with the planned slice.
7. Dispatch roles by responsibility, not by availability.
8. Merge results only after each slice has validation evidence.
9. Require the Stop review request gate before done:
   - review file exists under `tasks/reviews/`,
   - `code-reviewer` verdict is Ready or accepted by the user,
   - `> **Status**: Ready`,
   - `> **Validation**: Pass`,
   - commands and results are summarized,
   - no new code diff appears after the Ready review without another review pass.

## Conflict Policy

Parallel work must not overwrite user or other-agent changes.

Stop and report when:

- a planned file is already modified in the current checkout by unrelated work,
- two slices need the same file without an explicit merge owner,
- a worktree or branch cannot be identified,
- the issue dependency order is ambiguous,
- a role handoff lacks validation commands.

## Done Criteria

- The orchestration ledger is complete.
- All slices are either done or explicitly deferred.
- Review gate and validation gate are satisfied for the PR or final worktree.
- README, inventory, distribution checks, and tests are updated when the command or protocol changes.
