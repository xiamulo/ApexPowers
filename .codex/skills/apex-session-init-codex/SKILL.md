---
name: apex-session-init-codex
description: "Codex 开工初始化 skill。Use at the beginning of a Codex session or when the user asks for apex-session-init: read the project-root AGENTS.md first, read CLAUDE.md too when present, confirm understanding, then perform the current task under those rules."
---

# Apex Session Init Codex

## 工作流

在开始任何任务分析、计划、编辑、提交、运行验证或外部检索之前，先执行下面步骤。允许的前置动作只有定位项目根目录和读取规则文件。

1. 从当前工作目录定位活动项目根目录。
2. 完整阅读项目根目录的 `AGENTS.md`。不要依赖摘录、摘要、记忆或假设。
3. 如果项目根目录存在 `CLAUDE.md`，也完整阅读；除非它与 Codex 专用的 `AGENTS.md` 冲突，否则把它作为补充项目规则。
4. 如果项目根目录同时缺少 `AGENTS.md` 和 `CLAUDE.md`，明确说明未找到项目根规则文件，然后只依据当前会话中已经可见的更高优先级指令继续。
5. 读完至少一个规则文件后，明确回复确认：`我已经阅读并理解了 AGENTS.md / CLAUDE.md 中的规则。`
6. 如果用户已经给出具体任务，确认后继续完成当前任务；不要只停在确认句。

## Codex 侧优先级

- 以 `AGENTS.md` 作为 Codex 行为的主要项目契约。
- 仅在 `CLAUDE.md` 存在且提供不冲突的项目事实、命令或约束时，将其作为补充规则。
- 如果两个项目文件冲突，先遵守系统、开发者、用户等更高层级指令；同层项目规则冲突时，优先采用当前 host 对应文件，并在影响任务时简短说明冲突。

## 执行边界

- 不要用总结或转述替代实际读取规则文件。
- 不要编造不存在的项目规则。
- 不要在规则文件读取前执行任务特定的工具调用。
- 把用户的疑问当作真正的问题回答；只有当用户明确要求开始工作时才进入实现。
