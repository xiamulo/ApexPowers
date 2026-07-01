"""PostToolUse contract tests for already-executed tool feedback."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / ".codex" / "skills" / "apex-init-project-hooks" / "scripts" / "apex_loop.py"


def secret_fixture() -> str:
    """Secret-like token assembled at runtime so scanners do not flag source."""

    return "sk-" + "abcdefghijklmnopqrstuvwxyz" + "123456"


class PostToolUseSemanticsTests(unittest.TestCase):
    """PostToolUse can only report and require follow-up."""

    def init_repo(self, cwd: Path) -> None:
        subprocess.run(["git", "init"], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        subprocess.run(["git", "config", "user.name", "Hook Test"], cwd=cwd, check=True)
        subprocess.run(["git", "config", "user.email", "hook@test.local"], cwd=cwd, check=True)
        (cwd / "README.md").write_text("# demo\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=cwd, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

    def test_secret_feedback_says_tool_already_ran(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            (cwd / "src").mkdir()
            (cwd / "src" / "leak.py").write_text(f"TOKEN='{secret_fixture()}'\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(RUNTIME), "post-tool-use", "--host", "codex", "--route", "edit"],
                cwd=cwd,
                input=json.dumps({"tool_input": {"file_path": "src/leak.py"}}),
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            security_state = json.loads((cwd / "tasks" / "loops" / "security-required.json").read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stderr)
        self.assertEqual(payload["action"], "feedback_block")
        self.assertEqual(payload["effect"], "tool_already_ran_followup_required")
        self.assertEqual(payload["hookSpecificOutput"]["hookEventName"], "PostToolUse")
        self.assertEqual(security_state["status"], "security_required")
        self.assertIn("src/leak.py", security_state["subjects"])

    def test_shell_post_tool_use_scans_extracted_write_target(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            (cwd / "src").mkdir()
            (cwd / "src" / "leak.py").write_text(f"TOKEN='{secret_fixture()}'\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(RUNTIME), "post-tool-use", "--host", "codex", "--route", "bash"],
                cwd=cwd,
                input=json.dumps({"tool_input": {"command": "printf secret > src/leak.py"}}),
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("SecretContentGuard", result.stderr)

    def test_post_tool_use_without_paths_does_not_scan_all_changed_files(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            (cwd / "src").mkdir()
            (cwd / "src" / "leak.py").write_text(f"TOKEN='{secret_fixture()}'\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(RUNTIME), "post-tool-use", "--host", "codex", "--route", "edit"],
                cwd=cwd,
                input=json.dumps({"tool_input": {"command": "python generate.py"}}),
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((cwd / "tasks" / "loops" / "security-required.json").exists())

    def test_post_tool_use_unrelated_path_does_not_scan_agent_mirror_drift(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            (cwd / ".agents").mkdir()
            (cwd / ".codex" / "agents").mkdir(parents=True)
            (cwd / ".claude" / "agents").mkdir(parents=True)
            (cwd / "src").mkdir()
            (cwd / ".agents" / "developer.md").write_text("---\nname: developer\n---\nold\n", encoding="utf-8")
            (cwd / ".codex" / "agents" / "developer.toml").write_text("# generated\n", encoding="utf-8")
            (cwd / ".claude" / "agents" / "developer.md").write_text("# generated\n", encoding="utf-8")
            (cwd / "src" / "feature.py").write_text("print('hello')\n", encoding="utf-8")
            subprocess.run(["git", "add", ".agents", ".codex", ".claude", "src"], cwd=cwd, check=True)
            subprocess.run(["git", "commit", "-m", "base"], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            (cwd / ".agents" / "developer.md").write_text("---\nname: developer\n---\nnew\n", encoding="utf-8")
            (cwd / "src" / "feature.py").write_text("print('changed')\n", encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(RUNTIME), "post-tool-use", "--host", "codex", "--route", "edit"],
                cwd=cwd,
                input=json.dumps({"tool_input": {"file_path": "src/feature.py"}}),
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("MirrorDriftGuard", result.stderr)

    def test_post_tool_use_agent_source_path_still_warns_on_mirror_drift(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            (cwd / ".agents").mkdir()
            (cwd / ".codex" / "agents").mkdir(parents=True)
            (cwd / ".claude" / "agents").mkdir(parents=True)
            (cwd / ".agents" / "developer.md").write_text("---\nname: developer\n---\nold\n", encoding="utf-8")
            (cwd / ".codex" / "agents" / "developer.toml").write_text("# generated\n", encoding="utf-8")
            (cwd / ".claude" / "agents" / "developer.md").write_text("# generated\n", encoding="utf-8")
            subprocess.run(["git", "add", ".agents", ".codex", ".claude"], cwd=cwd, check=True)
            subprocess.run(["git", "commit", "-m", "agents"], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            (cwd / ".agents" / "developer.md").write_text("---\nname: developer\n---\nnew\n", encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(RUNTIME), "post-tool-use", "--host", "codex", "--route", "edit"],
                cwd=cwd,
                input=json.dumps({"tool_input": {"file_path": ".agents/developer.md"}}),
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("MirrorDriftGuard", result.stderr)

    def test_apply_patch_path_extraction_scans_added_file(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            (cwd / "src").mkdir()
            (cwd / "src" / "large.py").write_text("\n".join(f"print({index})" for index in range(751)) + "\n", encoding="utf-8")
            command = "*** Begin Patch\n*** Update File: src/large.py\n@@\n-print(0)\n+print(0)\n*** End Patch\n"
            result = subprocess.run(
                [sys.executable, str(RUNTIME), "post-tool-use", "--host", "codex", "--route", "edit"],
                cwd=cwd,
                input=json.dumps({"tool_input": {"command": command}}),
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        self.assertEqual(result.returncode, 0)
        self.assertIn("LineLengthGuard", result.stderr)

    def test_post_tool_batch_uses_same_diff_aware_guard_path(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            (cwd / "src").mkdir()
            (cwd / "src" / "large.py").write_text("\n".join(f"print({index})" for index in range(751)) + "\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(RUNTIME), "post-tool-batch", "--host", "codex", "--route", "default"],
                cwd=cwd,
                input=json.dumps({"tool_input": {"file_path": "src/large.py"}}),
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("LineLengthGuard", result.stderr)

    def test_failure_dedupe_suppresses_repeated_post_tool_secret_records(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            (cwd / "src").mkdir()
            (cwd / "src" / "leak.py").write_text(f"TOKEN='{secret_fixture()}'\n", encoding="utf-8")
            payload = json.dumps({"tool_input": {"file_path": "src/leak.py"}})
            first = subprocess.run(
                [sys.executable, str(RUNTIME), "post-tool-use", "--host", "codex", "--route", "edit"],
                cwd=cwd,
                input=payload,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            second = subprocess.run(
                [sys.executable, str(RUNTIME), "post-tool-use", "--host", "codex", "--route", "edit"],
                cwd=cwd,
                input=payload,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            failures = (cwd / "tasks" / "loops" / "failures.jsonl").read_text(encoding="utf-8").splitlines()
            dedupe = json.loads((cwd / "tasks" / "loops" / ".cache" / "failure-dedupe.json").read_text(encoding="utf-8"))
            guard_cache = json.loads((cwd / "tasks" / "loops" / ".cache" / "guard-cache.json").read_text(encoding="utf-8"))

        self.assertEqual(first.returncode, 2)
        self.assertEqual(second.returncode, 2)
        self.assertEqual(len(failures), 1)
        self.assertEqual(next(iter(dedupe["entries"].values()))["count"], 2)
        self.assertTrue(any(entry["result"] == "secret" for entry in guard_cache["entries"].values()))


if __name__ == "__main__":
    unittest.main()
