"""Contract tests for ApexPowers loop hooks."""

from __future__ import annotations

import json
import hashlib
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".codex" / "skills" / "apex-init-project-hooks" / "scripts" / "apex_loop.py"
PYTHON_LAUNCHER = "py -3" if os.name == "nt" else "python3"


def secret_fixture() -> str:
    """Secret-like token assembled at runtime so scanners do not flag source."""

    return "sk-" + "abcdefghijklmnopqrstuvwxyz" + "123456"


def review_frontmatter(slug: str, file_hashes: dict[str, str], validation: str = "pass", role: str = "independent-agent") -> str:
    """Structured review frontmatter for hook tests."""

    payload = json.dumps(file_hashes, sort_keys=True, separators=(",", ":"))
    diff_hash = "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()
    hash_lines = "\n".join(f'  "{path}": "{digest}"' for path, digest in sorted(file_hashes.items()))
    return f"""---
schema_version: 1
task_id: "{slug}"
slug: "{slug}"
status: ready
validation: {validation}
reviewed_diff_hash: "{diff_hash}"
risk_level: medium
reviewer:
  role: {role}
implementer:
  id: ""
reviewed_file_hashes:
{hash_lines}
validation_evidence:
  required_checks:
    - name: tests
      command: manual
      exit_code: 0
      recorded_at: now
findings: []
---

# Review
"""


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
        """Legacy Codex JSON config is rendered from the route registry."""

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
        self.assertIn("PostToolBatch", config["hooks"])
        self.assertIn("PreCompact", config["hooks"])
        self.assertIn("Stop", config["hooks"])
        self.assertEqual(len(config["hooks"]["PostToolUse"]), 3)
        self.assertEqual(config["hooks"]["PostToolUse"][0]["matcher"], "Edit|Write|MultiEdit|apply_patch")
        self.assertEqual(config["hooks"]["PostToolUse"][1]["matcher"], "Bash|Shell|PowerShell")
        self.assertNotIn("matcher", config["hooks"]["PostToolUse"][2])
        self.assertEqual(len(config["hooks"]["PostToolBatch"]), 1)
        command = config["hooks"]["SessionStart"][0]["hooks"][0]["command"]
        self.assertTrue(command.startswith(f'{PYTHON_LAUNCHER} ".codex/hooks/apex_loop.py"'), command)

    def test_render_codex_toml_config_contains_stable_routes(self) -> None:
        """Codex TOML config is rendered from the route registry."""

        result = subprocess.run(
            [
                sys.executable,
                str(RUNTIME),
                "render-config",
                "codex",
                "--script-path",
                ".codex/hooks/apex_loop.py",
                "--config-format",
                "toml",
            ],
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("# >>> apex-managed-hooks-begin", result.stdout)
        self.assertIn("[[hooks.UserPromptSubmit]]", result.stdout)
        self.assertIn("[[hooks.PreToolUse]]", result.stdout)
        self.assertIn("[[hooks.PostToolUse]]", result.stdout)
        self.assertIn("[[hooks.PostToolBatch]]", result.stdout)
        self.assertIn("[[hooks.PreCompact]]", result.stdout)
        self.assertIn("[[hooks.Stop]]", result.stdout)
        self.assertIn('--host codex --route ', result.stdout)
        self.assertIn(f'command = "{PYTHON_LAUNCHER} \\".codex/hooks/apex_loop.py\\"', result.stdout)
        self.assertNotIn('command = "python \\".codex/hooks/apex_loop.py\\"', result.stdout)

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
            (cwd / "tasks" / "todo+demo.md").write_text("# Demo\n\n- [x] Implement\n", encoding="utf-8")

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
            (cwd / "tasks" / "todo+demo.md").write_text("# Demo\n\n- [x] Implement\n", encoding="utf-8")
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
            (cwd / "tasks" / "todo+demo.md").write_text("# Demo\n\n- [x] Implement\n", encoding="utf-8")
            (cwd / "tasks" / "reviews" / "demo.md").write_text(
                """+++
schema_version = 1
task_id = "demo"
slug = "demo"
status = "ready"
validation = "missing"
risk_level = "medium"

[reviewer]
role = "independent-agent"
+++

# Review
""",
                encoding="utf-8",
            )

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
                "safety-shell",
                payload={"tool_input": {"command": "git reset --hard HEAD~1"}},
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("SecurityGuard", result.stdout)
        self.assertIn("permissionDecision", result.stdout)

    def test_pre_tool_use_dangerous_and_normal_command_fixtures(self) -> None:
        """Dangerous deletes block while normal test commands pass."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)

            rm_result = self.run_hook(cwd, "pre-tool-use", "--host", "codex", "--route", "safety-shell", payload={"tool_input": {"command": "rm -rf /"}})
            npm_result = self.run_hook(cwd, "pre-tool-use", "--host", "codex", "--route", "safety-shell", payload={"tool_input": {"command": "npm test"}})

        self.assertEqual(rm_result.returncode, 2)
        self.assertIn("SecurityGuard", rm_result.stdout)
        self.assertEqual(npm_result.returncode, 0, npm_result.stderr)

    def test_post_tool_use_warns_oversized_source_file(self) -> None:
        """PostToolUse warns on oversized files without blocking the tool loop."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            source = cwd / "src" / "large.py"
            source.parent.mkdir()
            source.write_text("\n".join(f"print({index})" for index in range(751)) + "\n", encoding="utf-8")

            result = self.run_hook(
                cwd,
                "post-tool-use",
                "--host",
                "codex",
                "--route",
                "edit",
                payload={"tool_input": {"file_path": "src/large.py"}},
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("LineLengthGuard", result.stderr)
        self.assertIn("quality_gate", result.stderr)

    def test_stop_blocks_oversized_source_file(self) -> None:
        """Stop gate blocks files beyond their type-aware hard limit."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            source = cwd / "src" / "large.py"
            source.parent.mkdir()
            source.write_text("\n".join(f"print({index})" for index in range(751)) + "\n", encoding="utf-8")

            result = self.run_hook(cwd, "stop", "--host", "codex", "--route", "default", payload={})

        self.assertEqual(result.returncode, 2)
        self.assertIn("LineLengthGuard", result.stdout)
        self.assertIn("backend module", result.stdout)

    def test_stop_warns_old_oversized_source_file_without_blocking(self) -> None:
        """Old oversized files do not hard-block when they were already oversized at HEAD."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            source = cwd / "src" / "large.py"
            source.parent.mkdir()
            source.write_text("\n".join(f"print({index})" for index in range(751)) + "\n", encoding="utf-8")
            subprocess.run(["git", "add", "src/large.py"], cwd=cwd, check=True)
            subprocess.run(["git", "commit", "-m", "large"], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            source.write_text(source.read_text(encoding="utf-8") + "print('small change')\n", encoding="utf-8")

            result = self.run_hook(cwd, "stop", "--host", "codex", "--route", "default", payload={})

        self.assertNotIn("LineLengthGuard", result.stdout)

    def test_line_length_threshold_fixtures(self) -> None:
        """LineLengthGuard allows, warns, and exempts the planned cases."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            src = cwd / "src"
            src.mkdir()
            ok_file = src / "ok.py"
            warn_file = src / "warn.py"
            frontend_block_file = src / "Widget.tsx"
            generated_file = src / "generated_client.py"
            ok_file.write_text("\n".join(f"print({index})" for index in range(299)) + "\n", encoding="utf-8")
            warn_file.write_text("\n".join(f"print({index})" for index in range(451)) + "\n", encoding="utf-8")
            frontend_block_file.write_text("\n".join(f"export const item{index} = {index};" for index in range(501)) + "\n", encoding="utf-8")
            generated_file.write_text("\n".join(f"print({index})" for index in range(650)) + "\n", encoding="utf-8")

            ok_result = self.run_hook(cwd, "post-tool-use", "--host", "codex", "--route", "edit", payload={"tool_input": {"file_path": "src/ok.py"}})
            warn_result = self.run_hook(cwd, "post-tool-use", "--host", "codex", "--route", "edit", payload={"tool_input": {"file_path": "src/warn.py"}})
            frontend_result = self.run_hook(cwd, "post-tool-use", "--host", "codex", "--route", "edit", payload={"tool_input": {"file_path": "src/Widget.tsx"}})
            generated_result = self.run_hook(cwd, "post-tool-use", "--host", "codex", "--route", "edit", payload={"tool_input": {"file_path": "src/generated_client.py"}})

        self.assertEqual(ok_result.returncode, 0, ok_result.stderr)
        self.assertEqual(warn_result.returncode, 0, warn_result.stderr)
        self.assertIn("LineLengthGuard", warn_result.stderr)
        self.assertIn("backend module", warn_result.stderr)
        self.assertEqual(frontend_result.returncode, 0, frontend_result.stderr)
        self.assertIn("frontend component", frontend_result.stderr)
        self.assertIn("Stop gate", frontend_result.stderr)
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
                "safety-read",
                payload={"tool_input": {"file_path": ".env"}},
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("SecretPathGuard", result.stdout)

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
                "safety-read",
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
            source.write_text(f"TOKEN = '{secret_fixture()}'\n", encoding="utf-8")

            result = self.run_hook(
                cwd,
                "post-tool-use",
                "--host",
                "codex",
                "--route",
                "bash",
                payload={"tool_input": {"file_path": "src/leak.py"}},
            )
            security_state = cwd / "tasks" / "loops" / "security-required.json"
            security_payload = json.loads(security_state.read_text(encoding="utf-8"))
            workflow_result = self.run_hook(cwd, "user-prompt-submit", "--host", "codex", payload={"prompt": "继续"})
            stop_result = self.run_hook(cwd, "stop", "--host", "codex", "--route", "default", payload={})

        self.assertEqual(result.returncode, 2)
        self.assertIn("SecretContentGuard", result.stderr)
        self.assertIn("tool_already_ran_followup_required", result.stderr)
        self.assertEqual(security_payload["status"], "security_required")
        self.assertIn("src/leak.py", security_payload["subjects"])
        self.assertIn('status="security_required"', workflow_result.stdout)
        self.assertEqual(stop_result.returncode, 2)
        self.assertIn("security_required", stop_result.stdout)

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
            (cwd / "tasks" / "todo+demo.md").write_text("# Demo\n\n- [x] Implement\n", encoding="utf-8")

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

    def test_stop_blocks_unfinished_contract_checklist_before_review(self) -> None:
        """ContractGate blocks completion while active todo checklist items remain open."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            (cwd / "src").mkdir()
            (cwd / "src" / "feature.py").write_text("print('hello')\n", encoding="utf-8")
            (cwd / "tasks").mkdir()
            (cwd / "tasks" / "todo+demo.md").write_text("# Demo\n\n- [ ] Implement all slices\n", encoding="utf-8")

            result = self.run_hook(cwd, "stop", "--host", "codex", "--route", "default", payload={})
            review_exists = (cwd / "tasks" / "reviews" / "demo.md").exists()

        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["decision"], "block")
        self.assertIn("ContractGate", result.stdout)
        self.assertIn("Implement all slices", result.stdout)
        self.assertFalse(review_exists)

    def test_stop_blocks_ambiguous_todos_without_active_state(self) -> None:
        """ReviewGate does not bind code changes to the newest todo when task state is ambiguous."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            (cwd / "src").mkdir()
            (cwd / "src" / "feature.py").write_text("print('hello')\n", encoding="utf-8")
            (cwd / "tasks").mkdir()
            (cwd / "tasks" / "todo+alpha.md").write_text("# Alpha\n\n- [x] Implement\n", encoding="utf-8")
            (cwd / "tasks" / "todo+beta.md").write_text("# Beta\n\n- [x] Implement\n", encoding="utf-8")

            result = self.run_hook(cwd, "stop", "--host", "codex", "--route", "default", payload={})
            beta_review_exists = (cwd / "tasks" / "reviews" / "beta.md").exists()

        self.assertEqual(result.returncode, 2)
        self.assertIn("ambiguous_task", result.stdout)
        self.assertFalse(beta_review_exists)

    def test_stop_uses_active_loop_state_when_multiple_todos_exist(self) -> None:
        """Loop state selects the review slug when multiple todo files exist."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            (cwd / "src").mkdir()
            (cwd / "src" / "feature.py").write_text("print('hello')\n", encoding="utf-8")
            (cwd / "tasks" / "loops" / "alpha").mkdir(parents=True)
            (cwd / "tasks" / "todo+alpha.md").write_text("# Alpha\n\n- [x] Implement\n", encoding="utf-8")
            (cwd / "tasks" / "todo+beta.md").write_text("# Beta\n\n- [x] Implement\n", encoding="utf-8")
            (cwd / "tasks" / "loops" / "alpha" / "state.json").write_text(
                json.dumps({"phase": "implementing", "todo_path": "tasks/todo+alpha.md"}),
                encoding="utf-8",
            )

            result = self.run_hook(cwd, "stop", "--host", "codex", "--route", "default", payload={})
            alpha_review_exists = (cwd / "tasks" / "reviews" / "alpha.md").exists()
            beta_review_exists = (cwd / "tasks" / "reviews" / "beta.md").exists()

        self.assertEqual(result.returncode, 2)
        self.assertTrue(alpha_review_exists)
        self.assertFalse(beta_review_exists)

    def test_stop_uses_active_json_owned_paths_when_multiple_todos_exist(self) -> None:
        """active.json owned_paths selects the review slug in parallel task scenarios."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            (cwd / "src" / "alpha").mkdir(parents=True)
            (cwd / "src" / "alpha" / "feature.py").write_text("print('alpha')\n", encoding="utf-8")
            (cwd / "tasks" / "loops").mkdir(parents=True)
            (cwd / "tasks" / "todo+alpha.md").write_text("# Alpha\n\n- [x] Implement\n", encoding="utf-8")
            (cwd / "tasks" / "todo+beta.md").write_text("# Beta\n\n- [x] Implement\n", encoding="utf-8")
            (cwd / "tasks" / "loops" / "active.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "active_tasks": [
                            {
                                "task_id": "alpha",
                                "slug": "alpha",
                                "todo_path": "tasks/todo+alpha.md",
                                "review_path": "tasks/reviews/alpha.md",
                                "owned_paths": ["src/alpha/**"],
                                "risk_level": "medium",
                                "status": "active",
                            },
                            {
                                "task_id": "beta",
                                "slug": "beta",
                                "todo_path": "tasks/todo+beta.md",
                                "review_path": "tasks/reviews/beta.md",
                                "owned_paths": ["src/beta/**"],
                                "risk_level": "medium",
                                "status": "active",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_hook(cwd, "stop", "--host", "codex", "--route", "default", payload={})
            alpha_review_exists = (cwd / "tasks" / "reviews" / "alpha.md").exists()
            beta_review_exists = (cwd / "tasks" / "reviews" / "beta.md").exists()

        self.assertEqual(result.returncode, 2)
        self.assertTrue(alpha_review_exists)
        self.assertFalse(beta_review_exists)

    def test_stop_allows_automated_pass_validation(self) -> None:
        """ReviewGate accepts automated-pass validation when checks passed."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            (cwd / "src").mkdir()
            feature = cwd / "src" / "feature.py"
            feature.write_text("print('hello')\n", encoding="utf-8")
            (cwd / "tasks" / "reviews").mkdir(parents=True)
            (cwd / "tasks" / "todo+demo.md").write_text("# Demo\n\n- [x] Implement\n", encoding="utf-8")
            digest = "sha256:" + hashlib.sha256(feature.read_bytes()).hexdigest()
            (cwd / "tasks" / "reviews" / "demo.md").write_text(
                review_frontmatter("demo", {"src/feature.py": digest}, validation="automated-pass"),
                encoding="utf-8",
            )

            result = self.run_hook(cwd, "stop", "--host", "codex", "--route", "default", payload={})

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_stop_blocks_same_agent_reviewer_for_medium_risk(self) -> None:
        """ReviewGate requires independent reviewer roles for normal risk."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            (cwd / "src").mkdir()
            feature = cwd / "src" / "feature.py"
            feature.write_text("print('hello')\n", encoding="utf-8")
            (cwd / "tasks" / "reviews").mkdir(parents=True)
            (cwd / "tasks" / "todo+demo.md").write_text("# Demo\n\n- [x] Implement\n", encoding="utf-8")
            digest = "sha256:" + hashlib.sha256(feature.read_bytes()).hexdigest()
            (cwd / "tasks" / "reviews" / "demo.md").write_text(
                review_frontmatter("demo", {"src/feature.py": digest}, role="same-agent"),
                encoding="utf-8",
            )

            result = self.run_hook(cwd, "stop", "--host", "codex", "--route", "default", payload={})

        self.assertEqual(result.returncode, 2)
        self.assertIn("reviewer.role", result.stdout)

    def test_stop_blocks_same_implementer_and_reviewer_id(self) -> None:
        """ReviewGate rejects a reviewer id that matches the implementer id."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            (cwd / "src").mkdir()
            feature = cwd / "src" / "feature.py"
            feature.write_text("print('hello')\n", encoding="utf-8")
            (cwd / "tasks" / "reviews").mkdir(parents=True)
            (cwd / "tasks" / "todo+demo.md").write_text("# Demo\n\n- [x] Implement\n", encoding="utf-8")
            digest = "sha256:" + hashlib.sha256(feature.read_bytes()).hexdigest()
            payload = json.dumps({"src/feature.py": digest}, sort_keys=True, separators=(",", ":"))
            diff_hash = "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()
            (cwd / "tasks" / "reviews" / "demo.md").write_text(
                f"""---
schema_version: 1
task_id: demo
slug: demo
status: ready
validation: pass
reviewed_diff_hash: "{diff_hash}"
risk_level: medium
reviewer:
  id: agent-1
  role: independent-agent
implementer:
  id: agent-1
reviewed_file_hashes:
  "src/feature.py": "{digest}"
validation_evidence:
  required_checks:
    - name: tests
      command: manual
      exit_code: 0
      recorded_at: now
findings: []
---

# Review
""",
                encoding="utf-8",
            )

            result = self.run_hook(cwd, "stop", "--host", "codex", "--route", "default", payload={})

        self.assertEqual(result.returncode, 2)
        self.assertIn("reviewer.role", result.stdout)

    def test_stop_hook_active_reports_blocked_status_without_new_gate(self) -> None:
        """Stop hook recursion guard lets the turn end as blocked without creating more work."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            (cwd / "src").mkdir()
            (cwd / "src" / "large.py").write_text("\n".join(f"print({index})" for index in range(751)) + "\n", encoding="utf-8")

            blocked = self.run_hook(cwd, "stop", "--host", "codex", "--route", "default", payload={})
            result = self.run_hook(cwd, "stop", "--host", "codex", "--route", "default", payload={"stop_hook_active": True})
            payload = json.loads(result.stdout)
            state = json.loads((cwd / "tasks" / "loops" / "session" / "state.json").read_text(encoding="utf-8"))

        self.assertEqual(blocked.returncode, 2)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(payload["status"], "blocked")
        self.assertIn("not done", payload["reason"])
        self.assertEqual(state["continuation_count"], 1)
        self.assertEqual(state["max_continuations"], 0)
        self.assertIn("last_block_reason_hash", state)

    def test_stop_respects_review_ready_and_critical_states(self) -> None:
        """Review ready allows Stop while Critical findings block it."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            (cwd / "src").mkdir()
            (cwd / "src" / "feature.py").write_text("print('hello')\n", encoding="utf-8")
            (cwd / "tasks" / "reviews").mkdir(parents=True)
            (cwd / "tasks" / "todo+demo.md").write_text("# Demo\n\n- [x] Implement\n", encoding="utf-8")
            review_path = cwd / "tasks" / "reviews" / "demo.md"

            feature = cwd / "src" / "feature.py"
            digest = "sha256:" + hashlib.sha256(feature.read_bytes()).hexdigest()
            review_path.write_text(review_frontmatter("demo", {"src/feature.py": digest}), encoding="utf-8")
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
            (cwd / "tasks" / "todo+demo.md").write_text("# Demo\n\n- [x] Implement\n", encoding="utf-8")
            (cwd / "tasks" / "reviews" / "demo.md").write_text(
                review_frontmatter("demo", {"src/feature.py": "sha256:stale"}),
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
            (cwd / "tasks" / "todo+demo.md").write_text("# Demo\n\n- [x] Implement\n", encoding="utf-8")
            (cwd / "tasks" / "reviews" / "demo.md").write_text(
                """+++
schema_version = 1
task_id = "demo"
slug = "demo"
status = "ready"
validation = "missing"
risk_level = "medium"

[reviewer]
role = "independent-agent"
+++

# Review
""",
                encoding="utf-8",
            )

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
