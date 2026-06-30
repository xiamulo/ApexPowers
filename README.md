# ApexPowers

ApexPowers is a cross-agent workflow installer for Codex, Claude Code, and AI coding harnesses. It packages skills, agent prompts, command wrappers, optional loop hooks, doctor checks, and planning workflows behind one `apex` CLI.

The default install is conservative: it previews changes unless you pass `--write`, it preserves user-modified files, and it never installs lifecycle hooks through plugin manifests.

## Quick Start

From npm:

```bash
npm install -g apexpowers
apex init --write
apex doctor
```

From Python:

```bash
pipx install apexpowers
apex init --write
apex doctor
```

From a source checkout:

```powershell
git clone https://github.com/xiamulo/ApexPowers.git
cd ApexPowers
.\apex.ps1 init --write
.\apex.ps1 doctor
```

Preview first:

```bash
apex init
apex add frontend
apex add planning,research
apex sync
```

Write changes explicitly:

```bash
apex init --write
apex add frontend --write
apex sync --write
```

## What You Get

- Project/session initialization skills for Codex and Claude Code.
- `.agents/*.md` source prompts with generated Codex and Claude Code agent mirrors.
- Profile-based install/update/uninstall with `.apex/apexpowers-install.json` ownership tracking.
- `apex doctor` health checks for skills, mirrors, hooks, manifests, workflow state, and git status.
- Planning profiles for requirement grilling, PRD synthesis, and vertical-slice issue creation.
- Frontend, quality, GSAP, and GitHub research profiles.
- Optional manifest-managed loop hooks with dry-run, review, update, and uninstall flows.
- Distribution artifacts with manifest, INSTALL, SBOM-lite, SHA256SUMS, and expected doctor output.

## Commands

Common commands:

```bash
apex init                 # install the core profile, dry-run by default
apex init --write
apex add frontend         # add one or more profiles
apex add planning,research --write
apex sync                 # regenerate official agent mirrors
apex doctor
apex remove frontend      # uninstall managed profile artifacts
apex hooks explain
apex hooks install        # dry-run by default
apex hooks install --write
apex hooks uninstall --write
```

Advanced profile lifecycle commands remain available:

```bash
apex install --profile core --target codex,claude --write
apex update --write
apex uninstall --profile core --target codex,claude --write
apex pack --profile core --target all --output dist
```

`--target auto` currently expands to the supported Codex and Claude Code targets. More harness-specific targets can be added without changing profile definitions.

## Profiles

Profiles are defined in `registry/apexpowers-profiles.json`.

| Profile | Purpose |
| --- | --- |
| `core` | Minimal project/session initialization, agent mirror sync, and health checks. |
| `hooks` | Manifest-managed Codex and Claude Code loop hook installation. |
| `planning` | Requirement grilling, PRD synthesis, issue slicing, and delivery orchestration. |
| `research` | GitHub-backed external solution research. |
| `frontend` | Frontend design, local web-app testing, React/Next.js, and UI review. |
| `quality` | Web quality, accessibility, performance, SEO, and lean review. |
| `gsap` | GSAP animation skills. |
| `full` | Private/full install that includes all major profiles. |

Inspect profiles:

```bash
apex profile list
apex profile show full --json
```

## Install Behavior

`apex init` and `apex add` install profile artifacts into the target project:

- `.codex/skills/<skill>`
- `.claude/skills/<skill>`
- `.agents/*.md`
- `commands/*.toml`
- `.apex/apexpowers-install.json`

The install manifest records Apex-managed files and their source hashes. Updates can safely distinguish unchanged managed files, user-modified managed files, and unmanaged files.

By default:

- Commands are dry-run unless `--write` is present.
- Existing unmanaged files are skipped.
- Modified managed files are skipped unless `--force` is present.
- Agent mirrors are generated from `.agents` sources.
- Hooks are not installed unless you explicitly install the `hooks` profile or run `apex hooks install --write`.

## Hooks

ApexPowers lifecycle hooks are opt-in. They are intended as deterministic guardrails for AI coding sessions, not as a replacement for lint, type-check, tests, pre-commit, or CI.

Review the trust boundary:

```bash
apex hooks explain
apex hooks install
```

Install only after reviewing the dry-run output:

```bash
apex hooks install --write
```

Uninstall Apex-managed hook entries:

```bash
apex hooks uninstall --write
```

Plugin manifests must remain thin and must not install hooks directly. See `docs/supply-chain-trust-security.md` for the hook threat model and telemetry policy.

## Distribution

Build profile-specific artifacts:

```bash
apex pack --profile core --target all --output dist
apex pack --profile full --target all --output dist --force
```

Supported pack targets:

- `codex-plugin`
- `claude-plugin`
- `skillpack`
- `local`
- `all`

Release tags are expected to use `vX.Y.Z`. The release workflow builds Python distributions, npm tarballs, and Apex profile artifacts. Publishing to PyPI and npm is intentionally gated behind workflow dispatch and configured secrets.

## Repository Layout

```text
src/apexpowers_cli/             apex CLI
registry/apexpowers-profiles.json
                                profile registry
.codex/skills/                 Codex skills
.claude/skills/                Claude Code skills
.agents/                       agent source prompts
commands/                      command wrappers
.codex-plugin/                 Codex plugin manifest and core wrappers
.claude-plugin/                Claude plugin manifest
scripts/check_apex_distribution.py
                                distribution consistency checker
benchmarks/apex_distribution_benchmark.py
                                Apex-only distribution benchmark
docs/                           design, portability, security, and user docs
tests/                          unittest suite
```

Key docs:

- `docs/user-guide.md`
- `docs/apexpowers-inventory.md`
- `docs/apex-agent-portability.md`
- `docs/apex-parallel-delivery-orchestration.md`
- `docs/platform-native-solutions.md`
- `docs/supply-chain-trust-security.md`
- `docs/open-source-release-playbook.md`
- `NOTICE.md`

## Development

```bash
python -m pip install -e .
apex version
python -m unittest tests.test_apex_cli
python scripts/check_apex_distribution.py --json
```

Run broader validation before release:

```bash
python -m unittest discover
python scripts/check_apex_distribution.py --json
python benchmarks/apex_distribution_benchmark.py --runs 1 --json
```

For npm wrapper smoke testing:

```bash
npm install -g .
apex version
apex init
```

## Privacy And Security

- Default telemetry policy: no telemetry.
- Do not commit `.env`, tokens, credentials, `.serena/`, or local machine state.
- Do not install hooks by default.
- Preserve user-modified files unless `--force` is explicit.
- Update `NOTICE.md` when vendored skill sources change.
- Update `docs/supply-chain-manifest.sha256` after reviewing trust-critical artifact changes.

See `SECURITY.md`, `CONTRIBUTING.md`, `docs/supply-chain-trust-security.md`, and `NOTICE.md`.
