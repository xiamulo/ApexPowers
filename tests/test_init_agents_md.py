"""Tests for the apex-init-project-file directory discovery helper."""

from __future__ import annotations

import tempfile
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".codex" / "skills" / "apex-init-project-file" / "scripts" / "init_agents_md.py"


class InitAgentsMdTests(unittest.TestCase):
    def run_script(self, root: Path, *args: str) -> dict[str, object]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(root), "--json", *args],
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_missing_mode_skips_folders_with_folder_md(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            documented = root / "documented"
            undocumented = root / "undocumented"
            documented.mkdir()
            undocumented.mkdir()
            (documented / "FOLDER.md").write_text("# documented\n", encoding="utf-8")

            payload = self.run_script(root)

            self.assertEqual(payload["targets"], ["undocumented"])

    def test_regenerate_mode_includes_existing_folder_md(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            documented = root / "documented"
            documented.mkdir()
            (documented / "folder.md").write_text("# documented\n", encoding="utf-8")

            payload = self.run_script(root, "--all")

            self.assertEqual(payload["targets"], ["documented"])


if __name__ == "__main__":
    unittest.main()
