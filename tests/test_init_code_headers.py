"""Contract tests for Apex init project code header discovery."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".codex" / "skills" / "apex-init-project-code" / "scripts" / "init_code_headers.py"


class InitCodeHeadersTests(unittest.TestCase):
    """Header discovery is driven by standard purpose markers."""

    def run_script(self, root: Path) -> dict[str, object]:
        """Run the header discovery script in JSON mode."""

        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(root), "--json"],
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_plain_leading_comment_still_needs_purpose_header(self) -> None:
        """A normal leading comment is not treated as an existing Apex header."""

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "plain.ts").write_text("// license note\nexport const value = 1;\n", encoding="utf-8")

            payload = self.run_script(root)

        self.assertEqual(payload["targets"], ["plain.ts"])

    def test_purpose_marker_skips_file(self) -> None:
        """A standard purpose marker is enough to identify an existing header."""

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "ready.ts").write_text("// @purpose: exposes a value\nexport const value = 1;\n", encoding="utf-8")

            payload = self.run_script(root)

        self.assertEqual(payload["targets"], [])

    def test_common_component_config_style_and_sql_exts_are_scanned(self) -> None:
        """Broader source families are selected without enabling Markdown scanning."""

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for name in ("App.vue", "page.nvue", "pipeline.yaml", "theme.scss", "query.sql"):
                (root / name).write_text("content\n", encoding="utf-8")
            (root / "notes.md").write_text("content\n", encoding="utf-8")

            payload = self.run_script(root)

        self.assertEqual(
            payload["targets"],
            ["App.vue", "page.nvue", "pipeline.yaml", "query.sql", "theme.scss"],
        )


if __name__ == "__main__":
    unittest.main()
