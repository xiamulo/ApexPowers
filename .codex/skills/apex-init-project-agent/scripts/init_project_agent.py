#!/usr/bin/env python3
"""Create a project-level AGENTS.md and companion rules documents."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


RULE_FILES = [
    "project-structure.md",
    "never-list.md",
    "coding-style.md",
    "api-design.md",
    "backend.md",
    "frontend.md",
    "git-workflow.md",
    "hooks.md",
]

SKIP_TOP_DIRS = {".git", ".serena", ".codex", "node_modules", "dist", "build", "coverage", ".next"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize project AGENTS.md and .claude/rules docs.")
    parser.add_argument("root", nargs="?", default=".", help="Project root. Defaults to current directory.")
    parser.add_argument(
        "--rules-dir",
        default=".claude/rules",
        help="Rules directory relative to project root. Defaults to .claude/rules.",
    )
    parser.add_argument("--write", action="store_true", help="Write files. Without this, only dry-run.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files. Use only on explicit request.")
    return parser.parse_args()


def detect_stack(root: Path) -> list[str]:
    stack: list[str] = []
    package_json = root / "package.json"
    if package_json.exists():
        stack.extend(package_stack(package_json))
    if (root / "pyproject.toml").exists():
        stack.append("Python / pyproject")
    if (root / "requirements.txt").exists():
        stack.append("Python / requirements.txt")
    if (root / "go.mod").exists():
        stack.append("Go")
    if (root / "Cargo.toml").exists():
        stack.append("Rust")
    if not stack:
        stack.append("待从项目文件补充")
    return unique(stack)


def package_stack(path: Path) -> list[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ["Node.js / package.json"]
    deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
    stack = ["Node.js / package.json"]
    if "react" in deps:
        stack.append("React")
    if "vite" in deps:
        stack.append("Vite")
    if "typescript" in deps:
        stack.append("TypeScript")
    if "next" in deps:
        stack.append("Next.js")
    if "vue" in deps:
        stack.append("Vue")
    return stack


def detect_commands(root: Path) -> list[str]:
    commands: list[str] = []
    package_json = root / "package.json"
    if package_json.exists():
        try:
            scripts = json.loads(package_json.read_text(encoding="utf-8")).get("scripts", {})
        except (OSError, json.JSONDecodeError):
            scripts = {}
        runner = "bun" if (root / "bun.lockb").exists() else "npm"
        for name in ("lint", "typecheck", "type-check", "test", "build", "dev"):
            if name in scripts:
                commands.append(f"{runner} run {name}")
    if (root / "pyproject.toml").exists() or (root / "requirements.txt").exists():
        commands.extend(["pytest", "ruff check .", "mypy ."])
    if (root / "go.mod").exists():
        commands.extend(["go test ./...", "go vet ./..."])
    if not commands:
        commands.append("按项目实际脚本补充 lint / type-check / test / build 命令")
    return unique(commands)


def top_dirs(root: Path) -> list[str]:
    dirs = [
        child.name
        for child in sorted(root.iterdir(), key=lambda item: item.name.lower())
        if child.is_dir() and child.name not in SKIP_TOP_DIRS and not child.name.startswith(".")
    ]
    return dirs or ["待补充"]


def unique(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def bullet(values: list[str]) -> str:
    return "\n".join(f"- {value}" for value in values)


def agents_md(root: Path, rules_dir: str) -> str:
    project = root.name
    rules = [
        ("project-structure.md", "项目目录、技术栈、文件放置原则"),
        ("never-list.md", "所有绝对不要做的硬性约束"),
        ("coding-style.md", "通用代码风格、命名、注释、目录文档纪律"),
        ("api-design.md", "接口边界、adapter、错误返回、兼容性"),
        ("backend.md", "后端相关约定，当前没有后端时作为未来扩展边界"),
        ("frontend.md", "前端栈、组件、状态、性能、交互规则"),
        ("git-workflow.md", "完成前验证、Git 操作边界、汇报格式"),
        ("hooks.md", "自动化 hooks、轻量格式化、轻量验证分层"),
    ]
    rules_table = "\n".join(f"| [{name}]({rules_dir}/{name}) | {purpose} |" for name, purpose in rules)
    return f"""# AGENTS.md - {project} 项目灵魂手册

## 核心人格与语气

- 默认写成温和、自然、像协作说明的中文。
- 先直接说结论，再补必要说明；少用明显的 AI 套话和空泛开头。
- 写 README、说明文档、汇报文档时，先参考同目录已有文档语气，尽量贴近用户文风。
- 避免把抽象流程、系统、模块写成很口语化的动作主体。
- 少用过硬的技术汇报腔，优先用朴素、清楚、可执行的表达。

## 核心协作原则

- 用户探索或提问时，认真回应问题本身，不要过早当成执行指令。
- 如果对任务内容或需求有关键不清楚的地方，先停下来问清楚，再继续。
- 变更前先理解现有代码和规则，优先小步、可测试、可回退的修改。
- 用户明确要求执行时，一次性完成当前任务，再汇报结果；不要把每一步都丢给用户确认。

## 强制工作流

1. 非平凡任务先写计划，必要时记录到 `tasks/todo.md`，包含清单、风险点和测试点。
2. 任务涉及多个方向、多个文件或并行调研时，拆成清晰子任务，避免主上下文混乱。
3. 每次被用户纠正后，把可复用教训记录到 `tasks/lessons.md` 或长期记忆文件。
4. 完成前按 `{rules_dir}/git-workflow.md` 做验证，并说明未能验证的部分。
5. 汇报时列出可能出问题的地方和建议覆盖的测试点。

## 工具与上下文

- 代码导航优先使用语义检索；已知路径的小修改可以直接读写对应文件。
- 涉及库、框架、SDK、API 或 CLI 的用法时，优先查官方或当前文档。
- 不读取 `.env`、密钥、凭据；删除、覆盖、批量改写前先说明影响范围。

## MCP 使用规范

- 任何涉及代码检索、上下文理解、调用链追踪、业务调研或查文档的任务，优先选择合适的 MCP / 工具。
- 代码语义检索优先用 Serena；库和框架文档优先用 Context7；本地批量文件和进程任务优先用 Desktop Commander。
- 复杂网络调研使用带规划的搜索流程；当前可用工具以实际会话工具列表为准。
- 调用 MCP 后简短说明用了哪个服务做了什么。
- 任何 MCP 都不得读取 `.env`、secrets 或凭据；带副作用操作前先说明影响范围。

## MEMORY.md 持久记忆管理

- 项目根目录 `MEMORY.md` 用作长期项目记忆库。
- 重要架构决策、用户纠正、跨会话需要保留的事实，应以结构化格式追加。
- `tasks/lessons.md` 存短期教训，`MEMORY.md` 存长期知识。
- 定期压缩和去重，避免长期记忆膨胀成噪音。

## 分形文档纪律

- 项目根规则放在本文件；细则放在 `{rules_dir}/`，按需加载。
- 每个业务子目录应有 `Agents.md`：控制在 3 行内，说明目录目的、主要文件、同步提醒。
- 源码文件头部应有简短 `@purpose / @deps / @exports / @location / @rules` 注释。
- 文件、接口、依赖、导出或目录结构变化时，同步更新相关头部注释和目录 `Agents.md`。

## AGENTS.md 自身维护

- 本文件尽量控制在 200 行以内；继续增长时，把细则拆到 `{rules_dir}/`。
- 2-4 周重写一次：先总结近期教训，再人工审核精简。
- 教训写进 `tasks/lessons.md` 或 `MEMORY.md`，不要堆进本文件。
- progressive disclosure：本文件只放总纲，细则按需加载。

## 规则入口

| 文件 | 适用场景 |
| --- | --- |
{rules_table}
"""


def project_structure_md(root: Path) -> str:
    return f"""# Project Structure

## 何时加载 / When to load

- 开始理解项目、移动文件、新增目录、判断代码应该放在哪里时加载。

## 项目定位 / Project Overview

- 项目名称：{root.name}
- 当前定位：已有项目，具体业务目标需要结合 README、源码和用户说明继续补充。

## 技术栈 / Tech Stack

{bullet(detect_stack(root))}

## 目录结构 / Directory Structure

{bullet(top_dirs(root))}

## 文件放置原则 / File Placement Rules

- 新文件优先放在语义最贴近的现有目录，避免为了单个用例新建抽象层。
- 共享工具放 `utils` / `lib` 一类目录；业务能力放回对应业务模块。
- 测试文件跟随项目现有约定，优先靠近被测模块或放入现有测试目录。

## 分形文档纪律 / Fractal Documentation

- 新增或调整目录时，同步维护该目录 `Agents.md`。
- 文件职责、依赖或导出变化时，同步维护文件头部注释。
"""


def never_list_md() -> str:
    return """# Never List

## 何时加载 / When to load

- 开始任何代码修改、删除文件、批量重构、处理高风险数据前加载。

## 绝对不要做 / Never do / NEVER / Forbidden patterns

- 不要覆盖用户已经手动修改过的文件，除非用户明确要求。
- 不要读取、打印、提交 `.env`、密钥、令牌、凭据或私人数据。
- 不要用大规模重写替代小步修改；不要为了显得高级而提前抽象。
- 不要静默吞掉异常；错误必须有可诊断上下文。
- 不要绕过现有测试、lint、类型检查，也不要禁用失败测试。

## 高风险区域 / High-risk areas / Critical files

- 配置、迁移、鉴权、支付、数据删除、构建发布、CI/CD、密钥管理相关文件。
- 项目级规则文件：`AGENTS.md`、`.claude/rules/`、目录 `Agents.md`。

## 不确定时的处理 / When in doubt / Escalation

- 先说明不确定点、可选方案和影响范围，再请求用户补充。
- 最多尝试三种不同方法；仍卡住时整理尝试、错误输出、诊断和备选路径。
"""


def coding_style_md() -> str:
    return """# Coding Style

## 何时加载 / When to load

- 写代码、改代码、重命名、拆分文件、添加注释或文档时加载。

## 基本风格 / Basic Style

- 优先直白、可读、容易测试的实现；避免聪明但难维护的技巧。
- 命名表达真实业务含义；不要用过度抽象的万能名称。
- import / dependency 保持局部、明确，避免无意义的跨层依赖。

## 文件大小与拆分 / File Size & Splitting

- 一个文件只承担一个清晰责任；膨胀时优先按真实职责拆分。
- 只有多个具体用例证明必要时再抽象公共层。

## 源码文件头注释 / Source File Header Comments

- 源码文件顶部使用简短 `@purpose / @deps / @exports / @location / @rules`。
- 头部注释必须基于实际代码，保持务实简洁，不写空泛说明。

## 目录 Agents.md / Directory Agents.md

- 每个业务子目录维护 `Agents.md`，最多 3 行。
- 文件或结构变化时，同步更新目录 `Agents.md` 和相关源码头部注释。

## React 约定 / React Conventions

- 组件职责清晰；复杂状态和副作用优先抽到 hooks 或 store。
- 避免不必要 render；依赖数组、memo 和 selector 要保持准确。

## 状态更新约定 / State Update Conventions

- 状态更新动作命名要描述意图；批量更新要保持边界清楚。

## 错误处理 / Error Handling

- 用户可见错误要可理解；日志要保留定位信息但不能泄露敏感数据。

## 注释原则 / Commenting Principles

- 注释解释原因、约束和非显而易见的决策，不重复代码表面含义。
"""


def api_design_md() -> str:
    return """# API Design

## 何时加载 / When to load

- 新增接口、调整数据结构、接入外部格式、设计 store action 或错误返回时加载。

## 当前项目实际边界 / Current Project Boundaries

- 先以当前仓库已有 API / store / adapter / IO 边界为准。
- 没有明确后端时，不要凭空设计服务端协议。

## 接口分类 / Interface Classification

- 区分 UI 事件、Store action、IO 读写、渲染接口、格式转换接口。

## Adapter 原则 / Adapter Principles

- 外部格式转换集中在 adapter；业务层使用稳定的内部结构。

## Store action 设计 / Store Action Design

- action 名称描述业务意图；避免把 UI 细节泄漏进核心状态层。

## 错误返回 / Error Returns

- 错误结构保持可诊断；用户提示和开发日志分层处理。

## 权限与鉴权 / Permissions & Auth

- 鉴权、权限、用户身份相关逻辑必须显式，不能散落在 UI 分支里。

## 兼容性 / Compatibility

- schema 和文件格式变更要考虑旧数据；必要时提供迁移或降级路径。
"""


def backend_md() -> str:
    return """# Backend

## 何时加载 / When to load

- 修改服务端、数据库、API、鉴权、日志、配置或准备新增后端时加载。

## 当前仓库状态 / Current Repository Status

- 先按当前仓库实际存在的后端边界处理；没有后端时只记录未来约定。

## 如果未来新增 Go 后端 / If Future Go Backend Added

- model / migration / repository / service / handler 分层清晰。
- 跨层依赖通过接口传入，避免全局单例扩散。

## GORM 约定 / GORM Conventions

- model 显式声明字段和索引；查询封装在 repository；迁移可回溯。

## JSON 与错误 / JSON & Error

- JSON 返回结构稳定；错误包含内部诊断信息但不向用户泄露敏感细节。

## 配置与日志 / Configuration & Logging

- 配置来自环境或配置文件；日志脱敏，不打印密钥、令牌、个人数据。

## 与当前前端集成 / Frontend Integration

- 前端优先通过 adapter 消化后端格式变化；保持离线或降级路径清晰。
"""


def frontend_md() -> str:
    return """# Frontend

## 何时加载 / When to load

- 修改 UI、组件、状态、样式、动画、Canvas/WebGL、导入保存或性能问题时加载。

## 当前前端栈 / Current Frontend Stack

- 以项目实际 package.json 和现有代码为准；不要凭模板假设框架。

## UI 组件 / UI Components

- 组件只承担清晰职责；复用组件放在现有组件目录，业务组件跟随业务模块。

## Tailwind 与主题 / Tailwind & Theming

- 样式优先沿用项目现有系统；不要引入冲突的主题和色彩体系。

## 状态分层 / State Layering

- 区分持久状态、运行态状态、派生状态；避免重复存储同一事实。

## Canvas / WebGL 交互 / Canvas & WebGL Interaction

- 渲染资源创建和释放必须成对；交互状态和渲染循环保持边界清楚。

## 动画 / Animation

- 动画服务于反馈和理解；避免影响可读性、性能或可访问性。

## 导入/保存/加载 / Import Save Load

- 外部格式进入系统前先经过 adapter；保存格式保持向后兼容。

## 请求与外部资源 / Requests & External Resources

- 本地优先；外部资源失败时提供可理解的降级路径。

## 性能 / Performance

- 避免不必要重渲染；昂贵计算使用缓存、分片或后台处理。
"""


def git_workflow_md(root: Path) -> str:
    return f"""# Git Workflow

## 何时加载 / When to load

- 完成任务前、准备提交、处理冲突、涉及删除/移动/批量变更时加载。

## 完成前验证清单 / Pre-Commit Validation Checklist

- 检查 diff，确认没有无关改动、调试输出、密钥或生成垃圾。
- 运行项目对应 lint、type-check、test、build；不能运行时说明原因。
- 新行为需要补测试，或说明未补测试的风险。

## 推荐验证命令 / Recommended Validation Commands

{bullet(detect_commands(root))}

## 手动测试重点 / Manual Testing Focus

- 覆盖被改功能的主路径、失败路径、边界输入和回归风险点。

## Git 操作边界 / Git Operation Boundaries

- 不执行破坏性 git 命令；不回滚用户未明确要求回滚的改动。
- 提交信息解释为什么改，而不仅是改了什么。

## 提交信息建议 / Commit Message Guidelines

- 使用简短动词开头，说明意图和影响范围。

## 汇报格式 / Reporting Format

- 先说完成了什么，再说验证结果，最后列出未验证或需要注意的风险。
"""


def hooks_md() -> str:
    return """# Hooks

## 何时加载 / When to load

- 配置自动格式化、保存后检查、提交前检查、工具钩子或轻量验证流程时加载。

## PostToolUse 轻量格式化 / PostToolUse Formatting

- 只做确定、低风险、可重复的格式化；不要在 hook 里做大型重构。

## Stop 轻量验证 / Stop Validation

- Stop 阶段适合跑快速检查；耗时验证应显式告知并按任务需要执行。

## 手动 review 分层 / Manual Review Layers

- 自动检查负责格式和明显错误；人工 review 关注行为、架构和边界。

## 失败处理 / Failure Handling

- hook 失败时保留完整命令和错误摘要，不要静默忽略。
"""


def planned_files(root: Path, rules_root: Path, rules_dir: str) -> dict[Path, str]:
    return {
        root / "AGENTS.md": agents_md(root, rules_dir),
        rules_root / "project-structure.md": project_structure_md(root),
        rules_root / "never-list.md": never_list_md(),
        rules_root / "coding-style.md": coding_style_md(),
        rules_root / "api-design.md": api_design_md(),
        rules_root / "backend.md": backend_md(),
        rules_root / "frontend.md": frontend_md(),
        rules_root / "git-workflow.md": git_workflow_md(root),
        rules_root / "hooks.md": hooks_md(),
    }


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"Project root is not a directory: {root}")

    rules_root = (root / args.rules_dir).resolve()
    try:
        rules_dir = rules_root.relative_to(root).as_posix()
    except ValueError as exc:
        raise SystemExit(f"Rules directory must stay inside project root: {rules_root}") from exc

    created = 0
    skipped = 0
    for path, content in planned_files(root, rules_root, rules_dir).items():
        exists = path.exists()
        if exists and not args.force:
            skipped += 1
            print(f"SKIP exists: {path}")
            continue
        action = "WRITE" if args.write else "DRY-RUN"
        suffix = "overwrite" if exists else "create"
        print(f"{action} {suffix}: {path}")
        created += 1
        if args.write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    mode = "written" if args.write else "would write"
    print(f"Summary: {created} {mode}, {skipped} skipped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
