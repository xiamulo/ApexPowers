"""Tests for the apex-init-project-agent root template generator."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".codex" / "skills" / "apex-init-project-agent" / "scripts" / "init_project_agent.py"


class InitProjectAgentTests(unittest.TestCase):
    def run_script(self, root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(root), *args],
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_generated_roots_include_chinese_task_contract(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)

            result = self.run_script(root, "--write")

            self.assertEqual(result.returncode, 0, result.stderr)
            claude_md = (root / "CLAUDE.md").read_text(encoding="utf-8")
            agents_md = (root / "AGENTS.md").read_text(encoding="utf-8")

        for content in (claude_md, agents_md):
            self.assertIn("契约式小任务 + 运行时结构化分解 + 证据化验收", content)
            self.assertIn("任务ID:", content)
            self.assertIn("允许路径:", content)
            self.assertIn("禁止路径:", content)
            self.assertIn("必跑检查:", content)
            self.assertIn("交付证据:", content)
            self.assertIn("需要审查: true", content)

        self.assertIn("任务契约与证据化验收", agents_md)
        self.assertIn('禁止使用 `fork_turns: "all"`', claude_md)
        self.assertIn('禁止使用 `fork_turns: "all"`', agents_md)
        self.assertIn("必须阅读的 md 文档", claude_md)
        self.assertIn("必须阅读的 md 文档", agents_md)
        self.assertIn("叶子执行者", claude_md)
        self.assertIn("叶子执行者", agents_md)
        self.assertIn("不能再 spawn / fork / 调度新的 Subagent", claude_md)
        self.assertIn("不能再 spawn / fork / 调度新的 Subagent", agents_md)


if __name__ == "__main__":
    unittest.main()
