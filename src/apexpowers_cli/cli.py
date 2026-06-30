#!/usr/bin/env python3
"""ApexPowers profile installation and distribution CLI."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    from . import __version__
except ImportError:  # pragma: no cover - direct script execution.
    __version__ = "0.1.0"

MANAGED_BY = "ApexPowers apex CLI"
INSTALL_MANIFEST = Path(".apex") / "apexpowers-install.json"
PROFILE_MANIFEST = Path("registry") / "apexpowers-profiles.json"
HOST_TARGETS = ("codex", "claude")
PACK_TARGETS = ("codex-plugin", "claude-plugin", "skillpack", "local")
DEFAULT_TARGETS = ("codex", "claude")
SKIP_DIRS = {"__pycache__", ".git"}
SKIP_SUFFIXES = {".pyc", ".pyo"}


class CliError(RuntimeError):
    """User-facing CLI error."""


@dataclass(frozen=True)
class ProfileSelection:
    """Resolved profile contents."""

    names: tuple[str, ...]
    codex_skills: tuple[str, ...]
    claude_skills: tuple[str, ...]
    agents: tuple[str, ...]
    commands: tuple[str, ...]
    hooks: bool


@dataclass(frozen=True)
class CopyPlan:
    """One file copy managed by the profile installer."""

    kind: str
    source: Path
    destination: Path
    source_rel: str
    destination_rel: str
    source_hash: str
    action: str


@dataclass(frozen=True)
class RemovePlan:
    """One uninstall action."""

    kind: str
    destination: Path
    destination_rel: str
    action: str


def source_root() -> Path:
    """Resolve the ApexPowers source checkout used by this CLI."""

    env_root = os.environ.get("APEXPOWERS_ROOT")
    if env_root:
        root = Path(env_root).expanduser().resolve()
        if (root / PROFILE_MANIFEST).is_file():
            return root
        raise CliError(f"APEXPOWERS_ROOT does not point at an ApexPowers checkout: {root}")

    current = Path(__file__).resolve()
    for parent in (current.parent, *current.parents):
        if (parent / PROFILE_MANIFEST).is_file():
            return parent
    installed_root = Path(sys.prefix) / "share" / "apexpowers"
    if (installed_root / PROFILE_MANIFEST).is_file():
        return installed_root
    raise CliError("Cannot locate registry/apexpowers-profiles.json. Set APEXPOWERS_ROOT.")


def load_json_file(path: Path) -> dict[str, Any]:
    """Load a JSON object with a clear error."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CliError(f"Missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CliError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise CliError(f"JSON root must be an object: {path}")
    return payload


def load_registry(root: Path) -> dict[str, Any]:
    """Load and minimally validate the ApexPowers profile registry."""

    registry = load_json_file(root / PROFILE_MANIFEST)
    if registry.get("schemaVersion") != "apexpowers.profiles.v1":
        raise CliError("Profile registry schemaVersion must be apexpowers.profiles.v1.")
    profiles = registry.get("profiles")
    if not isinstance(profiles, dict) or not profiles:
        raise CliError("Profile registry must contain a non-empty profiles object.")
    return registry


def parse_csv(value: str | None, default: Iterable[str]) -> tuple[str, ...]:
    """Parse comma-separated CLI values."""

    raw = value if value is not None else ",".join(default)
    values = tuple(item.strip() for item in raw.split(",") if item.strip())
    if not values:
        raise CliError("Expected at least one value.")
    return values


def unique_extend(output: list[str], values: Iterable[str]) -> None:
    """Append unique values while preserving registry order."""

    seen = set(output)
    for value in values:
        if value not in seen:
            output.append(value)
            seen.add(value)


def require_name(value: str, field_name: str) -> str:
    """Validate a registry name before using it in paths."""

    if not value or value in {".", ".."} or "/" in value or "\\" in value:
        raise CliError(f"Invalid {field_name} name: {value!r}")
    return value


def string_list(profile_name: str, profile: dict[str, Any], field: str) -> tuple[str, ...]:
    """Return a validated string-list profile field."""

    raw = profile.get(field, [])
    if raw is None:
        return ()
    if not isinstance(raw, list) or not all(isinstance(item, str) and item for item in raw):
        raise CliError(f"Profile {profile_name}.{field} must be a list of strings.")
    return tuple(raw)


def resolve_profile_selection(registry: dict[str, Any], names: Iterable[str]) -> ProfileSelection:
    """Resolve selected profile names, including inherited fields."""

    profiles = registry["profiles"]
    selected = tuple(require_name(name, "profile") for name in names)
    codex_skills: list[str] = []
    claude_skills: list[str] = []
    agents: list[str] = []
    commands: list[str] = []
    hooks = False

    def visit(name: str, stack: tuple[str, ...]) -> None:
        nonlocal hooks
        if name in stack:
            raise CliError(f"Profile inheritance cycle: {' -> '.join((*stack, name))}")
        raw_profile = profiles.get(name)
        if not isinstance(raw_profile, dict):
            raise CliError(f"Unknown profile: {name}")
        for parent in string_list(name, raw_profile, "extends"):
            require_name(parent, "profile")
            visit(parent, (*stack, name))
        unique_extend(codex_skills, string_list(name, raw_profile, "codexSkills"))
        unique_extend(claude_skills, string_list(name, raw_profile, "claudeSkills"))
        unique_extend(agents, string_list(name, raw_profile, "agents"))
        unique_extend(commands, string_list(name, raw_profile, "commands"))
        hook_config = raw_profile.get("hooks", False)
        if isinstance(hook_config, dict):
            hooks = True
        elif hook_config not in (False, None):
            raise CliError(f"Profile {name}.hooks must be false or an object.")

    for selected_name in selected:
        visit(selected_name, ())

    return ProfileSelection(
        names=selected,
        codex_skills=tuple(codex_skills),
        claude_skills=tuple(claude_skills),
        agents=tuple(agents),
        commands=tuple(commands),
        hooks=hooks,
    )


def load_install_manifest(target_root: Path) -> dict[str, Any] | None:
    """Load the profile install manifest if present."""

    path = target_root / INSTALL_MANIFEST
    if not path.is_file():
        return None
    payload = load_json_file(path)
    if payload.get("managed_by") != MANAGED_BY:
        return None
    return payload


def manifest_records(manifest: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    """Return manifest records by destination relative path."""

    if not manifest:
        return {}
    files = manifest.get("files", [])
    if not isinstance(files, list):
        return {}
    records: dict[str, dict[str, Any]] = {}
    for item in files:
        if isinstance(item, dict) and isinstance(item.get("path"), str):
            records[item["path"].replace("\\", "/")] = item
    return records


def safe_destination(root: Path, rel_path: str) -> Path:
    """Resolve a destination path and keep it inside target root."""

    destination = (root / rel_path).resolve()
    try:
        destination.relative_to(root.resolve())
    except ValueError as exc:
        raise CliError(f"Destination escapes target root: {destination}") from exc
    return destination


def sha256_file(path: Path) -> str:
    """SHA-256 for exact file bytes."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_bytes(content: bytes) -> str:
    """SHA-256 for in-memory bytes."""

    return hashlib.sha256(content).hexdigest()


def source_relative(root: Path, path: Path) -> str:
    """Return a source-relative POSIX path."""

    return path.resolve().relative_to(root.resolve()).as_posix()


def should_skip(path: Path) -> bool:
    """Skip generated cache files in copied profile artifacts."""

    return any(part in SKIP_DIRS for part in path.parts) or path.suffix in SKIP_SUFFIXES


def iter_source_files(source: Path) -> list[Path]:
    """List source files for a managed artifact."""

    if source.is_file():
        return [source]
    return sorted(path for path in source.rglob("*") if path.is_file() and not should_skip(path))


def add_directory_plans(
    plans: dict[str, CopyPlan],
    source_root_path: Path,
    source: Path,
    destination_root: Path,
    target_root: Path,
    kind: str,
    records: dict[str, dict[str, Any]],
    force: bool,
) -> None:
    """Add copy plans for one source file or directory."""

    if not source.exists():
        raise CliError(f"Profile references missing {kind}: {source_relative(source_root_path, source)}")
    for source_file in iter_source_files(source):
        rel_inside = source_file.relative_to(source if source.is_dir() else source.parent)
        destination = destination_root / rel_inside if source.is_dir() else destination_root
        destination_rel = destination.resolve().relative_to(target_root.resolve()).as_posix()
        source_hash = sha256_file(source_file)
        action = copy_action(destination, source_hash, records.get(destination_rel), force)
        plans[destination_rel] = CopyPlan(
            kind=kind,
            source=source_file,
            destination=destination,
            source_rel=source_relative(source_root_path, source_file),
            destination_rel=destination_rel,
            source_hash=source_hash,
            action=action,
        )


def copy_action(destination: Path, source_hash: str, record: dict[str, Any] | None, force: bool) -> str:
    """Resolve the copy action for one file."""

    if not destination.exists():
        return "create"
    current_hash = sha256_file(destination)
    if current_hash == source_hash:
        return "unchanged"
    if force:
        return "overwrite"
    if record and record.get("sha256") == current_hash:
        return "update"
    if record:
        return "skip-modified"
    return "skip-existing"


def build_copy_plans(
    apex_root: Path,
    target_root: Path,
    selection: ProfileSelection,
    targets: tuple[str, ...],
    force: bool,
) -> list[CopyPlan]:
    """Build profile copy plans from selected profiles and targets."""

    target_root = target_root.resolve()
    records = manifest_records(load_install_manifest(target_root))
    plans: dict[str, CopyPlan] = {}

    if "codex" in targets:
        for skill in selection.codex_skills:
            skill = require_name(skill, "codex skill")
            add_directory_plans(
                plans,
                apex_root,
                apex_root / ".codex" / "skills" / skill,
                safe_destination(target_root, f".codex/skills/{skill}"),
                target_root,
                "codex-skill",
                records,
                force,
            )

    if "claude" in targets:
        for skill in selection.claude_skills:
            skill = require_name(skill, "claude skill")
            add_directory_plans(
                plans,
                apex_root,
                apex_root / ".claude" / "skills" / skill,
                safe_destination(target_root, f".claude/skills/{skill}"),
                target_root,
                "claude-skill",
                records,
                force,
            )

    if any(target in targets for target in HOST_TARGETS):
        for agent in selection.agents:
            agent = require_name(agent, "agent")
            add_directory_plans(
                plans,
                apex_root,
                apex_root / ".agents" / f"{agent}.md",
                safe_destination(target_root, f".agents/{agent}.md"),
                target_root,
                "agent-source",
                records,
                force,
            )
        for command in selection.commands:
            command = require_name(command, "command")
            add_directory_plans(
                plans,
                apex_root,
                apex_root / "commands" / f"{command}.toml",
                safe_destination(target_root, f"commands/{command}.toml"),
                target_root,
                "command",
                records,
                force,
            )

    return [plans[key] for key in sorted(plans)]


def write_copy_plans(plans: Iterable[CopyPlan]) -> None:
    """Apply copy plans."""

    for plan in plans:
        if plan.action not in {"create", "update", "overwrite"}:
            continue
        plan.destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(plan.source, plan.destination)


def manifest_payload(
    target_root: Path,
    selection: ProfileSelection,
    targets: tuple[str, ...],
    plans: Iterable[CopyPlan],
    previous: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build an install manifest payload."""

    previous_records = manifest_records(previous)
    next_records = dict(previous_records)
    for plan in plans:
        if plan.action in {"skip-existing", "skip-modified"}:
            continue
        next_records[plan.destination_rel] = {
            "path": plan.destination_rel,
            "kind": plan.kind,
            "source": plan.source_rel,
            "sha256": plan.source_hash,
        }

    previous_profiles = tuple(previous.get("profiles", [])) if previous and isinstance(previous.get("profiles"), list) else ()
    previous_targets = tuple(previous.get("targets", [])) if previous and isinstance(previous.get("targets"), list) else ()
    profiles = tuple(dict.fromkeys((*previous_profiles, *selection.names)))
    merged_targets = tuple(dict.fromkeys((*previous_targets, *targets)))
    return {
        "schemaVersion": "apexpowers.install.v1",
        "managed_by": MANAGED_BY,
        "profiles": list(profiles),
        "targets": list(merged_targets),
        "files": [next_records[key] for key in sorted(next_records)],
    }


def write_install_manifest(target_root: Path, payload: dict[str, Any]) -> str:
    """Write the profile install manifest and return the action."""

    manifest_path = target_root / INSTALL_MANIFEST
    content = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if manifest_path.exists() and manifest_path.read_text(encoding="utf-8", errors="ignore") == content:
        return "unchanged"
    action = "update" if manifest_path.exists() else "create"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(content, encoding="utf-8", newline="\n")
    return action


def install_or_update(args: argparse.Namespace, operation: str) -> int:
    """Install or update selected profiles."""

    apex_root = source_root()
    registry = load_registry(apex_root)
    target_root = Path(args.root).expanduser().resolve()
    if not target_root.is_dir():
        raise CliError(f"Target root is not a directory: {target_root}")

    previous = load_install_manifest(target_root)
    default_profiles = previous.get("profiles", [registry.get("defaultProfile", "core")]) if previous and operation == "update" else [registry.get("defaultProfile", "core")]
    default_targets = previous.get("targets", DEFAULT_TARGETS) if previous and operation == "update" else DEFAULT_TARGETS
    profile_names = parse_csv(args.profile, default_profiles)
    targets = normalize_targets(parse_csv(args.target, default_targets))
    ensure_project_scope(args.scope)
    selection = resolve_profile_selection(registry, profile_names)
    plans = build_copy_plans(apex_root, target_root, selection, targets, args.force)

    if args.write:
        write_copy_plans(plans)
    manifest = manifest_payload(target_root, selection, targets, plans, previous)
    manifest_action = "absent"
    if args.write:
        manifest_action = write_install_manifest(target_root, manifest)
    elif plans:
        manifest_action = "create" if previous is None else "update"

    subprocess_results = []
    if args.write and selection.agents:
        subprocess_results.append(run_sync_agents(apex_root, target_root, targets, args.write, args.force, args.json))
    elif selection.agents:
        subprocess_results.append(sync_agents_preview(selection, targets))
    if selection.hooks:
        subprocess_results.append(run_hooks(apex_root, target_root, operation, args))

    payload = {
        "operation": operation,
        "root": str(target_root),
        "profiles": list(selection.names),
        "targets": list(targets),
        "scope": args.scope,
        "write": args.write,
        "results": [copy_plan_dict(plan) for plan in plans],
        "manifest": {"path": INSTALL_MANIFEST.as_posix(), "action": manifest_action},
        "subprocesses": subprocess_results,
    }
    return emit_payload(payload, args.json, subprocess_exit_code(subprocess_results))


def normalize_targets(targets: tuple[str, ...]) -> tuple[str, ...]:
    """Validate and normalize host targets."""

    output: list[str] = []
    for target in targets:
        if target in {"all", "auto"}:
            for item in HOST_TARGETS:
                if item not in output:
                    output.append(item)
            continue
        if target not in HOST_TARGETS:
            raise CliError(f"Unsupported install target: {target}. Expected codex, claude, auto, or all.")
        if target not in output:
            output.append(target)
    return tuple(output)


def normalize_pack_targets(targets: tuple[str, ...]) -> tuple[str, ...]:
    """Validate pack artifact targets."""

    output: list[str] = []
    for target in targets:
        if target == "all":
            for item in PACK_TARGETS:
                if item not in output:
                    output.append(item)
            continue
        if target not in PACK_TARGETS:
            raise CliError(f"Unsupported pack target: {target}. Expected codex-plugin, claude-plugin, skillpack, local, or all.")
        if target not in output:
            output.append(target)
    return tuple(output)


def ensure_project_scope(scope: str) -> None:
    """Validate profile installation scope."""

    if scope != "project":
        raise CliError("Only --scope project is currently supported for profile installs.")


def copy_plan_dict(plan: CopyPlan) -> dict[str, Any]:
    """Serialize a copy plan."""

    return {
        "kind": plan.kind,
        "path": plan.destination_rel,
        "source": plan.source_rel,
        "action": plan.action,
    }


def run_subprocess(command: list[str], cwd: Path) -> dict[str, Any]:
    """Run a child command and capture stable output."""

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
    parsed_stdout: Any = None
    if result.stdout.strip():
        try:
            parsed_stdout = json.loads(result.stdout)
        except json.JSONDecodeError:
            parsed_stdout = result.stdout
    return {
        "command": command,
        "returncode": result.returncode,
        "stdout": parsed_stdout,
        "stderr": result.stderr,
    }


def run_sync_agents(apex_root: Path, target_root: Path, targets: tuple[str, ...], write: bool, force: bool, json_output: bool) -> dict[str, Any]:
    """Delegate agent mirror generation to the existing sync script."""

    sync_target = "all" if set(targets) == set(HOST_TARGETS) else targets[0]
    command = [
        sys.executable,
        str(apex_root / ".codex" / "skills" / "apex-sync-agent-mirrors" / "scripts" / "sync_agent_mirrors.py"),
        str(target_root),
        "--target",
        sync_target,
        "--json",
    ]
    if write:
        command.append("--write")
    if force:
        command.append("--force")
    result = run_subprocess(command, target_root)
    result["name"] = "sync-agents"
    return result


def sync_agents_preview(selection: ProfileSelection, targets: tuple[str, ...]) -> dict[str, Any]:
    """Preview mirror sync without requiring dry-run files to exist first."""

    results = []
    for agent in selection.agents:
        if "codex" in targets:
            results.append({"path": f".codex/agents/{agent}.toml", "action": "plan"})
        if "claude" in targets:
            results.append({"path": f".claude/agents/{agent}.md", "action": "plan"})
    return {
        "name": "sync-agents",
        "returncode": 0,
        "stdout": {"write": False, "results": results},
        "stderr": "",
    }


def run_hooks(apex_root: Path, target_root: Path, operation: str, args: argparse.Namespace) -> dict[str, Any]:
    """Delegate hook lifecycle to the existing manifest-aware installer."""

    command = [
        sys.executable,
        str(apex_root / ".codex" / "skills" / "apex-init-project-hooks" / "scripts" / "init_project_hooks.py"),
        str(target_root),
        "--hook-scope",
        args.hook_scope,
        "--json",
    ]
    if operation == "update":
        command.append("--update")
    elif operation == "uninstall":
        command.append("--uninstall")
    if args.write:
        command.append("--write")
    if args.force:
        command.append("--force")
    if args.codex_home:
        command.extend(["--codex-home", args.codex_home])
    if args.claude_home:
        command.extend(["--claude-home", args.claude_home])
    if args.codex_config_format:
        command.extend(["--codex-config-format", args.codex_config_format])
    result = run_subprocess(command, target_root)
    result["name"] = "hooks"
    return result


def uninstall(args: argparse.Namespace) -> int:
    """Uninstall selected profile artifacts."""

    apex_root = source_root()
    registry = load_registry(apex_root)
    target_root = Path(args.root).expanduser().resolve()
    if not target_root.is_dir():
        raise CliError(f"Target root is not a directory: {target_root}")
    previous = load_install_manifest(target_root)
    default_profiles = previous.get("profiles", [registry.get("defaultProfile", "core")]) if previous else [registry.get("defaultProfile", "core")]
    default_targets = previous.get("targets", DEFAULT_TARGETS) if previous else DEFAULT_TARGETS
    profile_names = parse_csv(args.profile, default_profiles)
    targets = normalize_targets(parse_csv(args.target, default_targets))
    ensure_project_scope(args.scope)
    selection = resolve_profile_selection(registry, profile_names)
    copy_plans = build_copy_plans(apex_root, target_root, selection, targets, args.force)
    remove_plans = build_remove_plans(target_root, copy_plans, previous, args.force)
    mirror_plans = build_agent_mirror_remove_plans(target_root, selection, targets, args.force)
    all_remove_plans = [*remove_plans, *mirror_plans]

    if args.write:
        for plan in all_remove_plans:
            if plan.action == "remove-managed":
                plan.destination.unlink()

    manifest_action = update_manifest_after_uninstall(target_root, all_remove_plans, previous, args.write)
    subprocess_results = []
    if selection.hooks:
        subprocess_results.append(run_hooks(apex_root, target_root, "uninstall", args))

    payload = {
        "operation": "uninstall",
        "root": str(target_root),
        "profiles": list(selection.names),
        "targets": list(targets),
        "scope": args.scope,
        "write": args.write,
        "results": [remove_plan_dict(plan) for plan in all_remove_plans],
        "manifest": {"path": INSTALL_MANIFEST.as_posix(), "action": manifest_action},
        "subprocesses": subprocess_results,
    }
    return emit_payload(payload, args.json, subprocess_exit_code(subprocess_results))


def build_remove_plans(target_root: Path, copy_plans: Iterable[CopyPlan], manifest: dict[str, Any] | None, force: bool) -> list[RemovePlan]:
    """Build uninstall plans for copied profile files."""

    records = manifest_records(manifest)
    plans: list[RemovePlan] = []
    for copy_plan in copy_plans:
        destination = copy_plan.destination
        record = records.get(copy_plan.destination_rel)
        if not destination.exists():
            action = "absent"
        elif force:
            action = "remove-managed"
        elif record and record.get("sha256") == sha256_file(destination):
            action = "remove-managed"
        elif record:
            action = "skip-modified"
        else:
            action = "skip-unmanaged"
        plans.append(RemovePlan(copy_plan.kind, destination, copy_plan.destination_rel, action))
    return plans


def build_agent_mirror_remove_plans(target_root: Path, selection: ProfileSelection, targets: tuple[str, ...], force: bool) -> list[RemovePlan]:
    """Remove generated mirrors for selected agents when safe."""

    plans: list[RemovePlan] = []
    for agent in selection.agents:
        agent = require_name(agent, "agent")
        candidates: list[tuple[str, Path]] = []
        if "codex" in targets:
            candidates.append(("codex-agent-mirror", safe_destination(target_root, f".codex/agents/{agent}.toml")))
        if "claude" in targets:
            candidates.append(("claude-agent-mirror", safe_destination(target_root, f".claude/agents/{agent}.md")))
        for kind, destination in candidates:
            rel_path = destination.relative_to(target_root).as_posix()
            if not destination.exists():
                action = "absent"
            else:
                text = destination.read_text(encoding="utf-8", errors="ignore")
                action = "remove-managed" if force or "Generated from ApexPowers .agents source template" in text else "skip-existing"
            plans.append(RemovePlan(kind, destination, rel_path, action))
    return plans


def update_manifest_after_uninstall(target_root: Path, plans: Iterable[RemovePlan], manifest: dict[str, Any] | None, write: bool) -> str:
    """Update or remove the profile install manifest after uninstall."""

    if not manifest:
        return "absent"
    removed = {plan.destination_rel for plan in plans if plan.action == "remove-managed"}
    records = [item for item in manifest.get("files", []) if not (isinstance(item, dict) and item.get("path") in removed)]
    manifest_path = target_root / INSTALL_MANIFEST
    if not records:
        if write and manifest_path.exists():
            manifest_path.unlink()
        return "remove-manifest"
    next_payload = dict(manifest)
    next_payload["files"] = records
    content = json.dumps(next_payload, ensure_ascii=False, indent=2) + "\n"
    if manifest_path.exists() and manifest_path.read_text(encoding="utf-8", errors="ignore") == content:
        return "unchanged"
    if write:
        manifest_path.write_text(content, encoding="utf-8", newline="\n")
    return "update"


def remove_plan_dict(plan: RemovePlan) -> dict[str, Any]:
    """Serialize a remove plan."""

    return {"kind": plan.kind, "path": plan.destination_rel, "action": plan.action}


def doctor(args: argparse.Namespace) -> int:
    """Run the read-only doctor script."""

    apex_root = source_root()
    target_root = Path(args.root).expanduser().resolve()
    command = [
        sys.executable,
        str(apex_root / ".codex" / "skills" / "apex-doctor" / "scripts" / "apex_doctor.py"),
        str(target_root),
    ]
    if args.codex_home:
        command.extend(["--codex-home", args.codex_home])
    if args.claude_home:
        command.extend(["--claude-home", args.claude_home])
    if args.json:
        command.append("--json")
    result = subprocess.run(command, text=True, encoding="utf-8", errors="replace", check=False)
    return result.returncode


def profile(args: argparse.Namespace) -> int:
    """Show profile registry data."""

    apex_root = source_root()
    registry = load_registry(apex_root)
    profiles = registry["profiles"]
    if args.profile_command == "list":
        payload = {
            "defaultProfile": registry.get("defaultProfile"),
            "profiles": [
                {"name": name, "description": profile.get("description", "")}
                for name, profile in sorted(profiles.items())
                if isinstance(profile, dict)
            ],
        }
    else:
        name = require_name(args.name, "profile")
        if name not in profiles:
            raise CliError(f"Unknown profile: {name}")
        selection = resolve_profile_selection(registry, (name,))
        payload = {
            "name": name,
            "profile": profiles[name],
            "resolved": {
                "codexSkills": list(selection.codex_skills),
                "claudeSkills": list(selection.claude_skills),
                "agents": list(selection.agents),
                "commands": list(selection.commands),
                "hooks": selection.hooks,
            },
        }
    return emit_payload(payload, args.json)


def version(args: argparse.Namespace) -> int:
    """Print CLI and plugin versions."""

    apex_root = source_root()
    plugin = load_json_file(apex_root / ".codex-plugin" / "plugin.json")
    payload = {"cli": __version__, "plugin": plugin.get("version", "unknown")}
    return emit_payload(payload, args.json)


def friendly_install_args(args: argparse.Namespace, profile: str | None = None) -> argparse.Namespace:
    """Build an install/update namespace for user-facing shortcut commands."""

    return argparse.Namespace(
        root=args.root,
        profile=profile if profile is not None else args.profile,
        target=args.target,
        scope="project",
        hook_scope=args.hook_scope,
        codex_home=args.codex_home,
        claude_home=args.claude_home,
        codex_config_format=args.codex_config_format,
        dry_run=args.dry_run,
        write=args.write,
        force=args.force,
        json=args.json,
    )


def init_project(args: argparse.Namespace) -> int:
    """Initialize the current project with the public default profile."""

    install_args = friendly_install_args(args, args.profile or "core")
    return install_or_update(install_args, "init")


def add_profile(args: argparse.Namespace) -> int:
    """Add one or more profiles with a short command shape."""

    install_args = friendly_install_args(args, args.profile)
    return install_or_update(install_args, "add")


def remove_profile(args: argparse.Namespace) -> int:
    """Remove installed profile artifacts with a short command shape."""

    remove_args = friendly_install_args(args, args.profile)
    return uninstall(remove_args)


def sync_shortcut(args: argparse.Namespace) -> int:
    """Sync agent mirrors with a short command shape."""

    sync_args = argparse.Namespace(
        root=args.root,
        target=args.target,
        dry_run=args.dry_run,
        write=args.write,
        force=args.force,
        json=args.json,
    )
    return sync_agents(sync_args)


def hooks_explain(args: argparse.Namespace) -> int:
    """Explain the hook trust model without writing files."""

    payload = {
        "operation": "hooks-explain",
        "root": str(Path(args.root).expanduser().resolve()),
        "writesByDefault": False,
        "defaultMode": "dry-run",
        "summary": [
            "ApexPowers never installs lifecycle hooks through plugin manifests.",
            "Hook installation is opt-in and manifest-managed.",
            "Run `apex hooks install --dry-run` before `apex hooks install --write`.",
            "Run `apex hooks uninstall --write` to remove Apex-managed hook entries.",
        ],
        "managedLocations": {
            "codex": "Codex home config plus hooks/apex_loop.py",
            "claude": "Claude Code settings plus hooks/apex_loop.py",
            "project": "tasks/loops, tasks/reviews, and tasks/lessons.md",
        },
    }
    return emit_payload(payload, args.json)


def pack(args: argparse.Namespace) -> int:
    """Pack a profile-specific artifact directory."""

    apex_root = source_root()
    registry = load_registry(apex_root)
    profile_names = parse_csv(args.profile, [registry.get("defaultProfile", "core")])
    pack_targets = normalize_pack_targets(parse_csv(args.target, ("codex-plugin",)))
    selection = resolve_profile_selection(registry, profile_names)
    output_dir = Path(args.output).expanduser().resolve()
    results = []
    for target in pack_targets:
        artifact_dir, entries = pack_entries(apex_root, registry, selection, target, output_dir)
        action = artifact_action(artifact_dir, args.force)
        if not args.dry_run and action != "skip-existing":
            write_artifact_dir(artifact_dir, entries, args.force)
        results.append(
            {
                "target": target,
                "path": str(artifact_dir),
                "action": action if not args.dry_run else ("create" if not artifact_dir.exists() else action),
                "entry_count": len(entries),
            }
        )
    payload = {"operation": "pack", "profiles": list(selection.names), "dry_run": args.dry_run, "results": results}
    return emit_payload(payload, args.json)


def pack_entries(apex_root: Path, registry: dict[str, Any], selection: ProfileSelection, target: str, output_dir: Path) -> tuple[Path, dict[str, bytes]]:
    """Build artifact directory entries for one target."""

    profile_slug = "-".join(selection.names)
    artifact_dir = output_dir / f"apexpowers-{profile_slug}.{target}"
    entries: dict[str, bytes] = {}
    if target == "codex-plugin":
        plugin = load_json_file(apex_root / ".codex-plugin" / "plugin.json")
        plugin["skills"] = "./skills/"
        entries["plugin.json"] = json.dumps(plugin, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
        for skill in selection.codex_skills:
            add_artifact_tree(entries, apex_root / ".codex" / "skills" / require_name(skill, "codex skill"), f"skills/{skill}")
    elif target == "claude-plugin":
        plugin = load_json_file(apex_root / ".claude-plugin" / "plugin.json")
        plugin["skills"] = ["./skills/"]
        plugin["commands"] = ["./commands/"]
        entries["plugin.json"] = json.dumps(plugin, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
        for skill in selection.claude_skills:
            add_artifact_tree(entries, apex_root / ".claude" / "skills" / require_name(skill, "claude skill"), f"skills/{skill}")
        for command in selection.commands:
            command = require_name(command, "command")
            source = apex_root / "commands" / f"{command}.toml"
            if source.is_file():
                entries[f"commands/{command}.toml"] = source.read_bytes()
    elif target == "skillpack":
        for skill in selection.codex_skills:
            add_artifact_tree(entries, apex_root / ".codex" / "skills" / require_name(skill, "codex skill"), f"skills/{skill}")
        for command in selection.commands:
            command = require_name(command, "command")
            source = apex_root / "commands" / f"{command}.toml"
            if source.is_file():
                entries[f"commands/{command}.toml"] = source.read_bytes()
    elif target == "local":
        for skill in selection.codex_skills:
            add_artifact_tree(entries, apex_root / ".codex" / "skills" / require_name(skill, "codex skill"), f".codex/skills/{skill}")
        for skill in selection.claude_skills:
            add_artifact_tree(entries, apex_root / ".claude" / "skills" / require_name(skill, "claude skill"), f".claude/skills/{skill}")
        for agent in selection.agents:
            agent = require_name(agent, "agent")
            entries[f".agents/{agent}.md"] = (apex_root / ".agents" / f"{agent}.md").read_bytes()
        for command in selection.commands:
            command = require_name(command, "command")
            source = apex_root / "commands" / f"{command}.toml"
            if source.is_file():
                entries[f"commands/{command}.toml"] = source.read_bytes()
    entries["registry/apexpowers-profiles.json"] = (apex_root / PROFILE_MANIFEST).read_bytes()
    entries["NOTICE.md"] = (apex_root / "NOTICE.md").read_bytes()
    add_artifact_metadata(entries, registry, selection, target, artifact_dir.name)
    return artifact_dir, entries


def add_artifact_tree(entries: dict[str, bytes], source: Path, archive_root: str) -> None:
    """Add a source directory tree to artifact entries."""

    if not source.exists():
        raise CliError(f"Pack source is missing: {source}")
    for file_path in iter_source_files(source):
        rel = file_path.relative_to(source).as_posix()
        entries[f"{archive_root}/{rel}"] = file_path.read_bytes()


def add_artifact_metadata(entries: dict[str, bytes], registry: dict[str, Any], selection: ProfileSelection, target: str, artifact_name: str) -> None:
    """Add manifest, checksums, SBOM-lite, instructions, and expected doctor output."""

    plugin_version = load_json_file(source_root() / ".codex-plugin" / "plugin.json").get("version", "unknown")
    doctor_expected = {
        "command": "apex doctor --json",
        "expected": {"summary": {"fail": 0}},
        "notes": [
            "Warnings are acceptable before hooks are explicitly installed.",
            "Malformed Apex-managed manifests, runtime files, or host config should produce fail > 0.",
        ],
    }
    install_text = install_instructions(selection, target)
    sbom = {
        "schemaVersion": "apexpowers.sbom-lite.v1",
        "name": artifact_name,
        "profiles": list(selection.names),
        "target": target,
        "components": [
            {
                "path": path,
                "sha256": sha256_bytes(content),
                "bytes": len(content),
                "kind": component_kind(path),
            }
            for path, content in sorted(entries.items())
        ],
    }
    manifest = {
        "schemaVersion": "apexpowers.artifact.v1",
        "name": artifact_name,
        "profiles": list(selection.names),
        "target": target,
        "pluginVersion": plugin_version,
        "registrySchemaVersion": registry.get("schemaVersion"),
        "managedBy": MANAGED_BY,
        "contents": {
            "codexSkills": list(selection.codex_skills),
            "claudeSkills": list(selection.claude_skills),
            "agents": list(selection.agents),
            "commands": list(selection.commands),
            "hooks": selection.hooks,
        },
        "install": {"instructions": "INSTALL.md"},
        "doctorExpectedOutput": "doctor-expected-output.json",
        "sbomLite": "SBOM-lite.json",
        "files": [
            {"path": path, "sha256": sha256_bytes(content), "bytes": len(content)}
            for path, content in sorted(entries.items())
        ],
    }
    entries["doctor-expected-output.json"] = json.dumps(doctor_expected, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    entries["INSTALL.md"] = install_text.encode("utf-8")
    entries["SBOM-lite.json"] = json.dumps(sbom, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    entries["manifest.json"] = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    entries["SHA256SUMS"] = sha256sums(entries).encode("utf-8")


def install_instructions(selection: ProfileSelection, target: str) -> str:
    """Render artifact-local install instructions."""

    profiles = ",".join(selection.names)
    lines = [
        "# Install ApexPowers Artifact",
        "",
        f"- Profiles: `{profiles}`",
        f"- Artifact target: `{target}`",
        "",
        "Recommended CLI flow from an ApexPowers checkout:",
        "",
        "```powershell",
        f"apex install --profile {profiles} --target codex,claude --scope project --dry-run",
        f"apex install --profile {profiles} --target codex,claude --scope project --write",
        "apex doctor --json",
        "```",
        "",
        "Hooks remain opt-in and are installed only through the manifest-aware hook installer.",
    ]
    return "\n".join(lines) + "\n"


def component_kind(path: str) -> str:
    """Classify one artifact entry for SBOM-lite output."""

    if path.startswith("skills/") or "/skills/" in path:
        return "skill"
    if path.startswith("commands/"):
        return "command"
    if path.startswith(".agents/"):
        return "agent-source"
    if path == "plugin.json":
        return "plugin-manifest"
    if path.startswith("registry/"):
        return "registry"
    return "metadata"


def sha256sums(entries: dict[str, bytes]) -> str:
    """Render SHA256SUMS for artifact entries except the checksum file."""

    lines = []
    for path in sorted(entries):
        if path == "SHA256SUMS":
            continue
        lines.append(f"{sha256_bytes(entries[path])}  {path}")
    return "\n".join(lines) + "\n"


def artifact_action(path: Path, force: bool) -> str:
    """Resolve artifact write action."""

    if not path.exists():
        return "create"
    return "overwrite" if force else "skip-existing"


def write_artifact_dir(artifact_dir: Path, entries: dict[str, bytes], force: bool) -> None:
    """Write artifact entries to a directory."""

    if artifact_dir.exists():
        if not force:
            return
        if artifact_dir.is_dir():
            shutil.rmtree(artifact_dir)
        else:
            artifact_dir.unlink()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    for rel_path, content in sorted(entries.items()):
        path = artifact_dir / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def hooks(args: argparse.Namespace) -> int:
    """Run hook installer subcommands directly."""

    apex_root = source_root()
    target_root = Path(args.root).expanduser().resolve()
    if not target_root.is_dir():
        raise CliError(f"Target root is not a directory: {target_root}")
    operation = args.hooks_command
    result = run_hooks(apex_root, target_root, operation, args)
    payload = {"operation": f"hooks-{operation}", "root": str(target_root), "subprocesses": [result]}
    return emit_payload(payload, args.json, int(result["returncode"]))


def sync_agents(args: argparse.Namespace) -> int:
    """Run agent mirror sync directly."""

    apex_root = source_root()
    target_root = Path(args.root).expanduser().resolve()
    if not target_root.is_dir():
        raise CliError(f"Target root is not a directory: {target_root}")
    targets = normalize_targets(parse_csv(args.target, DEFAULT_TARGETS))
    result = run_sync_agents(apex_root, target_root, targets, args.write, args.force, args.json)
    payload = {"operation": "sync-agents", "root": str(target_root), "targets": list(targets), "subprocesses": [result]}
    return emit_payload(payload, args.json, int(result["returncode"]))


def subprocess_exit_code(results: Iterable[dict[str, Any]]) -> int:
    """Return the first failing subprocess exit code, or zero."""

    for result in results:
        returncode = int(result.get("returncode", 0))
        if returncode != 0:
            return returncode
    return 0


def emit_payload(payload: dict[str, Any], json_output: bool, exit_code: int = 0) -> int:
    """Print JSON or compact text output."""

    if json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_text_payload(payload)
    return exit_code


def print_text_payload(payload: dict[str, Any]) -> None:
    """Render a human-readable summary for common payloads."""

    operation = payload.get("operation")
    if operation:
        print(f"Apex {operation}: {payload.get('root', '')}".rstrip())
    if "defaultProfile" in payload:
        print(f"Default profile: {payload['defaultProfile']}")
        for profile_item in payload.get("profiles", []):
            print(f"- {profile_item['name']}: {profile_item.get('description', '')}")
        return
    if "resolved" in payload:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if "cli" in payload:
        print(f"apex CLI {payload['cli']} (plugin {payload['plugin']})")
        return
    for result in payload.get("results", []):
        path = result.get("path", "")
        kind = result.get("kind", result.get("target", "item"))
        print(f"{kind} {result.get('action')}: {path}")
    manifest = payload.get("manifest")
    if isinstance(manifest, dict):
        print(f"manifest {manifest.get('action')}: {manifest.get('path')}")
    for child in payload.get("subprocesses", []):
        print(f"{child.get('name', 'subprocess')} exit={child.get('returncode')}")


def add_common_install_args(parser: argparse.ArgumentParser) -> None:
    """Add common profile lifecycle arguments."""

    parser.add_argument("root", nargs="?", default=".", help="Target project root. Defaults to current directory.")
    parser.add_argument("--profile", help="Comma-separated profile names. Defaults to registry default or installed manifest.")
    parser.add_argument("--target", help="Comma-separated targets: codex, claude, auto, or all. Defaults to codex,claude.")
    parser.add_argument("--scope", choices=["project"], default="project", help="Install profile artifacts into the target project.")
    parser.add_argument("--hook-scope", choices=["agent", "project"], default="agent", help="Hook installer scope when selected profiles include hooks.")
    parser.add_argument("--codex-home", help="Codex agent home passed to hook installer or doctor.")
    parser.add_argument("--claude-home", help="Claude Code home passed to hook installer or doctor.")
    parser.add_argument("--codex-config-format", choices=["auto", "toml", "json"], help="Codex hook config format passed to hook installer.")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing. This is the default.")
    parser.add_argument("--write", action="store_true", help="Write changes. Default is dry-run.")
    parser.add_argument("--force", action="store_true", help="Overwrite managed or conflicting files when supported.")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON.")


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser."""

    parser = argparse.ArgumentParser(prog="apex", description="ApexPowers profile installer and distribution CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Initialize a project with the default ApexPowers workflow.")
    init_parser.add_argument("root", nargs="?", default=".", help="Target project root. Defaults to current directory.")
    init_parser.add_argument("--profile", help="Comma-separated profile names. Defaults to core.")
    init_parser.add_argument("--target", default="auto", help="Comma-separated targets: codex, claude, auto, or all. Defaults to auto.")
    init_parser.add_argument("--hook-scope", choices=["agent", "project"], default="agent")
    init_parser.add_argument("--codex-home")
    init_parser.add_argument("--claude-home")
    init_parser.add_argument("--codex-config-format", choices=["auto", "toml", "json"])
    init_parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing. This is the default.")
    init_parser.add_argument("--write", action="store_true", help="Write changes. Default is dry-run.")
    init_parser.add_argument("--force", action="store_true")
    init_parser.add_argument("--json", action="store_true")
    init_parser.set_defaults(func=init_project)

    add_parser = subparsers.add_parser("add", help="Add one or more ApexPowers profiles.")
    add_parser.add_argument("profile", help="Comma-separated profile names, for example frontend or planning,research.")
    add_parser.add_argument("root", nargs="?", default=".", help="Target project root. Defaults to current directory.")
    add_parser.add_argument("--target", default="auto", help="Comma-separated targets: codex, claude, auto, or all. Defaults to auto.")
    add_parser.add_argument("--hook-scope", choices=["agent", "project"], default="agent")
    add_parser.add_argument("--codex-home")
    add_parser.add_argument("--claude-home")
    add_parser.add_argument("--codex-config-format", choices=["auto", "toml", "json"])
    add_parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing. This is the default.")
    add_parser.add_argument("--write", action="store_true")
    add_parser.add_argument("--force", action="store_true")
    add_parser.add_argument("--json", action="store_true")
    add_parser.set_defaults(func=add_profile)

    remove_parser = subparsers.add_parser("remove", help="Remove ApexPowers profile artifacts.")
    remove_parser.add_argument("profile", nargs="?", help="Comma-separated profile names. Defaults to installed profiles.")
    remove_parser.add_argument("root", nargs="?", default=".", help="Target project root. Defaults to current directory.")
    remove_parser.add_argument("--target", default="auto", help="Comma-separated targets: codex, claude, auto, or all. Defaults to auto.")
    remove_parser.add_argument("--hook-scope", choices=["agent", "project"], default="agent")
    remove_parser.add_argument("--codex-home")
    remove_parser.add_argument("--claude-home")
    remove_parser.add_argument("--codex-config-format", choices=["auto", "toml", "json"])
    remove_parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing. This is the default.")
    remove_parser.add_argument("--write", action="store_true")
    remove_parser.add_argument("--force", action="store_true")
    remove_parser.add_argument("--json", action="store_true")
    remove_parser.set_defaults(func=remove_profile)

    sync_short_parser = subparsers.add_parser("sync", help="Sync official agent mirrors from .agents sources.")
    sync_short_parser.add_argument("root", nargs="?", default=".", help="Target project root. Defaults to current directory.")
    sync_short_parser.add_argument("--target", default="auto", help="Comma-separated targets: codex, claude, auto, or all. Defaults to auto.")
    sync_short_parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing. This is the default.")
    sync_short_parser.add_argument("--write", action="store_true")
    sync_short_parser.add_argument("--force", action="store_true")
    sync_short_parser.add_argument("--json", action="store_true")
    sync_short_parser.set_defaults(func=sync_shortcut)

    install_parser = subparsers.add_parser("install", help="Install one or more ApexPowers profiles.")
    add_common_install_args(install_parser)
    install_parser.set_defaults(func=lambda args: install_or_update(args, "install"))

    update_parser = subparsers.add_parser("update", help="Update installed ApexPowers profiles.")
    add_common_install_args(update_parser)
    update_parser.set_defaults(func=lambda args: install_or_update(args, "update"))

    uninstall_parser = subparsers.add_parser("uninstall", help="Uninstall ApexPowers profile artifacts.")
    add_common_install_args(uninstall_parser)
    uninstall_parser.set_defaults(func=uninstall)

    doctor_parser = subparsers.add_parser("doctor", help="Run ApexPowers doctor.")
    doctor_parser.add_argument("root", nargs="?", default=".", help="Target project root. Defaults to current directory.")
    doctor_parser.add_argument("--codex-home", help="Codex agent home.")
    doctor_parser.add_argument("--claude-home", help="Claude Code home.")
    doctor_parser.add_argument("--json", action="store_true", help="Output machine-readable JSON.")
    doctor_parser.set_defaults(func=doctor)

    profile_parser = subparsers.add_parser("profile", help="Inspect profile registry.")
    profile_subparsers = profile_parser.add_subparsers(dest="profile_command", required=True)
    profile_list = profile_subparsers.add_parser("list", help="List available profiles.")
    profile_list.add_argument("--json", action="store_true", help="Output machine-readable JSON.")
    profile_list.set_defaults(func=profile)
    profile_show = profile_subparsers.add_parser("show", help="Show one resolved profile.")
    profile_show.add_argument("name", help="Profile name.")
    profile_show.add_argument("--json", action="store_true", help="Output machine-readable JSON.")
    profile_show.set_defaults(func=profile)

    pack_parser = subparsers.add_parser("pack", help="Pack profile-specific artifact directories.")
    pack_parser.add_argument("--profile", help="Comma-separated profile names. Defaults to core.")
    pack_parser.add_argument("--target", help="Pack target: codex-plugin, claude-plugin, skillpack, local, or all.")
    pack_parser.add_argument("--output", default="dist", help="Output directory. Defaults to dist.")
    pack_parser.add_argument("--dry-run", action="store_true", help="Preview without writing artifact directories.")
    pack_parser.add_argument("--force", action="store_true", help="Overwrite existing artifact directories.")
    pack_parser.add_argument("--json", action="store_true", help="Output machine-readable JSON.")
    pack_parser.set_defaults(func=pack)

    hooks_parser = subparsers.add_parser("hooks", help="Run hook installer directly.")
    hooks_subparsers = hooks_parser.add_subparsers(dest="hooks_command", required=True)
    explain_hooks = hooks_subparsers.add_parser("explain", help="Explain hook trust boundaries without writing files.")
    explain_hooks.add_argument("root", nargs="?", default=".", help="Target project root.")
    explain_hooks.add_argument("--json", action="store_true")
    explain_hooks.set_defaults(func=hooks_explain)
    for name in ("install", "update", "uninstall"):
        child = hooks_subparsers.add_parser(name, help=f"{name.title()} hooks through apex-init-project-hooks.")
        child.add_argument("root", nargs="?", default=".", help="Target project root.")
        child.add_argument("--hook-scope", choices=["agent", "project"], default="agent")
        child.add_argument("--codex-home")
        child.add_argument("--claude-home")
        child.add_argument("--codex-config-format", choices=["auto", "toml", "json"])
        child.add_argument("--dry-run", action="store_true", help="Preview changes without writing. This is the default.")
        child.add_argument("--write", action="store_true")
        child.add_argument("--force", action="store_true")
        child.add_argument("--json", action="store_true")
        child.set_defaults(func=hooks)

    for sync_name in ("sync-agent-mirrors", "sync-agents"):
        sync_parser = subparsers.add_parser(sync_name, help="Generate official agent mirrors from .agents sources.")
        sync_parser.add_argument("root", nargs="?", default=".", help="Target project root.")
        sync_parser.add_argument("--target", help="Comma-separated targets: codex, claude, auto, or all.")
        sync_parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing. This is the default.")
        sync_parser.add_argument("--write", action="store_true")
        sync_parser.add_argument("--force", action="store_true")
        sync_parser.add_argument("--json", action="store_true")
        sync_parser.set_defaults(func=sync_agents)

    version_parser = subparsers.add_parser("version", help="Print CLI and plugin versions.")
    version_parser.add_argument("--json", action="store_true")
    version_parser.set_defaults(func=version)

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except CliError as exc:
        print(f"apex: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
