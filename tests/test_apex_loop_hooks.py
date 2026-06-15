"""Contract tests for ApexPowers loop hooks."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".codex" / "skills" / "apex-init-project-hooks" / "scripts" / "apex_loop.py"


class ApexLoopHookTests(unittest.TestCase):
    """Hook runtime behavior that must stay stable for Claude and Codex."""

    def run_hook(self, cwd: Path, *args: str, payload: dict[str, object] | None = None) -> subprocess.CompletedProcess[str]:
        """Run the hook runtime in a temporary repo."""

        return subprocess.run(
            [sys.executable, str(RUNTIME), *args],
            cwd=cwd,
            input=json.dumps(payload or {}, ensure_ascii=False),
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def init_repo(self, cwd: Path) -> None:
        """Initialize a git repo with one base commit."""

        subprocess.run(["git", "init"], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        subprocess.run(["git", "config", "user.name", "Hook Test"], cwd=cwd, check=True)
        subprocess.run(["git", "config", "user.email", "hook@test.local"], cwd=cwd, check=True)
        (cwd / "README.md").write_text("# demo\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=cwd, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

    def test_render_config_contains_stable_routes(self) -> None:
        """Codex config is rendered from the route registry."""

        result = subprocess.run(
            [sys.executable, str(RUNTIME), "render-config", "codex", "--script-path", ".codex/hooks/apex_loop.py"],
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        config = json.loads(result.stdout)
        self.assertNotIn("_generated_by", config)
        self.assertNotIn("_generated_marker", config)
        self.assertIn("UserPromptSubmit", config["hooks"])
        self.assertIn("PreToolUse", config["hooks"])
        self.assertIn("PostToolUse", config["hooks"])
        self.assertIn("Stop", config["hooks"])

    def test_user_prompt_submit_is_advisory(self) -> None:
        """Prompt route hints must never block."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)

            result = self.run_hook(
                cwd,
                "user-prompt-submit",
                "--host",
                "codex",
                payload={"prompt": "review 一下当前 diff"},
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("<apex-workflow-state", result.stdout)
        self.assertIn('status="no_task"', result.stdout)
        self.assertIn("ApexLoopRoute", result.stdout)

    def test_session_start_includes_workflow_state_summary(self) -> None:
        """SessionStart context includes the inferred workflow state."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            (cwd / "tasks").mkdir()
            (cwd / "tasks" / "todo+demo.md").write_text("# Demo\n\n- [ ] Implement\n", encoding="utf-8")

            result = self.run_hook(cwd, "session-start", "--host", "codex", payload={})
            payload = json.loads(result.stdout)
            context_text = payload["hookSpecificOutput"]["additionalContext"]

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Workflow state: planning", context_text)

    def test_workflow_state_uses_custom_workflow_block(self) -> None:
        """Editable workflow.md blocks are injected for the inferred state."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            (cwd / "src").mkdir()
            (cwd / "src" / "feature.py").write_text("print('hello')\n", encoding="utf-8")
            (cwd / "tasks" / "loops").mkdir(parents=True)
            (cwd / "tasks" / "todo+demo.md").write_text("# Demo\n\n- [ ] Implement\n", encoding="utf-8")
            (cwd / "tasks" / "loops" / "workflow.md").write_text(
                "# Workflow\n\n[apex-state:review_required]\nCUSTOM REVIEW BLOCK\n[/apex-state:review_required]\n",
                encoding="utf-8",
            )

            result = self.run_hook(cwd, "user-prompt-submit", "--host", "codex", payload={"prompt": "继续"})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('status="review_required"', result.stdout)
        self.assertIn("CUSTOM REVIEW BLOCK", result.stdout)

    def test_workflow_state_detects_validation_required(self) -> None:
        """Ready reviews without validation move the workflow into validation_required."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            (cwd / "src").mkdir()
            (cwd / "src" / "feature.py").write_text("print('hello')\n", encoding="utf-8")
            (cwd / "tasks" / "reviews").mkdir(parents=True)
            (cwd / "tasks" / "todo+demo.md").write_text("# Demo\n\n- [ ] Implement\n", encoding="utf-8")
            (cwd / "tasks" / "reviews" / "demo.md").write_text("# Review\n\n> **Status**: Ready\n", encoding="utf-8")

            result = self.run_hook(cwd, "user-prompt-submit", "--host", "codex", payload={"prompt": "完成了吗"})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('status="validation_required"', result.stdout)

    def test_pre_tool_use_blocks_dangerous_git(self) -> None:
        """Dangerous destructive commands fail closed."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)

            result = self.run_hook(
                cwd,
                "pre-tool-use",
                "--host",
                "codex",
                "--route",
                "safety",
                payload={"tool_input": {"command": "git reset --hard HEAD~1"}},
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("SecurityGuard", result.stderr)
        self.assertIn("security_risk", result.stderr)

    def test_pre_tool_use_dangerous_and_normal_command_fixtures(self) -> None:
        """Dangerous deletes block while normal test commands pass."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)

            rm_result = self.run_hook(cwd, "pre-tool-use", "--host", "codex", "--route", "safety", payload={"tool_input": {"command": "rm -rf /"}})
            npm_result = self.run_hook(cwd, "pre-tool-use", "--host", "codex", "--route", "safety", payload={"tool_input": {"command": "npm test"}})

        self.assertEqual(rm_result.returncode, 2)
        self.assertIn("SecurityGuard", rm_result.stderr)
        self.assertEqual(npm_result.returncode, 0, npm_result.stderr)

    def test_post_tool_use_blocks_oversized_source_file(self) -> None:
        """LineLengthGuard blocks source files beyond the hard limit."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            source = cwd / "src" / "large.py"
            source.parent.mkdir()
            source.write_text("\n".join(f"print({index})" for index in range(501)) + "\n", encoding="utf-8")

            result = self.run_hook(
                cwd,
                "post-tool-use",
                "--host",
                "codex",
                "--route",
                "edit",
                payload={"tool_input": {"file_path": "src/large.py"}},
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("LineLengthGuard", result.stderr)
        self.assertIn("quality_gate", result.stderr)

    def test_line_length_threshold_fixtures(self) -> None:
        """LineLengthGuard allows, warns, and exempts the planned cases."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            src = cwd / "src"
            src.mkdir()
            ok_file = src / "ok.py"
            warn_file = src / "warn.py"
            generated_file = src / "generated_client.py"
            ok_file.write_text("\n".join(f"print({index})" for index in range(299)) + "\n", encoding="utf-8")
            warn_file.write_text("\n".join(f"print({index})" for index in range(401)) + "\n", encoding="utf-8")
            generated_file.write_text("\n".join(f"print({index})" for index in range(650)) + "\n", encoding="utf-8")

            ok_result = self.run_hook(cwd, "post-tool-use", "--host", "codex", "--route", "edit", payload={"tool_input": {"file_path": "src/ok.py"}})
            warn_result = self.run_hook(cwd, "post-tool-use", "--host", "codex", "--route", "edit", payload={"tool_input": {"file_path": "src/warn.py"}})
            generated_result = self.run_hook(cwd, "post-tool-use", "--host", "codex", "--route", "edit", payload={"tool_input": {"file_path": "src/generated_client.py"}})

        self.assertEqual(ok_result.returncode, 0, ok_result.stderr)
        self.assertEqual(warn_result.returncode, 0, warn_result.stderr)
        self.assertIn("LineLengthGuard", warn_result.stderr)
        self.assertEqual(generated_result.returncode, 0, generated_result.stderr)
        self.assertNotIn("LineLengthGuard", generated_result.stderr)

    def test_pre_tool_use_blocks_secret_path(self) -> None:
        """Secret-like paths fail closed."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)

            result = self.run_hook(
                cwd,
                "pre-tool-use",
                "--host",
                "codex",
                "--route",
                "safety",
                payload={"tool_input": {"file_path": ".env"}},
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("SecretPathGuard", result.stderr)

    def test_pre_tool_use_allows_secret_substrings_in_normal_names(self) -> None:
        """Secret path detection does not block tokenizer-like filenames."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)

            result = self.run_hook(
                cwd,
                "pre-tool-use",
                "--host",
                "codex",
                "--route",
                "safety",
                payload={"tool_input": {"file_path": "src/tokenizer.py"}},
            )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_post_tool_use_blocks_secret_content(self) -> None:
        """Secret-looking file contents fail closed after writes."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            source = cwd / "src" / "leak.py"
            source.parent.mkdir()
            source.write_text("TOKEN = 'sk-abcdefghijklmnopqrstuvwxyz123456'\n", encoding="utf-8")

            result = self.run_hook(
                cwd,
                "post-tool-use",
                "--host",
                "codex",
                "--route",
                "edit",
                payload={"tool_input": {"file_path": "src/leak.py"}},
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("SecretContentGuard", result.stderr)

    def test_stop_blocks_agent_mirror_drift(self) -> None:
        """Modified .agents source without mirror changes blocks Stop."""

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

            result = self.run_hook(cwd, "stop", "--host", "codex", "--route", "default", payload={})

        self.assertEqual(result.returncode, 2)
        self.assertIn("MirrorDriftGuard", result.stdout)

    def test_mirror_drift_passes_when_mirrors_change_together(self) -> None:
        """Mirror drift is clear when source and mirrors are changed together."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            (cwd / ".agents").mkdir()
            (cwd / ".codex" / "agents").mkdir(parents=True)
            (cwd / ".claude" / "agents").mkdir(parents=True)
            (cwd / ".agents" / "developer.md").write_text("---\nname: developer\n---\nold\n", encoding="utf-8")
            (cwd / ".codex" / "agents" / "developer.toml").write_text("# old\n", encoding="utf-8")
            (cwd / ".claude" / "agents" / "developer.md").write_text("# old\n", encoding="utf-8")
            subprocess.run(["git", "add", ".agents", ".codex", ".claude"], cwd=cwd, check=True)
            subprocess.run(["git", "commit", "-m", "agents"], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            (cwd / ".agents" / "developer.md").write_text("---\nname: developer\n---\nnew\n", encoding="utf-8")
            (cwd / ".codex" / "agents" / "developer.toml").write_text("# new\n", encoding="utf-8")
            (cwd / ".claude" / "agents" / "developer.md").write_text("# new\n", encoding="utf-8")

            result = self.run_hook(cwd, "stop", "--host", "codex", "--route", "default", payload={})

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_stop_creates_review_request_for_code_diff(self) -> None:
        """Stop gate creates a review request and blocks completion."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            (cwd / "src").mkdir()
            (cwd / "src" / "feature.py").write_text("print('hello')\n", encoding="utf-8")
            (cwd / "tasks").mkdir()
            (cwd / "tasks" / "todo+demo.md").write_text("# Demo\n\n- [ ] Implement\n", encoding="utf-8")

            result = self.run_hook(cwd, "stop", "--host", "codex", "--route", "default", payload={})
            review_path = cwd / "tasks" / "reviews" / "demo.md"
            state_path = cwd / "tasks" / "loops" / "demo" / "state.json"

            self.assertTrue(review_path.exists())
            review_text = review_path.read_text(encoding="utf-8")
            state = json.loads(state_path.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["decision"], "block")
        self.assertIn("ReviewGate", result.stdout)
        self.assertIn("Status**: Pending", review_text)
        self.assertEqual(state["phase"], "review_required")

    def test_stop_respects_review_ready_and_critical_states(self) -> None:
        """Review ready allows Stop while Critical findings block it."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            (cwd / "src").mkdir()
            (cwd / "src" / "feature.py").write_text("print('hello')\n", encoding="utf-8")
            (cwd / "tasks" / "reviews").mkdir(parents=True)
            (cwd / "tasks" / "todo+demo.md").write_text("# Demo\n\n- [ ] Implement\n", encoding="utf-8")
            review_path = cwd / "tasks" / "reviews" / "demo.md"

            review_path.write_text("# Review\n\n> **Status**: Ready\n> **Validation**: Pass\n\n## Scope\n\n- `src/feature.py`\n", encoding="utf-8")
            ready_result = self.run_hook(cwd, "stop", "--host", "codex", "--route", "default", payload={})

            review_path.write_text("# Review\n\n- Critical: fix this\n", encoding="utf-8")
            critical_result = self.run_hook(cwd, "stop", "--host", "codex", "--route", "default", payload={})

        self.assertEqual(ready_result.returncode, 0, ready_result.stdout + ready_result.stderr)
        self.assertEqual(critical_result.returncode, 2)
        self.assertIn("ReviewGate", critical_result.stdout)

    def test_stop_blocks_stale_ready_review_after_new_code_diff(self) -> None:
        """Ready reviews do not cover code changes made after review evidence."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            (cwd / "src").mkdir()
            (cwd / "tasks" / "reviews").mkdir(parents=True)
            (cwd / "tasks" / "todo+demo.md").write_text("# Demo\n\n- [ ] Implement\n", encoding="utf-8")
            (cwd / "tasks" / "reviews" / "demo.md").write_text(
                "# Review\n\n> **Status**: Ready\n> **Validation**: Pass\n\n## Scope\n\n- `src/feature.py`\n",
                encoding="utf-8",
            )
            time.sleep(0.05)
            (cwd / "src" / "feature.py").write_text("print('changed after review')\n", encoding="utf-8")

            result = self.run_hook(cwd, "stop", "--host", "codex", "--route", "default", payload={})

        self.assertEqual(result.returncode, 2)
        self.assertIn("ReviewGate", result.stdout)

    def test_stop_requires_validation_after_review_ready(self) -> None:
        """Ready review without validation evidence still blocks Stop."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            (cwd / "src").mkdir()
            (cwd / "src" / "feature.py").write_text("print('hello')\n", encoding="utf-8")
            (cwd / "tasks" / "reviews").mkdir(parents=True)
            (cwd / "tasks" / "todo+demo.md").write_text("# Demo\n\n- [ ] Implement\n", encoding="utf-8")
            (cwd / "tasks" / "reviews" / "demo.md").write_text("# Review\n\n> **Status**: Ready\n", encoding="utf-8")

            result = self.run_hook(cwd, "stop", "--host", "codex", "--route", "default", payload={})

        self.assertEqual(result.returncode, 2)
        self.assertIn("ValidationGate", result.stdout)

    def test_stop_ignores_todo_only_changes(self) -> None:
        """Todo-only planning does not trigger review gate."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            (cwd / "tasks").mkdir()
            (cwd / "tasks" / "todo+planning.md").write_text("# Planning\n\n- [ ] Decide\n", encoding="utf-8")

            result = self.run_hook(cwd, "stop", "--host", "codex", "--route", "default", payload={})

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

if __name__ == "__main__":
    unittest.main()
