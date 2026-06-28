"""Contract fixtures for PreToolUse security behavior."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / ".codex" / "skills" / "apex-init-project-hooks" / "scripts" / "apex_loop.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def secret_fixtures() -> dict[str, str]:
    """Secret-like values assembled at runtime so scanners do not flag source."""

    return {
        "__OPENAI_SECRET__": "sk-" + "abcdefghijklmnopqrstuvwxyz" + "123456",
        "__GITHUB_SECRET__": "ghp_" + "abcdefghijklmnopqrstuvwxyz" + "123456",
        "__AWS_ACCESS_KEY__": "AKIA" + "ABCDEFGHIJKLMNOP",
    }


class PreToolUseSecurityTests(unittest.TestCase):
    """PreToolUse must block writes before they hit the filesystem."""

    def run_hook(self, cwd: Path, fixture: str, host: str, route: str) -> subprocess.CompletedProcess[str]:
        payload = (FIXTURES / fixture).read_text(encoding="utf-8")
        for marker, value in secret_fixtures().items():
            payload = payload.replace(marker, value)
        return subprocess.run(
            [sys.executable, str(RUNTIME), "pre-tool-use", "--host", host, "--route", route],
            cwd=cwd,
            input=payload,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def init_repo(self, cwd: Path) -> None:
        subprocess.run(["git", "init"], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        subprocess.run(["git", "config", "user.name", "Hook Test"], cwd=cwd, check=True)
        subprocess.run(["git", "config", "user.email", "hook@test.local"], cwd=cwd, check=True)
        (cwd / "README.md").write_text("# demo\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=cwd, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

    def assert_denied(self, result: subprocess.CompletedProcess[str], guard: str) -> None:
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        output = payload["hookSpecificOutput"]
        self.assertEqual(output["permissionDecision"], "deny")
        self.assertIn(guard, output["permissionDecisionReason"])

    def test_claude_write_edit_and_multiedit_secret_payloads_deny(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            for fixture in (
                "claude_pre_write_secret.json",
                "claude_pre_edit_secret.json",
                "claude_pre_multiedit_secret.json",
            ):
                result = self.run_hook(cwd, fixture, "claude", "safety-write")
                self.assert_denied(result, "SecretContentGuard")

    def test_codex_apply_patch_and_shell_write_secret_payloads_deny(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            patch_result = self.run_hook(cwd, "codex_pre_apply_patch_secret.json", "codex", "safety-write")
            shell_result = self.run_hook(cwd, "codex_pre_bash_heredoc_secret.json", "codex", "safety-shell")

        self.assert_denied(patch_result, "SecretContentGuard")
        self.assert_denied(shell_result, "SecretContentGuard")

    def test_read_and_grep_env_payloads_deny(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            read_result = self.run_hook(cwd, "claude_pre_read_env.json", "claude", "safety-read")
            grep_result = self.run_hook(cwd, "claude_pre_grep_env.json", "claude", "safety-read")

        self.assert_denied(read_result, "SecretPathGuard")
        self.assert_denied(grep_result, "SecretPathGuard")

    def test_allowed_secret_path_false_positive_cases(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            for path in (".env.example", ".env.sample", ".env.template", "docs/secrets.md", "src/secret-manager.ts"):
                payload = {"tool_name": "Read", "tool_input": {"file_path": path}}
                result = subprocess.run(
                    [sys.executable, str(RUNTIME), "pre-tool-use", "--host", "claude", "--route", "safety-read"],
                    cwd=cwd,
                    input=json.dumps(payload),
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, path + result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
