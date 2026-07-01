"""Stop and PreCompact loop-safety contracts."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / ".codex" / "skills" / "apex-init-project-hooks" / "scripts" / "apex_loop.py"


class StopLoopSafetyTests(unittest.TestCase):
    """Stop recursion and compaction state should stay bounded."""

    def init_repo(self, cwd: Path) -> None:
        subprocess.run(["git", "init"], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        subprocess.run(["git", "config", "user.name", "Hook Test"], cwd=cwd, check=True)
        subprocess.run(["git", "config", "user.email", "hook@test.local"], cwd=cwd, check=True)
        (cwd / "README.md").write_text("# demo\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=cwd, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

    def test_stop_hook_active_allows_blocked_exit_without_new_review(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            (cwd / "src").mkdir()
            (cwd / "src" / "large.py").write_text("\n".join(f"print({index})" for index in range(751)) + "\n", encoding="utf-8")
            (cwd / "tasks").mkdir()
            (cwd / "tasks" / "todo+demo.md").write_text("# Demo\n\n- [x] Implement\n", encoding="utf-8")
            first = subprocess.run(
                [sys.executable, str(RUNTIME), "stop", "--host", "codex", "--route", "default"],
                cwd=cwd,
                input=json.dumps({}),
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            result = subprocess.run(
                [sys.executable, str(RUNTIME), "stop", "--host", "codex", "--route", "default"],
                cwd=cwd,
                input=json.dumps({"stop_hook_active": True}),
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            payload = json.loads(result.stdout)
            state = json.loads((cwd / "tasks" / "loops" / "demo" / "state.json").read_text(encoding="utf-8"))

        self.assertEqual(first.returncode, 2)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(payload["status"], "blocked")
        self.assertIn("not done", payload["reason"])
        self.assertEqual(state["last_block_gate"], "LineLengthGuard")
        self.assertFalse((cwd / "tasks" / "reviews" / "demo.md").exists())
        self.assertEqual(state["continuation_count"], 1)
        self.assertEqual(state["max_continuations"], 0)

    def test_pre_compact_writes_session_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.init_repo(cwd)
            (cwd / "src").mkdir()
            (cwd / "src" / "feature.py").write_text("print('hello')\n", encoding="utf-8")
            (cwd / "tasks").mkdir()
            (cwd / "tasks" / "todo+demo.md").write_text("# Demo\n\n- [ ] Implement\n", encoding="utf-8")
            (cwd / "tasks" / "loops").mkdir(parents=True, exist_ok=True)
            (cwd / "tasks" / "loops" / "security-required.json").write_text(
                json.dumps({"schema_version": 1, "status": "security_required", "subjects": ["src/leak.py"]}),
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(RUNTIME), "pre-compact", "--host", "codex", "--route", "default"],
                cwd=cwd,
                input=json.dumps({"trigger": "manual"}),
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            snapshot = cwd / "tasks" / "loops" / "session-snapshot.json"
            self.assertTrue(snapshot.exists())
            snapshot_payload = json.loads(snapshot.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(snapshot_payload["schema_version"], 1)
        self.assertEqual(snapshot_payload["workflow_state"], "security_required")
        self.assertNotIn("review_missing", snapshot_payload["blockers"])
        self.assertIn("security_required", snapshot_payload["blockers"])
        self.assertTrue(snapshot_payload["security_required"])
        self.assertIn("hookSpecificOutput", result.stdout)


if __name__ == "__main__":
    unittest.main()
