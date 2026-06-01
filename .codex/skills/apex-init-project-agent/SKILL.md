---
name: apex-init-project-agent
description: 初始化已有项目的项目级 AGENTS.md 和 .claude/rules 规则文档。适用于用户希望创建可维护的项目协作手册、分层规则文档，且不覆盖已有手写规则文件的场景。
---

# Apex Init Project Agent

## 工作流

运行 `scripts/init_project_agent.py <project-root>`。默认只预览；确认范围合理后，才传入 `--write` 真正写入固定的根 `AGENTS.md`，并创建 `.claude/rules/` 目录。

项目根目录 `AGENTS.md` 必须使用脚本里的固定模板原文，不要总结、改写、删减或重新组织。

`.claude/rules/*.md` 不能由脚本套模板硬写。脚本只列出缺失的规则文件；你必须读取项目源码、配置、目录结构、README/docs 和已有约定后，再由模型根据真实项目上下文写入 rules 内容。

需要生成的 rules 文件包括：project-structure、never-list、coding-style、api-design、backend、frontend、git-workflow 和 hooks。已有 rules 文件默认不覆盖；只有用户明确要求重写时，才可以改写已有文件。

## rules 写法

每个 rules 文件都必须使用固定的二级标题模板。二级标题只作为结构骨架；读取项目源码后，把具体规则写在对应二级标题下面的三级标题里。

不要把泛泛模板内容直接写在二级标题下面。每条规则都要来自项目真实源码、配置、目录结构、README/docs 或用户明确约定。

固定二级标题模板如下：

```markdown
# project-structure.md
## 何时加载 / When to load（明确触发时机）
## 项目定位 / Project Overview
## 技术栈 / Tech Stack
## 目录结构 / Directory Structure（顶层目录）
## 文件放置原则 / File Placement Rules
## 分形文档纪律

# never-list.md
## 何时加载 / When to load（明确触发时机）
## 绝对不要做 / Never do / NEVER / Forbidden patterns（核心禁止清单）
## 高风险区域 / High-risk areas / Critical files（重点保护区）
## 不确定时的处理 / When in doubt / Escalation（兜底流程）

# coding-style.md
## 何时加载 / When to load（明确触发时机）
## 基本风格 / Basic Style（命名、import、复用约定）
## 文件大小与拆分 / File Size & Splitting（单文件拆分原则）
## 源码文件头注释 / Source File Header Comments（@tag 格式要求）
## 目录 claude.md / Directory AGENTS.md（分形文档纪律）
## React 约定 / React Conventions（hooks、render 优化）
## 状态更新约定 / State Update Conventions（store action 规则）
## 错误处理 / Error Handling（用户可见错误与日志）
## 注释原则 / Commenting Principles（保留与噪音控制）

# api-design.md
## 何时加载 / When to load（明确触发时机）
## 当前项目实际边界 / Current Project Boundaries（本仓库 API 范围）
## 接口分类 / Interface Classification（UI / Store / IO / 渲染 / 格式）
## Adapter 原则 / Adapter Principles（外部格式转换规则）
## Store action 设计 / Store Action Design（action 命名与批量规则）
## 错误返回 / Error Returns（错误格式与处理）
## 权限与鉴权 / Permissions & Auth（未来扩展）
## 兼容性 / Compatibility（schema 与格式兼容）

# backend.md
## 何时加载 / When to load（明确触发时机）
## 当前仓库状态 / Current Repository Status（前端本地编辑器边界）
## 如果未来新增 Go 后端 / If Future Go Backend Added（目录与集成规则）
## GORM 约定 / GORM Conventions（model / migration / repository 分层）
## JSON 与错误 / JSON & Error（返回结构与日志）
## 配置与日志 / Configuration & Logging（环境变量与隐私保护）
## 与当前前端集成 / Frontend Integration（离线能力与资产保护）

# frontend.md
## 何时加载 / When to load（明确触发时机）
## 当前前端栈 / Current Frontend Stack（技术栈与注意事项）
## UI 组件 / UI Components（组件放置与职责划分）
## Tailwind 与主题 / Tailwind & Theming（样式与主题约定）
## 状态分层 / State Layering（store 分层与持久 vs 运行态）
## Canvas / WebGL 交互 / Canvas & WebGL Interaction（画布交互与 GPU 管理）
## 动画 / Animation（动画模式、draft pose 与插值规则）
## 导入/保存/加载 / Import Save Load（PSD、.stretch 与资源重建）
## 请求与外部资源 / Requests & External Resources（本地优先与降级路径）
## 性能 / Performance（渲染优化与 selector 粒度）

# git-workflow.md
## 何时加载 / When to load（明确触发时机）
## 完成前验证清单 / Pre-Commit Validation Checklist（必检项）
## 推荐验证命令 / Recommended Validation Commands（lint/build/dev）
## 手动测试重点 / Manual Testing Focus（关键功能点）
## Git 操作边界 / Git Operation Boundaries（只读与禁止操作）
## 提交信息建议 / Commit Message Guidelines（格式建议）
## 汇报格式 / Reporting Format（完成时汇报模板）
```

写每个二级标题时，先补一个或多个三级标题，例如 `### 当前项目约定`、`### 已确认事实`、`### 例外与不适用项`、`### 执行要求`，再把根据源码分析出的具体内容写进去。

只有在用户明确要求重新生成根 `AGENTS.md` 时，才使用 `--force` 覆盖它。
