"""Tests for ApexPowers distribution artifact checks."""

from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "check_apex_distribution.py"
SPEC = importlib.util.spec_from_file_location("check_apex_distribution", CHECKER)
assert SPEC is not None and SPEC.loader is not None
CHECKER_MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CHECKER_MODULE
SPEC.loader.exec_module(CHECKER_MODULE)


class ApexDistributionTests(unittest.TestCase):
    """Distribution files stay coherent across host adapters."""

    def run_checker(self, root: Path) -> subprocess.CompletedProcess[str]:
        """Run the distribution checker."""

        return subprocess.run(
            [sys.executable, str(CHECKER), str(root), "--json"],
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_current_distribution_passes(self) -> None:
        """The repository distribution artifacts are internally consistent."""

        result = self.run_checker(ROOT)
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["summary"]["fail"], 0)
        statuses = {item["name"]: item["status"] for item in payload["checks"]}
        self.assertEqual(statuses[".codex-plugin/plugin.json"], "pass")
        self.assertEqual(statuses[".claude-plugin/plugin.json"], "pass")
        self.assertEqual(statuses["profile-manifest"], "pass")
        self.assertEqual(statuses["lean-review-skill"], "pass")
        self.assertEqual(statuses["parallel-delivery-orchestration"], "pass")
        self.assertEqual(statuses["supply-chain-security-doc"], "pass")
        self.assertEqual(statuses["notice"], "pass")
        self.assertEqual(statuses["supply-chain-sha256-manifest"], "pass")

    def test_missing_distribution_artifacts_fail(self) -> None:
        """A blank project fails with actionable missing-artifact output."""

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            result = self.run_checker(root)
            payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        checks = {item["name"]: item for item in payload["checks"]}
        self.assertEqual(checks["required-artifacts"]["status"], "fail")
        self.assertIn("production-plan", checks["required-artifacts"]["message"])

    def test_plugin_manifests_are_thin(self) -> None:
        """Plugin manifests expose skills but do not directly install hooks."""

        for rel in (".codex-plugin/plugin.json", ".claude-plugin/plugin.json"):
            payload = json.loads((ROOT / rel).read_text(encoding="utf-8"))
            self.assertEqual(payload["name"], "apexpowers")
            self.assertRegex(payload["version"], r"^\d+\.\d+\.\d+$")
            self.assertNotIn("hooks", payload)
        codex_payload = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(codex_payload["skills"], "./.codex-plugin/profiles/core/skills/")

    def test_profile_manifest_covers_current_skills(self) -> None:
        """Profiles keep default plugin exposure small while covering every skill."""

        check = CHECKER_MODULE.check_profile_manifest(ROOT)
        payload = json.loads((ROOT / "registry" / "apexpowers-profiles.json").read_text(encoding="utf-8"))
        all_codex_skills = {path.name for path in (ROOT / ".codex" / "skills").iterdir() if path.is_dir()}
        core_skills = set(payload["profiles"]["core"]["codexSkills"])
        full_skills = set()
        for profile_name in payload["profiles"]["full"]["extends"]:
            full_skills.update(payload["profiles"][profile_name].get("codexSkills", []))

        self.assertEqual(check.status, "pass", check.message)
        self.assertLess(len(core_skills), len(all_codex_skills))
        self.assertEqual(full_skills, all_codex_skills)
        self.assertTrue(payload["profiles"]["hooks"]["hooks"]["requiresTrust"])
        self.assertTrue(payload["profiles"]["hooks"]["hooks"]["managedByManifest"])

    def test_supply_chain_security_doc_requires_trust_invariants(self) -> None:
        """The supply-chain doc check fails when trust and telemetry policy disappear."""

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "docs").mkdir()
            (root / "docs" / "supply-chain-trust-security.md").write_text("# incomplete\n", encoding="utf-8")

            check = CHECKER_MODULE.check_supply_chain_security_doc(root)

        self.assertEqual(check.status, "fail")
        self.assertIn("Telemetry Policy", check.details["missing"])
        self.assertIn("review / trust", check.details["missing"])

    def test_notice_requires_vendored_skill_groups(self) -> None:
        """NOTICE must account for current vendored source groups."""

        check = CHECKER_MODULE.check_notice(ROOT)

        self.assertEqual(check.status, "pass", check.message)
        with tempfile.TemporaryDirectory() as raw:
            self.assertEqual(CHECKER_MODULE.check_notice(Path(raw)).status, "fail")

    def test_parallel_delivery_orchestration_requires_command_and_protocol(self) -> None:
        """The orchestration gate protects worktree/issue/PR delivery protocol drift."""

        check = CHECKER_MODULE.check_parallel_delivery_orchestration(ROOT)

        self.assertEqual(check.status, "pass", check.message)
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "docs").mkdir()
            (root / "commands").mkdir()
            (root / "docs" / "apex-parallel-delivery-orchestration.md").write_text("# incomplete\nworktree\n", encoding="utf-8")
            (root / "commands" / "apex-orchestrate-delivery.toml").write_text('description = "x"\nprompt = "x"\n', encoding="utf-8")

            missing_check = CHECKER_MODULE.check_parallel_delivery_orchestration(root)

        self.assertEqual(missing_check.status, "fail")
        self.assertIn("apex-to-issues", missing_check.details["missing"])
        self.assertIn("explicit review gate", missing_check.details["missing"])


if __name__ == "__main__":
    unittest.main()
