"""Contract tests for ApexPowers hook installer."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / ".codex" / "skills" / "apex-init-project-hooks" / "scripts" / "init_project_hooks.py"
PYTHON_LAUNCHER = "py -3" if os.name == "nt" else "python3"


class ApexLoopInstallerTests(unittest.TestCase):
    """Installer behavior that keeps hook files out of target projects by default."""

    def init_repo(self, cwd: Path) -> None:
        """Initialize a git repo with one base commit."""

        subprocess.run(["git", "init"], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        subprocess.run(["git", "config", "user.name", "Hook Test"], cwd=cwd, check=True)
        subprocess.run(["git", "config", "user.email", "hook@test.local"], cwd=cwd, check=True)
        (cwd / "README.md").write_text("# demo\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=cwd, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

    def installer_command(self, cwd: Path, codex_home: Path, claude_home: Path, *extra: str) -> list[str]:
        """Command line for an installer run with isolated agent homes."""

        return [
            sys.executable,
            str(INSTALLER),
            str(cwd),
            "--codex-home",
            str(codex_home),
            "--claude-home",
            str(claude_home),
            *extra,
        ]

    def run_installer(self, command: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        """Run installer and capture output."""

        return subprocess.run(
            command,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            env=env,
        )

    def test_dry_run_outputs_agent_scope_json(self) -> None:
        """Dry-run exposes agent homes and project-local state targets."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            codex_home = cwd / "agent-roots" / "codex"
            claude_home = cwd / "agent-roots" / "claude"

            result = self.run_installer(self.installer_command(cwd, codex_home, claude_home, "--json"))

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["write"])
        self.assertEqual(payload["hook_scope"], "agent")
        self.assertEqual(payload["codex_config_format"], "toml")
        self.assertEqual(Path(payload["codex_home"]), codex_home.resolve())

        planned_paths = [Path(item["path"]) if Path(item["path"]).is_absolute() else cwd / item["path"] for item in payload["results"]]
        self.assertIn(codex_home / "config.toml", planned_paths)
        self.assertIn(claude_home / "settings.json", planned_paths)
        self.assertIn(cwd / "tasks" / "loops" / ".gitkeep", planned_paths)
        self.assertIn(cwd / "tasks" / "loops" / "workflow.md", planned_paths)
        self.assertIn(cwd / "tasks" / "loops" / ".apex-manifest.json", planned_paths)
        self.assertIn(codex_home / "apex" / "manifest.json", planned_paths)

    def test_agent_home_environment_default_is_portable(self) -> None:
        """AGENT_HOME can select an isolated agent root without hard-coded user paths."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            agent_home = cwd / "shared-agent-home"
            env = {**os.environ, "AGENT_HOME": str(agent_home)}
            env.pop("CODEX_HOME", None)
            env.pop("CLAUDE_HOME", None)

            result = self.run_installer([sys.executable, str(INSTALLER), str(cwd), "--json"], env=env)
            payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(payload["codex_home"]), agent_home.resolve())
        self.assertEqual(Path(payload["claude_home"]), agent_home.resolve())

    def test_agent_scope_can_write_legacy_codex_hooks_json(self) -> None:
        """Explicit JSON mode remains available for older Codex installs."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            codex_home = cwd / "agent-roots" / "codex"
            claude_home = cwd / "agent-roots" / "claude"

            result = self.run_installer(
                self.installer_command(cwd, codex_home, claude_home, "--codex-config-format", "json", "--write", "--json")
            )
            config_text = (codex_home / "hooks.json").read_text(encoding="utf-8")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("apex_loop.py", config_text)

    def test_agent_scope_writes_hooks_outside_project(self) -> None:
        """Default installer scope writes hooks to agent homes and state to project."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            codex_home = cwd / "agent-roots" / "codex"
            claude_home = cwd / "agent-roots" / "claude"

            result = self.run_installer(self.installer_command(cwd, codex_home, claude_home, "--write", "--json"))
            config_text = (codex_home / "config.toml").read_text(encoding="utf-8")
            claude_config_text = (claude_home / "settings.json").read_text(encoding="utf-8")
            codex_runtime_exists = (codex_home / "hooks" / "apex_loop.py").is_file()
            claude_runtime_exists = (claude_home / "hooks" / "apex_loop.py").is_file()
            project_state_exists = (cwd / "tasks" / "loops" / ".gitkeep").is_file()
            workflow_exists = (cwd / "tasks" / "loops" / "workflow.md").is_file()
            project_manifest = json.loads((cwd / "tasks" / "loops" / ".apex-manifest.json").read_text(encoding="utf-8"))
            codex_manifest_exists = (codex_home / "apex" / "manifest.json").is_file()
            claude_manifest_exists = (claude_home / "apex" / "manifest.json").is_file()
            project_hook_config_exists = (cwd / ".codex" / "hooks.json").exists()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(codex_runtime_exists)
        self.assertTrue(claude_runtime_exists)
        self.assertTrue(project_state_exists)
        self.assertTrue(workflow_exists)
        self.assertTrue(codex_manifest_exists)
        self.assertTrue(claude_manifest_exists)
        self.assertFalse(project_hook_config_exists)
        self.assertIn((codex_home / "hooks" / "apex_loop.py").resolve().as_posix(), config_text)
        self.assertIn((claude_home / "hooks" / "apex_loop.py").resolve().as_posix(), claude_config_text)
        self.assertIn(f'{PYTHON_LAUNCHER} \\"', config_text)
        self.assertIn(f'{PYTHON_LAUNCHER} \\"', claude_config_text)
        self.assertNotIn('command = "python \\"', config_text)
        self.assertIn("# >>> apex-managed-hooks-begin", config_text)
        self.assertEqual(project_manifest["managed_by"], "Generated by ApexPowers apex-init-project-hooks")
        self.assertEqual(project_manifest["codex_config_format"], "toml")
        self.assertIn("workflow", {item["kind"] for item in project_manifest["files"]})
        self.assertIn("host-config", {item["kind"] for item in project_manifest["files"]})
        self.assertTrue(project_manifest["files"])
        self.assertTrue(all(re.fullmatch(r"[0-9a-f]{64}", item["hash"]) for item in project_manifest["files"]))

    def test_project_scope_keeps_legacy_project_paths(self) -> None:
        """Project hook scope remains available for legacy project-local installs."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)

            result = self.run_installer(
                [
                    sys.executable,
                    str(INSTALLER),
                    str(cwd),
                    "--hook-scope",
                    "project",
                    "--write",
                    "--json",
                ]
            )
            config_text = (cwd / ".codex" / "hooks.json").read_text(encoding="utf-8")
            project_runtime_exists = (cwd / ".codex" / "hooks" / "apex_loop.py").is_file()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(project_runtime_exists)
        self.assertIn(".codex/hooks/apex_loop.py", config_text)

    def test_merges_existing_host_config(self) -> None:
        """Installer preserves hand-written hooks while adding Apex hooks."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            codex_home = cwd / "agent-roots" / "codex"
            claude_home = cwd / "agent-roots" / "claude"
            config_path = codex_home / "config.toml"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(self.existing_toml_config(), encoding="utf-8")

            result = self.run_installer(self.installer_command(cwd, codex_home, claude_home, "--write", "--json"))
            config_text = config_path.read_text(encoding="utf-8")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('custom = true', config_text)
        self.assertIn("python custom.py", config_text)
        self.assertIn("python same-entry-custom.py", config_text)
        self.assertNotIn("old --host codex", config_text)
        self.assertIn("apex_loop.py", config_text)
        self.assertEqual(config_text.count("# >>> apex-managed-hooks-begin"), 1)

    def test_claude_settings_merge_preserves_user_hooks(self) -> None:
        """Claude Code settings keep user hooks while receiving Apex hooks."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            codex_home = cwd / "agent-roots" / "codex"
            claude_home = cwd / "agent-roots" / "claude"
            config_path = claude_home / "settings.json"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(self.existing_config(), encoding="utf-8")

            result = self.run_installer(self.installer_command(cwd, codex_home, claude_home, "--write", "--json"))
            config = json.loads(config_path.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(config["custom"], True)
        self.assertNotIn("_generated_by", config)
        self.assertIn("python custom.py", json.dumps(config))
        self.assertIn("python same-entry-custom.py", json.dumps(config))
        self.assertNotIn("old --host codex", json.dumps(config))
        self.assertIn("apex_loop.py", json.dumps(config))

    def test_invalid_codex_toml_is_not_modified(self) -> None:
        """Invalid Codex config.toml is skipped instead of being corrupted."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            codex_home = cwd / "agent-roots" / "codex"
            claude_home = cwd / "agent-roots" / "claude"
            config_path = codex_home / "config.toml"
            config_path.parent.mkdir(parents=True)
            config_path.write_text("[[hooks.SessionStart]\n", encoding="utf-8")

            result = self.run_installer(self.installer_command(cwd, codex_home, claude_home, "--write", "--json"))
            payload = json.loads(result.stdout)
            config_text = config_path.read_text(encoding="utf-8")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(config_text, "[[hooks.SessionStart]\n")
        self.assertIn(
            "skip-existing",
            {item["action"] for item in payload["results"] if item["path"].replace("\\", "/").endswith("agent-roots/codex/config.toml")},
        )

    def test_merge_is_idempotent(self) -> None:
        """Repeated installer writes do not duplicate Apex hook entries."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            codex_home = cwd / "agent-roots" / "codex"
            claude_home = cwd / "agent-roots" / "claude"

            first = self.run_installer(self.installer_command(cwd, codex_home, claude_home, "--write", "--json"))
            second = self.run_installer(self.installer_command(cwd, codex_home, claude_home, "--write", "--json"))
            config_text = (codex_home / "config.toml").read_text(encoding="utf-8")

        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(config_text.count("apex_loop.py"), 10)
        self.assertEqual(config_text.count("# >>> apex-managed-hooks-begin"), 1)

    def test_update_alias_reports_operation_and_keeps_manifest_idempotent(self) -> None:
        """Update is a manifest-aware reinstall and leaves clean installs unchanged."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            codex_home = cwd / "agent-roots" / "codex"
            claude_home = cwd / "agent-roots" / "claude"

            install = self.run_installer(self.installer_command(cwd, codex_home, claude_home, "--write", "--json"))
            update = self.run_installer(self.installer_command(cwd, codex_home, claude_home, "--update", "--json"))
            payload = json.loads(update.stdout)
            manifest_actions = [item["action"] for item in payload["results"] if item["kind"] == "manifest"]

        self.assertEqual(install.returncode, 0, install.stderr)
        self.assertEqual(update.returncode, 0, update.stderr)
        self.assertEqual(payload["operation"], "update")
        self.assertTrue(manifest_actions)
        self.assertTrue(all(action == "unchanged" for action in manifest_actions))

    def test_uninstall_removes_managed_files_and_preserves_user_hooks(self) -> None:
        """Manifest uninstall scrubs Apex entries but keeps user-owned hooks and notes."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            codex_home = cwd / "agent-roots" / "codex"
            claude_home = cwd / "agent-roots" / "claude"
            config_path = codex_home / "config.toml"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(self.existing_toml_config(), encoding="utf-8")

            install = self.run_installer(self.installer_command(cwd, codex_home, claude_home, "--write", "--json"))
            dry_run = self.run_installer(self.installer_command(cwd, codex_home, claude_home, "--uninstall", "--json"))
            uninstall = self.run_installer(self.installer_command(cwd, codex_home, claude_home, "--uninstall", "--write", "--json"))
            config_text = config_path.read_text(encoding="utf-8")
            workflow_exists = (cwd / "tasks" / "loops" / "workflow.md").is_file()
            lessons_exists = (cwd / "tasks" / "lessons.md").is_file()
            runtime_exists = (codex_home / "hooks" / "apex_loop.py").exists()
            project_manifest_exists = (cwd / "tasks" / "loops" / ".apex-manifest.json").exists()
            codex_manifest_exists = (codex_home / "apex" / "manifest.json").exists()
            dry_payload = json.loads(dry_run.stdout)

        self.assertEqual(install.returncode, 0, install.stderr)
        self.assertEqual(dry_run.returncode, 0, dry_run.stderr)
        self.assertEqual(uninstall.returncode, 0, uninstall.stderr)
        self.assertEqual(dry_payload["operation"], "uninstall")
        self.assertIn("scrub-managed", {item["action"] for item in dry_payload["results"]})
        self.assertIn("python custom.py", config_text)
        self.assertIn("python same-entry-custom.py", config_text)
        self.assertNotIn("apex_loop.py", config_text)
        self.assertFalse(runtime_exists)
        self.assertFalse(project_manifest_exists)
        self.assertFalse(codex_manifest_exists)
        self.assertTrue(workflow_exists)
        self.assertTrue(lessons_exists)

    def test_uninstall_uses_lf_normalized_hashes(self) -> None:
        """CRLF-only changes do not make managed runtime files look user-modified."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            codex_home = cwd / "agent-roots" / "codex"
            claude_home = cwd / "agent-roots" / "claude"

            install = self.run_installer(self.installer_command(cwd, codex_home, claude_home, "--write", "--json"))
            runtime_path = codex_home / "hooks" / "apex_loop.py"
            runtime_text = runtime_path.read_text(encoding="utf-8")
            runtime_path.write_text(runtime_text.replace("\n", "\r\n"), encoding="utf-8", newline="")
            dry_run = self.run_installer(self.installer_command(cwd, codex_home, claude_home, "--uninstall", "--json"))
            payload = json.loads(dry_run.stdout)
            runtime_actions = [
                item["action"]
                for item in payload["results"]
                if item["path"].replace("\\", "/").endswith("agent-roots/codex/hooks/apex_loop.py")
            ]

        self.assertEqual(install.returncode, 0, install.stderr)
        self.assertEqual(dry_run.returncode, 0, dry_run.stderr)
        self.assertEqual(runtime_actions, ["remove-managed"])

    def test_uninstall_keeps_manifest_when_managed_file_is_modified(self) -> None:
        """Modified managed files keep their manifest so ownership is not lost."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            codex_home = cwd / "agent-roots" / "codex"
            claude_home = cwd / "agent-roots" / "claude"

            install = self.run_installer(self.installer_command(cwd, codex_home, claude_home, "--write", "--json"))
            runtime_path = codex_home / "hooks" / "apex_loop.py"
            runtime_path.write_text("# user modified runtime copy\n", encoding="utf-8")
            uninstall = self.run_installer(self.installer_command(cwd, codex_home, claude_home, "--uninstall", "--write", "--json"))
            payload = json.loads(uninstall.stdout)
            runtime_exists = runtime_path.exists()
            project_manifest_exists = (cwd / "tasks" / "loops" / ".apex-manifest.json").exists()
            manifest_actions = {item["action"] for item in payload["results"] if item["kind"] == "manifest"}

        self.assertEqual(install.returncode, 0, install.stderr)
        self.assertEqual(uninstall.returncode, 0, uninstall.stderr)
        self.assertTrue(runtime_exists)
        self.assertTrue(project_manifest_exists)
        self.assertIn("skip-modified", {item["action"] for item in payload["results"]})
        self.assertIn("keep-manifest", manifest_actions)

    def test_uninstall_manifest_survives_project_move(self) -> None:
        """Manifest relative paths keep uninstall usable after a project directory move."""

        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            old_root = base / "old-project"
            old_root.mkdir()
            self.init_repo(old_root)
            old_codex_home = old_root / "agent-roots" / "codex"
            old_claude_home = old_root / "agent-roots" / "claude"

            install = self.run_installer(self.installer_command(old_root, old_codex_home, old_claude_home, "--write", "--json"))
            new_root = base / "new-project"
            old_root.rename(new_root)
            new_codex_home = new_root / "agent-roots" / "codex"
            new_claude_home = new_root / "agent-roots" / "claude"

            uninstall = self.run_installer(self.installer_command(new_root, new_codex_home, new_claude_home, "--uninstall", "--json"))
            payload = json.loads(uninstall.stdout)
            actions = {item["action"] for item in payload["results"]}
            paths = [item["path"].replace("\\", "/") for item in payload["results"]]

        self.assertEqual(install.returncode, 0, install.stderr)
        self.assertEqual(uninstall.returncode, 0, uninstall.stderr)
        self.assertNotIn("skip-outside-root", actions)
        self.assertIn("remove-managed", actions)
        self.assertIn("agent-roots/codex/hooks/apex_loop.py", paths)

    def test_agent_scope_removes_generated_legacy_project_hooks(self) -> None:
        """Reinstalling after a legacy project install removes stale project hooks."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            codex_home = cwd / "agent-roots" / "codex"
            claude_home = cwd / "agent-roots" / "claude"

            legacy = self.run_installer(
                [
                    sys.executable,
                    str(INSTALLER),
                    str(cwd),
                    "--hook-scope",
                    "project",
                    "--write",
                    "--json",
                ]
            )
            reinstall = self.run_installer(self.installer_command(cwd, codex_home, claude_home, "--write", "--json"))
            payload = json.loads(reinstall.stdout)
            legacy_actions = {item["path"]: item["action"] for item in payload["results"] if item["kind"] == "legacy"}

            project_codex_config_exists = (cwd / ".codex" / "hooks.json").exists()
            project_claude_config_exists = (cwd / ".claude" / "settings.json").exists()
            project_codex_runtime_exists = (cwd / ".codex" / "hooks" / "apex_loop.py").exists()
            project_claude_runtime_exists = (cwd / ".claude" / "hooks" / "apex_loop.py").exists()
            agent_config_text = (codex_home / "config.toml").read_text(encoding="utf-8")

        self.assertEqual(legacy.returncode, 0, legacy.stderr)
        self.assertEqual(reinstall.returncode, 0, reinstall.stderr)
        self.assertFalse(project_codex_config_exists)
        self.assertFalse(project_claude_config_exists)
        self.assertFalse(project_codex_runtime_exists)
        self.assertFalse(project_claude_runtime_exists)
        self.assertEqual(agent_config_text.count("apex_loop.py"), 10)
        self.assertEqual(legacy_actions[".codex/hooks.json"], "remove-legacy")
        self.assertEqual(legacy_actions[".claude/settings.json"], "remove-legacy")

    def test_agent_scope_strips_legacy_apex_entries_but_keeps_user_hooks(self) -> None:
        """Legacy project config keeps user hooks while stale Apex entries are removed."""

        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            codex_home = cwd / "agent-roots" / "codex"
            claude_home = cwd / "agent-roots" / "claude"
            project_config = cwd / ".codex" / "hooks.json"
            project_runtime = cwd / ".codex" / "hooks" / "apex_loop.py"
            project_config.parent.mkdir(parents=True)
            project_runtime.parent.mkdir(parents=True)
            project_config.write_text(self.existing_config(), encoding="utf-8")
            project_runtime.write_text("# Runtime copy marker: Generated by ApexPowers apex-init-project-hooks.\n", encoding="utf-8")

            result = self.run_installer(self.installer_command(cwd, codex_home, claude_home, "--write", "--json"))
            project_config_text = project_config.read_text(encoding="utf-8")
            project_runtime_exists = project_runtime.exists()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("python custom.py", project_config_text)
        self.assertIn("python same-entry-custom.py", project_config_text)
        self.assertNotIn("apex_loop.py", project_config_text)
        self.assertFalse(project_runtime_exists)

    def existing_config(self) -> str:
        """Existing user hook config fixture."""

        return json.dumps(
            {
                "custom": True,
                "hooks": {
                    "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "python custom.py"}]}],
                    "PreToolUse": [
                        {
                            "matcher": "Bash",
                            "hooks": [
                                {"type": "command", "command": "python same-entry-custom.py"},
                                {"type": "command", "command": "python .codex/hooks/apex_loop.py old --host codex"},
                            ],
                        }
                    ],
                },
            },
            indent=2,
        ) + "\n"

    def existing_toml_config(self) -> str:
        """Existing user Codex config.toml fixture."""

        return """custom = true

[[hooks.SessionStart]]
[[hooks.SessionStart.hooks]]
type = "command"
command = "python custom.py"

[[hooks.PreToolUse]]
matcher = "Bash"
[[hooks.PreToolUse.hooks]]
type = "command"
command = "python same-entry-custom.py"

# >>> apex-managed-hooks-begin (Generated by ApexPowers apex-init-project-hooks) >>>
[[hooks.PreToolUse]]
matcher = "Bash"
[[hooks.PreToolUse.hooks]]
type = "command"
command = "python .codex/hooks/apex_loop.py old --host codex"
# <<< apex-managed-hooks-end <<<
"""


if __name__ == "__main__":
    unittest.main()
