---
name: apex-init-project-code
description: Initialize existing project code files with missing standard header comments. Use when the user asks to scan an existing project or selected directories and add concise @purpose/@deps/@exports/@location/@rules headers without overwriting existing file headers.
---

# Apex Init Project Code

## Workflow

Run `scripts/init_code_headers.py <project-root> [paths...]` from this skill directory. Default mode is a dry run; pass `--write` only after confirming the target list is reasonable.

The script scans supported code files, skips generated/vendor folders, and inserts a header only when the first 40 lines contain neither `@purpose` nor `文件作用` and the file does not already start with a header comment. It must never overwrite or reformat existing headers.

Generated headers stay within eight lines and use the correct comment syntax for the file type. Descriptions are derived from imports, exports, declarations, file name, and folder path; review broad or generic headers before committing.
