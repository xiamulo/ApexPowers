"""Tests for the ApexPowers apex CLI."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "src" / "apexpowers_cli" / "cli.py"


class ApexCliTests(unittest.TestCase):
    """Profile install, lifecycle, and pack behavior."""

    def run_apex(self, *args: str) -> subprocess.CompletedProcess[str]:
        """Run the CLI against the source checkout."""

        return subprocess.run(
            [sys.executable, str(CLI), *args],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_profile_show_resolves_extends(self) -> None:
        """Profile inspection resolves inherited full-profile contents."""

        result = self.run_apex("profile", "show", "full", "--json")
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(payload["resolved"]["hooks"])
        self.assertIn("apex-session-init-codex", payload["resolved"]["codexSkills"])
        self.assertIn("gsap-core", payload["resolved"]["codexSkills"])
        self.assertIn("perf-optimizer", payload["resolved"]["agents"])

    def test_install_write_copies_profile_and_writes_manifest(self) -> None:
        """A profile install copies selected artifacts and records ownership."""

        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "project"
            target.mkdir()

            result = self.run_apex("install", str(target), "--profile", "core", "--target", "codex,claude", "--write", "--json")
            payload = json.loads(result.stdout)
            manifest = json.loads((target / ".apex" / "apexpowers-install.json").read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["manifest"]["action"], "create")
        self.assertTrue(any(item["path"].endswith(".codex/skills/apex-doctor/SKILL.md") for item in payload["results"]))
        self.assertTrue(any(item["path"].endswith(".claude/skills/apex-session-init-claude-code/SKILL.md") for item in payload["results"]))
        self.assertIn("core", manifest["profiles"])
        self.assertIn("codex", manifest["targets"])
        self.assertIn("claude", manifest["targets"])

    def test_install_dry_run_previews_agent_sync_without_requiring_files(self) -> None:
        """Dry-run stays side-effect free while still showing mirror sync plans."""

        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "project"
            target.mkdir()

            result = self.run_apex("install", str(target), "--profile", "core", "--target", "codex,claude", "--dry-run", "--json")
            payload = json.loads(result.stdout)
            sync_step = next(item for item in payload["subprocesses"] if item["name"] == "sync-agents")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sync_step["returncode"], 0)
        self.assertFalse((target / ".agents").exists())
        self.assertTrue(any(item["path"].endswith(".codex/agents/researcher.toml") for item in sync_step["stdout"]["results"]))

    def test_user_facing_cli_shapes_are_accepted(self) -> None:
        """The documented minimum CLI command shapes parse and execute."""

        install = self.run_apex("install", "--profile", "core", "--target", "codex,claude", "--scope", "project", "--dry-run", "--json")
        update = self.run_apex("update", "--dry-run", "--json")
        doctor = self.run_apex("doctor", "--json")
        sync = self.run_apex("sync-agent-mirrors", "--json")

        self.assertEqual(install.returncode, 0, install.stderr)
        self.assertEqual(json.loads(install.stdout)["operation"], "install")
        self.assertEqual(update.returncode, 0, update.stderr)
        self.assertEqual(json.loads(update.stdout)["operation"], "update")
        self.assertEqual(doctor.returncode, 0, doctor.stderr)
        self.assertEqual(sync.returncode, 0, sync.stderr)

    def test_update_skips_modified_managed_file(self) -> None:
        """Update does not overwrite a managed file after user modification."""

        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "project"
            target.mkdir()
            install = self.run_apex("install", str(target), "--profile", "core", "--target", "codex", "--write", "--json")
            skill = target / ".codex" / "skills" / "apex-doctor" / "SKILL.md"
            skill.write_text("# user modified\n", encoding="utf-8")

            update = self.run_apex("update", str(target), "--profile", "core", "--target", "codex", "--write", "--json")
            payload = json.loads(update.stdout)
            modified = [item for item in payload["results"] if item["path"] == ".codex/skills/apex-doctor/SKILL.md"]

        self.assertEqual(install.returncode, 0, install.stderr)
        self.assertEqual(update.returncode, 0, update.stderr)
        self.assertEqual(modified[0]["action"], "skip-modified")

    def test_uninstall_removes_unmodified_profile_files(self) -> None:
        """Uninstall removes exact managed copies and the install manifest."""

        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "project"
            target.mkdir()
            install = self.run_apex("install", str(target), "--profile", "core", "--target", "codex", "--write", "--json")
            uninstall = self.run_apex("uninstall", str(target), "--profile", "core", "--target", "codex", "--write", "--json")
            payload = json.loads(uninstall.stdout)
            skill_exists = (target / ".codex" / "skills" / "apex-doctor" / "SKILL.md").exists()
            manifest_exists = (target / ".apex" / "apexpowers-install.json").exists()

        self.assertEqual(install.returncode, 0, install.stderr)
        self.assertEqual(uninstall.returncode, 0, uninstall.stderr)
        self.assertFalse(skill_exists)
        self.assertFalse(manifest_exists)
        self.assertEqual(payload["manifest"]["action"], "remove-manifest")

    def test_uninstall_without_manifest_does_not_delete_matching_files(self) -> None:
        """Uninstall requires manifest ownership unless force is explicit."""

        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "project"
            target.mkdir()
            destination = target / ".codex" / "skills" / "apex-doctor"
            destination.mkdir(parents=True)
            source = ROOT / ".codex" / "skills" / "apex-doctor" / "SKILL.md"
            (destination / "SKILL.md").write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

            uninstall = self.run_apex("uninstall", str(target), "--profile", "core", "--target", "codex", "--write", "--json")
            payload = json.loads(uninstall.stdout)
            skill_exists = (destination / "SKILL.md").exists()
            actions = {item["action"] for item in payload["results"]}

        self.assertEqual(uninstall.returncode, 0, uninstall.stderr)
        self.assertTrue(skill_exists)
        self.assertIn("skip-unmanaged", actions)

    def test_hooks_profile_delegates_to_hook_installer(self) -> None:
        """Installing the hooks profile delegates hook files to the existing installer."""

        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "project"
            target.mkdir()
            codex_home = Path(raw) / "codex-home"
            claude_home = Path(raw) / "claude-home"

            result = self.run_apex(
                "install",
                str(target),
                "--profile",
                "hooks",
                "--target",
                "codex,claude",
                "--codex-home",
                str(codex_home),
                "--claude-home",
                str(claude_home),
                "--write",
                "--json",
            )
            payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        hooks_step = next(item for item in payload["subprocesses"] if item["name"] == "hooks")
        self.assertEqual(hooks_step["returncode"], 0, hooks_step["stderr"])
        self.assertEqual(hooks_step["stdout"]["operation"], "install")
        self.assertTrue(any(item["kind"] == "manifest" for item in hooks_step["stdout"]["results"]))

    def test_pack_codex_plugin_writes_profile_artifact_directory(self) -> None:
        """Pack creates a profile-specific Codex plugin artifact directory."""

        with tempfile.TemporaryDirectory() as raw:
            output = Path(raw) / "dist"
            result = self.run_apex("pack", "--profile", "core", "--target", "codex-plugin", "--output", str(output), "--json")
            payload = json.loads(result.stdout)
            artifact_dir = Path(payload["results"][0]["path"])
            plugin = json.loads((artifact_dir / "plugin.json").read_text(encoding="utf-8"))
            manifest = json.loads((artifact_dir / "manifest.json").read_text(encoding="utf-8"))
            sbom = json.loads((artifact_dir / "SBOM-lite.json").read_text(encoding="utf-8"))
            sha256sums = (artifact_dir / "SHA256SUMS").read_text(encoding="utf-8")
            has_skill = (artifact_dir / "skills" / "apex-doctor" / "SKILL.md").is_file()
            has_registry = (artifact_dir / "registry" / "apexpowers-profiles.json").is_file()
            has_notice = (artifact_dir / "NOTICE.md").is_file()
            has_install = (artifact_dir / "INSTALL.md").is_file()
            has_doctor_expected = (artifact_dir / "doctor-expected-output.json").is_file()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["results"][0]["action"], "create")
        self.assertEqual(plugin["skills"], "./skills/")
        self.assertEqual(manifest["schemaVersion"], "apexpowers.artifact.v1")
        self.assertEqual(manifest["target"], "codex-plugin")
        self.assertEqual(sbom["schemaVersion"], "apexpowers.sbom-lite.v1")
        self.assertIn("manifest.json", sha256sums)
        self.assertTrue(has_skill)
        self.assertTrue(has_registry)
        self.assertTrue(has_notice)
        self.assertTrue(has_install)
        self.assertTrue(has_doctor_expected)

    def test_pack_supports_skillpack_and_local_artifacts(self) -> None:
        """Pack can emit the artifact shapes requested by profile type."""

        with tempfile.TemporaryDirectory() as raw:
            output = Path(raw) / "dist"
            planning = self.run_apex("pack", "--profile", "planning", "--target", "skillpack", "--output", str(output), "--json")
            full = self.run_apex("pack", "--profile", "full", "--target", "local", "--output", str(output), "--json")
            planning_dir = Path(json.loads(planning.stdout)["results"][0]["path"])
            full_dir = Path(json.loads(full.stdout)["results"][0]["path"])
            has_planning_manifest = (planning_dir / "manifest.json").is_file()
            has_prd_skill = (planning_dir / "skills" / "apex-to-prd" / "SKILL.md").is_file()
            has_orchestration_command = (planning_dir / "commands" / "apex-orchestrate-delivery.toml").is_file()
            has_full_manifest = (full_dir / "manifest.json").is_file()
            has_gsap_skill = (full_dir / ".codex" / "skills" / "gsap-core" / "SKILL.md").is_file()
            has_perf_agent = (full_dir / ".agents" / "perf-optimizer.md").is_file()

        self.assertEqual(planning.returncode, 0, planning.stderr)
        self.assertEqual(full.returncode, 0, full.stderr)
        self.assertTrue(has_planning_manifest)
        self.assertTrue(has_prd_skill)
        self.assertTrue(has_orchestration_command)
        self.assertTrue(has_full_manifest)
        self.assertTrue(has_gsap_skill)
        self.assertTrue(has_perf_agent)


if __name__ == "__main__":
    unittest.main()
