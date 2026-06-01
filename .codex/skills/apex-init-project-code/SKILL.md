---
name: apex-init-project-code
description: Initialize missing standard header comments in existing project code using agent-written, code-aware content. Use when the user asks to scan code files and add @purpose/@deps/@exports/@location/@rules headers without overwriting existing headers.
---

# Apex Init Project Code

## Workflow

Use `scripts/init_code_headers.py <project-root> [paths...]` only to find supported code files whose first 40 lines do not contain `@purpose` or `文件作用` and that do not already start with a header comment. The script is discovery-only and must not insert or rewrite headers.

For each reported file, read the actual code and generate the header yourself. Descriptions must be based on real imports, exports, declarations, side effects, and the file's role in its folder. Do not rely on script guesses.

Use the language-appropriate comment syntax:

- `.ts/.tsx/.js/.jsx/.go/.rs/.java/.cs/.cpp/.c/.h/.hpp/.kt`: `//`
- `.py`: `#`
- `.md/.mdx`: `<!-- -->` only when explicitly requested with `--include-md`

Header template, within eight lines:

```text
@purpose: [一句话准确描述本文件核心作用]
@deps: [关键 import/依赖模块，最重要的 3-5 个]
@exports: [主要对外提供的函数/类/变量/接口]
@location: [当前文件夹相对路径]（参考 @当前文件夹/claude.md）
@rules: [本文件必须遵守的 1-2 条核心架构或编码约定]

Claude: 本文件内容、接口、依赖、导出或架构发生任何变更时，请**立即**同步更新本头部注释，并同时更新所属文件夹的 claude.md 文件。
```

Only modify files reported by the discovery script. Never overwrite or reformat an existing header comment, even if its format differs from this standard.
