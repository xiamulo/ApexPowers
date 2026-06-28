#!/usr/bin/env python3
"""Check ApexPowers distribution artifacts for drift."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback.
    tomllib = None  # type: ignore[assignment]


SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
HOST_INVARIANTS = (
    "Codex",
    "Claude Code",
    "OpenCode",
    "Gemini",
    "GitHub Copilot",
    "Cursor",
    "Windsurf",
    "Cline",
    "Kiro",
    "CodeWhale",
    "MCP",
)
PLATFORM_SECTIONS = (
    "HTML And Form Controls",
    "CSS Capabilities",
    "Browser APIs",
    "Node.js Standard Library",
    "Python Standard Library",
    "Database Capabilities",
)
REQUIRED_ARTIFACTS = {
    "production-plan": "tasks/todo+apex-ponytail-production.md",
    "portability-doc": "docs/apex-agent-portability.md",
    "parallel-delivery-orchestration-doc": "docs/apex-parallel-delivery-orchestration.md",
    "platform-native-doc": "docs/platform-native-solutions.md",
    "supply-chain-security-doc": "docs/supply-chain-trust-security.md",
    "supply-chain-sha256-manifest": "docs/supply-chain-manifest.sha256",
    "notice": "NOTICE.md",
    "codex-plugin": ".codex-plugin/plugin.json",
    "profile-manifest": "registry/apexpowers-profiles.json",
    "claude-plugin": ".claude-plugin/plugin.json",
    "lean-review-skill": ".codex/skills/apex-lean-review/SKILL.md",
    "benchmark-readme": "benchmarks/README.md",
    "benchmark-script": "benchmarks/apex_distribution_benchmark.py",
    "inventory-doc": "docs/apexpowers-inventory.md",
    "readme": "README.md",
}
COMMAND_FILES = (
    "commands/apex-doctor.toml",
    "commands/apex-init-project-hooks.toml",
    "commands/apex-sync-agent-mirrors.toml",
    "commands/apex-lean-review.toml",
    "commands/apex-orchestrate-delivery.toml",
)
PROFILE_MANIFEST = "registry/apexpowers-profiles.json"
CODEX_CORE_PROFILE_SKILLS = "./.codex-plugin/profiles/core/skills/"
SHA256_MANIFEST = "docs/supply-chain-manifest.sha256"
TRUST_CRITICAL_HASH_PATHS = (
    ".codex-plugin/plugin.json",
    ".claude-plugin/plugin.json",
    "registry/apexpowers-profiles.json",
    "commands/apex-doctor.toml",
    "commands/apex-init-project-hooks.toml",
    "commands/apex-sync-agent-mirrors.toml",
    "commands/apex-lean-review.toml",
    "commands/apex-orchestrate-delivery.toml",
    ".codex/skills/apex-init-project-hooks/SKILL.md",
    ".codex/skills/apex-init-project-hooks/scripts/init_project_hooks.py",
    ".codex/skills/apex-init-project-hooks/scripts/apex_loop_routes.py",
    ".codex/skills/apex-init-project-hooks/scripts/apex_loop_runtime.py",
    ".codex/skills/apex-init-project-hooks/scripts/apex_loop_utils.py",
    ".github/workflows/quality.yml",
    ".pre-commit-config.yaml",
    "gitleaks.toml",
    "docs/supply-chain-trust-security.md",
    "docs/apex-parallel-delivery-orchestration.md",
    "NOTICE.md",
)


@dataclass(frozen=True)
class Check:
    """One distribution check result."""

    name: str
    status: str
    message: str
    fix: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-ready dict."""

        payload: dict[str, Any] = {"name": self.name, "status": self.status, "message": self.message}
        if self.fix:
            payload["fix"] = self.fix
        if self.details:
            payload["details"] = self.details
        return payload


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(description="Check ApexPowers distribution artifacts.")
    parser.add_argument("root", nargs="?", default=".", help="Repository root. Defaults to current directory.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--write-sha256-manifest", action="store_true", help=f"Update {SHA256_MANIFEST} before checking.")
    return parser.parse_args()


def read_text(path: Path) -> str | None:
    """Read UTF-8 text, returning None when missing or unreadable."""

    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    """Load a JSON object."""

    text = read_text(path)
    if text is None:
        return None, "missing"
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, f"invalid json: {exc}"
    if not isinstance(payload, dict):
        return None, "json root is not an object"
    return payload, None


def file_sha256(path: Path) -> str:
    """SHA-256 for the exact bytes stored on disk."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_sha256_manifest(root: Path) -> None:
    """Write the trust-critical source manifest."""

    lines = [
        "# ApexPowers trust-critical artifact hashes.",
        "# Format: <sha256>  <repo-relative-path>",
    ]
    for rel in TRUST_CRITICAL_HASH_PATHS:
        path = root / rel
        if path.is_file():
            lines.append(f"{file_sha256(path)}  {rel}")
    (root / SHA256_MANIFEST).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def parse_toml(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    """Parse a TOML command file with a small fallback."""

    text = read_text(path)
    if text is None:
        return None, "missing"
    if tomllib is not None:
        try:
            payload = tomllib.loads(text)
        except tomllib.TOMLDecodeError as exc:
            return None, f"invalid toml: {exc}"
        return payload, None

    payload: dict[str, Any] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] == '"':
            payload[key.strip()] = value[1:-1]
    return payload, None


def check_required_artifacts(root: Path) -> Check:
    """Check that the expected distribution files exist."""

    missing = [name for name, rel in REQUIRED_ARTIFACTS.items() if not (root / rel).is_file()]
    missing.extend(rel for rel in COMMAND_FILES if not (root / rel).is_file())
    if missing:
        return Check("required-artifacts", "fail", f"Missing distribution artifacts: {', '.join(missing)}", "Create the missing files or update REQUIRED_ARTIFACTS.", {"missing": missing})
    return Check("required-artifacts", "pass", f"{len(REQUIRED_ARTIFACTS) + len(COMMAND_FILES)} distribution artifacts are present.")


def check_plugin_manifest(root: Path, rel: str, expected_skills: str) -> Check:
    """Check one plugin manifest."""

    path = root / rel
    payload, error = load_json(path)
    if error:
        return Check(rel, "fail", f"Manifest error: {error}", "Fix the plugin JSON.")
    assert payload is not None

    issues: list[str] = []
    if payload.get("name") != "apexpowers":
        issues.append("name must be apexpowers")
    version = str(payload.get("version", ""))
    if not SEMVER.match(version):
        issues.append("version must be pinned semver")
    if "hooks" in payload:
        issues.append("thin manifest must not declare hooks")
    skills = payload.get("skills")
    skill_values = skills if isinstance(skills, list) else [skills]
    if expected_skills not in skill_values:
        issues.append(f"skills must include {expected_skills}")
    if not (root / expected_skills).resolve().exists():
        issues.append(f"skills path does not exist: {expected_skills}")

    if issues:
        return Check(rel, "fail", f"Manifest drift: {', '.join(issues)}", "Keep plugin manifests thin and pointed at existing skill directories.", {"issues": issues})
    return Check(rel, "pass", f"{rel} is a thin plugin manifest.")


def require_string_list(profile_name: str, profile: dict[str, Any], field_name: str, issues: list[str]) -> list[str]:
    """Return a string list field and append validation issues."""

    value = profile.get(field_name, [])
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        issues.append(f"{profile_name}.{field_name} must be a list of non-empty strings")
        return []
    return value


def collect_profile_field(profiles: dict[str, dict[str, Any]], profile_name: str, field_name: str, seen: set[str] | None = None) -> set[str]:
    """Collect a profile field through extends."""

    if seen is None:
        seen = set()
    if profile_name in seen:
        return set()
    seen.add(profile_name)

    profile = profiles.get(profile_name, {})
    values = set(require_string_list(profile_name, profile, field_name, []))
    for parent in require_string_list(profile_name, profile, "extends", []):
        values.update(collect_profile_field(profiles, parent, field_name, seen))
    return values


def check_profile_manifest(root: Path) -> Check:
    """Check ApexPowers profile manifest and default minimal Codex exposure."""

    payload, error = load_json(root / PROFILE_MANIFEST)
    if error:
        return Check("profile-manifest", "fail", f"Profile manifest error: {error}", "Create registry/apexpowers-profiles.json.")
    assert payload is not None

    issues: list[str] = []
    if payload.get("schemaVersion") != "apexpowers.profiles.v1":
        issues.append("schemaVersion must be apexpowers.profiles.v1")

    profiles_raw = payload.get("profiles")
    if not isinstance(profiles_raw, dict) or not profiles_raw:
        return Check("profile-manifest", "fail", "profiles must be a non-empty object", "Add profile definitions to the manifest.")

    profiles: dict[str, dict[str, Any]] = {}
    for name, profile in profiles_raw.items():
        if not isinstance(name, str) or not name:
            issues.append("profile names must be non-empty strings")
            continue
        if not isinstance(profile, dict):
            issues.append(f"{name} profile must be an object")
            continue
        profiles[name] = profile

    default_profile = payload.get("defaultProfile")
    if default_profile != "core":
        issues.append("defaultProfile must be core")
    if default_profile not in profiles:
        issues.append("defaultProfile must reference an existing profile")

    all_codex_skills = {path.name for path in (root / ".codex" / "skills").iterdir() if path.is_dir()}
    manifest_codex_skills: set[str] = set()
    for name, profile in profiles.items():
        extends = require_string_list(name, profile, "extends", issues)
        for parent in extends:
            if parent not in profiles:
                issues.append(f"{name}.extends references missing profile {parent}")

        codex_skills = require_string_list(name, profile, "codexSkills", issues)
        manifest_codex_skills.update(codex_skills)
        for skill in codex_skills:
            if not (root / ".codex" / "skills" / skill / "SKILL.md").is_file():
                issues.append(f"{name}.codexSkills references missing skill {skill}")

        for skill in require_string_list(name, profile, "claudeSkills", issues):
            if not (root / ".claude" / "skills" / skill / "SKILL.md").is_file():
                issues.append(f"{name}.claudeSkills references missing skill {skill}")

        for agent in require_string_list(name, profile, "agents", issues):
            if not (root / ".agents" / f"{agent}.md").is_file():
                issues.append(f"{name}.agents references missing agent {agent}")

        for command in require_string_list(name, profile, "commands", issues):
            if not (root / "commands" / f"{command}.toml").is_file():
                issues.append(f"{name}.commands references missing command {command}")

        hooks = profile.get("hooks", False)
        if hooks not in (False, None) and not isinstance(hooks, dict):
            issues.append(f"{name}.hooks must be false or an object")
        if isinstance(hooks, dict) and (hooks.get("requiresTrust") is not True or hooks.get("managedByManifest") is not True):
            issues.append(f"{name}.hooks must declare requiresTrust=true and managedByManifest=true")

    missing_codex_skills = sorted(all_codex_skills - manifest_codex_skills)
    if missing_codex_skills:
        issues.append(f"profile manifest does not cover Codex skills: {', '.join(missing_codex_skills)}")

    core_skills = collect_profile_field(profiles, "core", "codexSkills")
    if len(core_skills) > 8:
        issues.append("core profile must stay small; expected at most 8 Codex skills")
    for skill in core_skills:
        if not (root / ".codex-plugin" / "profiles" / "core" / "skills" / skill / "SKILL.md").is_file():
            issues.append(f"core wrapper missing for {skill}")

    full_skills = collect_profile_field(profiles, "full", "codexSkills")
    if full_skills != all_codex_skills:
        missing = sorted(all_codex_skills - full_skills)
        extra = sorted(full_skills - all_codex_skills)
        issues.append(f"full profile must match all Codex skills; missing={missing}, extra={extra}")

    if issues:
        return Check("profile-manifest", "fail", f"Profile manifest issues: {len(issues)}", "Keep registry/apexpowers-profiles.json aligned with skills, agents, commands, and hook trust boundaries.", {"issues": issues})
    return Check("profile-manifest", "pass", f"{len(profiles)} profiles cover {len(all_codex_skills)} Codex skills; default profile exposes {len(core_skills)} core skills.")


def check_commands(root: Path) -> Check:
    """Check command prompt wrappers."""

    issues: list[str] = []
    for rel in COMMAND_FILES:
        payload, error = parse_toml(root / rel)
        if error:
            issues.append(f"{rel}: {error}")
            continue
        assert payload is not None
        if not str(payload.get("description", "")).strip():
            issues.append(f"{rel}: missing description")
        if not str(payload.get("prompt", "")).strip():
            issues.append(f"{rel}: missing prompt")
    if issues:
        return Check("commands", "fail", f"Command wrapper issues: {len(issues)}", "Each command TOML needs description and prompt.", {"issues": issues})
    return Check("commands", "pass", f"{len(COMMAND_FILES)} command wrappers are valid.")


def check_portability_doc(root: Path) -> Check:
    """Check host matrix invariants."""

    text = read_text(root / "docs/apex-agent-portability.md") or ""
    missing = [item for item in HOST_INVARIANTS if item not in text]
    if missing:
        return Check("portability-doc", "fail", f"Portability doc missing hosts: {', '.join(missing)}", "Update docs/apex-agent-portability.md.", {"missing": missing})
    return Check("portability-doc", "pass", f"Portability doc covers {len(HOST_INVARIANTS)} host invariants.")


def check_parallel_delivery_orchestration(root: Path) -> Check:
    """Check explicit worktree/issue/PR orchestration command and protocol."""

    doc = read_text(root / "docs/apex-parallel-delivery-orchestration.md") or ""
    command = read_text(root / "commands/apex-orchestrate-delivery.toml") or ""
    combined = f"{doc}\n{command}"
    required = (
        "apex-orchestrate-delivery",
        "worktree",
        "issue",
        "PR",
        "apex-to-issues",
        "planner",
        "researcher",
        "implementer",
        "developer",
        "code-reviewer",
        "perf-optimizer",
        "official agent mirrors",
        "Stop review request gate",
        "Validation: Pass",
        "overlapping uncommitted changes",
    )
    missing = [item for item in required if item not in combined]
    if missing:
        return Check("parallel-delivery-orchestration", "fail", f"Orchestration protocol missing invariants: {', '.join(missing)}", "Update docs/apex-parallel-delivery-orchestration.md and commands/apex-orchestrate-delivery.toml.", {"missing": missing})
    return Check("parallel-delivery-orchestration", "pass", "Explicit worktree/issue/PR orchestration command and protocol are present.")


def check_platform_doc(root: Path) -> Check:
    """Check platform-native capability sections."""

    text = read_text(root / "docs/platform-native-solutions.md") or ""
    missing = [item for item in PLATFORM_SECTIONS if item not in text]
    if missing:
        return Check("platform-native-doc", "fail", f"Platform-native doc missing sections: {', '.join(missing)}", "Restore required capability sections.", {"missing": missing})
    return Check("platform-native-doc", "pass", f"Platform-native doc covers {len(PLATFORM_SECTIONS)} areas.")


def check_lean_skill(root: Path) -> Check:
    """Check lean review skill invariants."""

    text = read_text(root / ".codex/skills/apex-lean-review/SKILL.md") or ""
    invariant_groups = (
        ("input validation at trust boundaries", ("input validation at trust boundaries", "信任边界上的输入校验")),
        ("error handling that prevents data loss", ("error handling that prevents data loss", "防止数据丢失的错误处理")),
        ("accessibility", ("accessibility", "可访问性")),
        ("docs/platform-native-solutions.md", ("docs/platform-native-solutions.md",)),
        ("Apex Lean Review", ("Apex Lean Review", "Apex 精简审查")),
    )
    missing = [name for name, alternatives in invariant_groups if not any(alternative in text for alternative in alternatives)]
    if missing:
        return Check("lean-review-skill", "fail", f"Lean review skill missing invariants: {', '.join(missing)}", "Restore safety boundaries and platform-native reference.", {"missing": missing})
    return Check("lean-review-skill", "pass", "Lean review skill contains required safety and native-platform invariants.")


def check_benchmark_method(root: Path) -> Check:
    """Check benchmark method files and language."""

    readme = read_text(root / "benchmarks/README.md") or ""
    script = root / "benchmarks/apex_distribution_benchmark.py"
    issues: list[str] = []
    if "No comparative savings claim" not in readme:
        issues.append("README must forbid comparative savings claims")
    if "Ponytail" not in readme:
        issues.append("README must explain that Ponytail results are not reused")
    if not script.is_file():
        issues.append("benchmark script missing")
    if issues:
        return Check("benchmark-method", "fail", f"Benchmark method issues: {', '.join(issues)}", "Update benchmarks docs and script.", {"issues": issues})
    return Check("benchmark-method", "pass", "Benchmark method is present and framed as Apex-only measurement.")


def check_supply_chain_security_doc(root: Path) -> Check:
    """Check supply-chain, trust, and hook security documentation invariants."""

    text = read_text(root / "docs/supply-chain-trust-security.md") or ""
    required = (
        "Vendored Skills Source",
        "NOTICE",
        "Hook Command Threat Model",
        "review / trust",
        "plugin manifests must not declare hooks",
        "opt-in",
        "sha256",
        "Generated by ApexPowers apex-init-project-hooks",
        "Telemetry Policy",
        "Default: no telemetry",
        "update / uninstall",
        "secret/path guard false-positive",
    )
    missing = [item for item in required if item not in text]
    if missing:
        return Check("supply-chain-security-doc", "fail", f"Supply-chain security doc missing invariants: {', '.join(missing)}", "Update docs/supply-chain-trust-security.md.", {"missing": missing})
    return Check("supply-chain-security-doc", "pass", "Supply-chain, trust, telemetry, provenance, and hook threat-model policy is documented.")


def check_notice(root: Path) -> Check:
    """Check third-party notice coverage for vendored skill groups."""

    text = read_text(root / "NOTICE.md") or ""
    required = (
        "ApexPowers",
        "web-quality-skills",
        "GSAP",
        "Vercel",
        "Anthropic",
        "github-solution-research",
        "MIT",
        "Apache-2.0",
        "UNLICENSED",
    )
    missing = [item for item in required if item not in text]
    if missing:
        return Check("notice", "fail", f"NOTICE missing entries: {', '.join(missing)}", "Update NOTICE.md when vendored skill sources change.", {"missing": missing})
    return Check("notice", "pass", "NOTICE covers current vendored skill source groups and licenses.")


def check_sha256_manifest(root: Path) -> Check:
    """Check trust-critical artifact hashes."""

    path = root / SHA256_MANIFEST
    text = read_text(path)
    if text is None:
        return Check("supply-chain-sha256-manifest", "fail", f"Missing {SHA256_MANIFEST}.", f"Run python scripts/check_apex_distribution.py --write-sha256-manifest.")

    entries: dict[str, str] = {}
    issues: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split(None, 1)
        if len(parts) != 2:
            issues.append(f"line {line_number}: expected '<sha256>  <path>'")
            continue
        digest, rel = parts[0], parts[1].strip()
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            issues.append(f"{rel}: invalid sha256")
            continue
        rel_path = Path(rel)
        if rel_path.is_absolute() or ".." in rel_path.parts:
            issues.append(f"{rel}: path must be repo-relative")
            continue
        target = root / rel
        if not target.is_file():
            issues.append(f"{rel}: missing")
            continue
        actual = file_sha256(target)
        if actual != digest:
            issues.append(f"{rel}: sha256 drift")
        entries[rel.replace("\\", "/")] = digest

    missing_entries = [rel for rel in TRUST_CRITICAL_HASH_PATHS if rel not in entries]
    issues.extend(f"{rel}: missing manifest entry" for rel in missing_entries if (root / rel).is_file())
    if issues:
        return Check("supply-chain-sha256-manifest", "fail", f"SHA-256 manifest issues: {len(issues)}", "Regenerate hashes after reviewing trust-critical artifact changes.", {"issues": issues})
    return Check("supply-chain-sha256-manifest", "pass", f"{len(entries)} trust-critical artifact hashes are current.")


def check_repo_metadata(root: Path) -> Check:
    """Check README and inventory mention distribution artifacts."""

    readme = read_text(root / "README.md") or ""
    inventory = read_text(root / "docs/apexpowers-inventory.md") or ""
    required = (
        "apex-doctor",
        "apex-lean-review",
        "check_apex_distribution.py",
        "apex_distribution_benchmark.py",
        "apex-agent-portability.md",
        "apex-parallel-delivery-orchestration.md",
        "apex-orchestrate-delivery.toml",
        "platform-native-solutions.md",
        "supply-chain-trust-security.md",
        "NOTICE.md",
    )
    issues: list[str] = []
    for item in required:
        if item not in readme and item not in inventory:
            issues.append(f"missing metadata mention: {item}")
    if issues:
        return Check("repo-metadata", "fail", f"README/inventory drift: {', '.join(issues)}", "Update README.md or docs/apexpowers-inventory.md.", {"issues": issues})
    return Check("repo-metadata", "pass", "README/inventory mention the new distribution artifacts.")


def run_checks(root: Path) -> list[Check]:
    """Run all distribution checks."""

    return [
        check_required_artifacts(root),
        check_plugin_manifest(root, ".codex-plugin/plugin.json", CODEX_CORE_PROFILE_SKILLS),
        check_plugin_manifest(root, ".claude-plugin/plugin.json", "./.claude/skills/"),
        check_profile_manifest(root),
        check_commands(root),
        check_portability_doc(root),
        check_parallel_delivery_orchestration(root),
        check_platform_doc(root),
        check_lean_skill(root),
        check_benchmark_method(root),
        check_supply_chain_security_doc(root),
        check_notice(root),
        check_sha256_manifest(root),
        check_repo_metadata(root),
    ]


def summary(checks: list[Check]) -> dict[str, int]:
    """Count check statuses."""

    return {status: sum(1 for check in checks if check.status == status) for status in ("pass", "warn", "fail")}


def print_text(root: Path, checks: list[Check]) -> None:
    """Print human-readable output."""

    print(f"Apex distribution check: {root}")
    for check in checks:
        print(f"[{check.status.upper()}] {check.name}: {check.message}")
        if check.fix:
            print(f"  fix: {check.fix}")
    counts = summary(checks)
    print(f"Summary: {counts['pass']} pass, {counts['warn']} warn, {counts['fail']} fail.")


def print_json(root: Path, checks: list[Check]) -> None:
    """Print JSON output."""

    payload = {"root": str(root), "summary": summary(checks), "checks": [check.to_dict() for check in checks]}
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> int:
    """CLI entrypoint."""

    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    if args.write_sha256_manifest:
        write_sha256_manifest(root)
    checks = run_checks(root)
    if args.json:
        print_json(root, checks)
    else:
        print_text(root, checks)
    return 1 if any(check.status == "fail" for check in checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
