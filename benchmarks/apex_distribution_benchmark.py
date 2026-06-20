#!/usr/bin/env python3
"""Offline benchmark harness for ApexPowers distribution paths."""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DISTRIBUTION_CHECK = ROOT / "scripts" / "check_apex_distribution.py"
DOCTOR = ROOT / ".codex" / "skills" / "apex-doctor" / "scripts" / "apex_doctor.py"
INSTALLER = ROOT / ".codex" / "skills" / "apex-init-project-hooks" / "scripts" / "init_project_hooks.py"
RUNTIME = ROOT / ".codex" / "skills" / "apex-init-project-hooks" / "scripts" / "apex_loop.py"


@dataclass
class Sample:
    """One benchmark command sample."""

    name: str
    elapsed_ms: float
    returncode: int
    stderr: str = ""

    def to_dict(self) -> dict[str, Any]:
        """JSON-ready sample."""

        payload: dict[str, Any] = {
            "name": self.name,
            "elapsed_ms": round(self.elapsed_ms, 3),
            "returncode": self.returncode,
        }
        if self.stderr:
            payload["stderr"] = self.stderr[:1000]
        return payload


@dataclass
class Cell:
    """Benchmark cell with samples."""

    name: str
    command: list[str]
    samples: list[Sample] = field(default_factory=list)

    def summarize(self) -> dict[str, Any]:
        """Summarize sample timings."""

        elapsed = [sample.elapsed_ms for sample in self.samples]
        return {
            "name": self.name,
            "runs": len(self.samples),
            "returncodes": sorted({sample.returncode for sample in self.samples}),
            "min_ms": round(min(elapsed), 3),
            "median_ms": round(statistics.median(elapsed), 3),
            "max_ms": round(max(elapsed), 3),
            "samples": [sample.to_dict() for sample in self.samples],
        }


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(description="Run offline ApexPowers distribution benchmarks.")
    parser.add_argument("--root", default=str(ROOT), help="Repository root. Defaults to this checkout.")
    parser.add_argument("--runs", type=int, default=3, help="Samples per cell.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser.parse_args()


def run_command(name: str, command: list[str], cwd: Path) -> Sample:
    """Run one command and measure wall time."""

    start = time.perf_counter()
    result = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    elapsed_ms = (time.perf_counter() - start) * 1000
    return Sample(name=name, elapsed_ms=elapsed_ms, returncode=result.returncode, stderr=result.stderr.strip())


def build_cells(root: Path, temp_root: Path) -> list[Cell]:
    """Build benchmark cells with isolated agent homes."""

    codex_home = temp_root / "codex-home"
    claude_home = temp_root / "claude-home"
    script_path = temp_root / "hooks" / "apex_loop.py"
    return [
        Cell("distribution-check", [sys.executable, str(DISTRIBUTION_CHECK), str(root), "--json"]),
        Cell("doctor", [sys.executable, str(DOCTOR), str(root), "--codex-home", str(codex_home), "--claude-home", str(claude_home), "--json"]),
        Cell("installer-dry-run", [sys.executable, str(INSTALLER), str(root), "--codex-home", str(codex_home), "--claude-home", str(claude_home), "--json"]),
        Cell("render-codex-toml", [sys.executable, str(RUNTIME), "render-config", "codex", "--script-path", str(script_path), "--config-format", "toml"]),
        Cell("render-claude-json", [sys.executable, str(RUNTIME), "render-config", "claude", "--script-path", str(script_path), "--config-format", "json"]),
    ]


def run_benchmark(root: Path, runs: int) -> tuple[list[Cell], int]:
    """Run all cells."""

    if runs < 1:
        raise SystemExit("--runs must be >= 1")
    with tempfile.TemporaryDirectory() as raw:
        temp_root = Path(raw)
        cells = build_cells(root, temp_root)
        for cell in cells:
            for _ in range(runs):
                cell.samples.append(run_command(cell.name, cell.command, root))
    exit_code = 1 if any(sample.returncode != 0 for cell in cells for sample in cell.samples) else 0
    return cells, exit_code


def print_text(root: Path, cells: list[Cell]) -> None:
    """Print human-readable output."""

    print(f"Apex distribution benchmark: {root}")
    print("No comparative savings claim; this measures local offline Apex paths only.")
    for cell in cells:
        summary = cell.summarize()
        print(
            f"{summary['name']}: median={summary['median_ms']}ms "
            f"min={summary['min_ms']}ms max={summary['max_ms']}ms returncodes={summary['returncodes']}"
        )


def print_json(root: Path, cells: list[Cell]) -> None:
    """Print JSON output."""

    payload = {
        "root": str(root),
        "method": "offline ApexPowers distribution benchmark; no Ponytail result reuse and no comparative savings claim",
        "cells": [cell.summarize() for cell in cells],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> int:
    """CLI entrypoint."""

    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    cells, exit_code = run_benchmark(root, args.runs)
    if args.json:
        print_json(root, cells)
    else:
        print_text(root, cells)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
