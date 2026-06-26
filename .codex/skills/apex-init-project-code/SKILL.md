---
name: apex-init-project-code
description: 初始化已有项目中缺失的源码文件头部注释。适用于用户要求扫描代码文件，并在不覆盖已有头部注释的前提下，由 agent 根据真实代码写入 @purpose/@scope/@deps/@exports/@invariants 标准头。
---

# Apex Init Project Code

## 工作流

只使用 `scripts/init_code_headers.py <project-root> [paths...]` 查找缺少标准头部注释的代码文件。这个脚本只负责发现候选文件：前 40 行内没有 `@purpose` 或 `文件作用`。普通文件头注释、license 注释或 shebang 不算 Apex 标准头，不能让文件被跳过。脚本绝不负责插入或重写头部注释。

对每个发现脚本列出的文件，先阅读真实代码，再由你生成头部注释。描述必须基于实际 import、依赖、导出、声明、副作用，以及文件在当前文件夹中的角色。不要依赖脚本猜测。

如果用户明确要求“重新生成 / 重跑 / 覆盖 / 刷新 / regenerate”，就进入重新生成模式：已有头部注释的代码文件也必须重新处理，不能因为文件已有注释就跳过。使用辅助脚本时传入 `--all`、`--force` 或 `--regenerate` 获取全量代码文件清单。

根据文件扩展名使用对应注释语法：

- `.ts/.tsx/.js/.jsx/.go/.rs/.java/.cs/.cpp/.c/.h/.hpp/.kt`：使用 `//`
- `.py`：使用 `#`
- `.md/.mdx`：只有用户明确要求 `--include-md` 时，才使用 `<!-- -->`

标准头部模板必须控制在 8 行以内：

```text
@purpose: [50字内说明本文件在系统/模型流程中的定位、核心职责和上下游作用；不要复述文件名、路径、类名或实现步骤]
@scope: [所属业务域/架构层，如 auth/domain、billing/api、model/postprocess]
@deps: [关键跨层依赖或不可替换依赖，最多 3 个；无则 none]
@exports: [对外公共 API/入口；纯内部文件写 internal]
@invariants: [修改时必须保持的 1 条业务、数据或架构约束；无则 none]

Claude: 本文件内容、接口、依赖、导出或架构发生任何变更时，请**立即**同步更新本头部注释，并同时更新所属文件夹的 claude.md 文件。
```

默认模式下只修改发现脚本列出的缺失文件。重新生成模式下，按用户要求更新或重写已有头部注释；仍然必须先阅读真实代码，避免机械模板化。
