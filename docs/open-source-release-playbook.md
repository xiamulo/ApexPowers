# Open Source Release Playbook

This playbook turns ApexPowers from a private checkout into a public installable project.

## Phase 1: Public Project Shape

Goal: make the repository understandable, auditable, and installable from source.

Required state:

- `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, and `CHANGELOG.md` exist.
- README starts with `apex init`, not low-level profile internals.
- `apex init`, `apex add`, `apex sync`, and `apex remove` are the public command path.
- Hooks remain opt-in through `apex hooks install`.
- `apex hooks explain` documents trust boundaries.
- CI runs CLI tests and distribution checks.

Verification:

```bash
python -m unittest tests.test_apex_cli tests.test_apex_distribution
python scripts/check_apex_distribution.py --json
npm install -g .
apex version
apex init
```

## Phase 2: Package Manager Distribution

Goal: make install feel like common AI workflow tools.

Python:

```bash
python -m build
python -m twine check dist/*
```

Publish after configuring PyPI trusted publishing or token-based credentials:

```bash
python -m twine upload dist/*
```

npm:

```bash
npm pack
npm publish --access public
```

The npm package is a thin wrapper around the Python CLI. It requires Python 3.10+ to be available on the user's PATH. If that becomes too much friction, replace the wrapper with a native Node installer or ship platform-specific standalone binaries.

Release tags should use:

```bash
git tag v0.1.0
git push origin v0.1.0
```

The GitHub release workflow builds:

- Python sdist/wheel
- npm tarball
- profile-specific Apex artifacts from `apex pack`

Publishing to PyPI and npm is intentionally gated by workflow dispatch and secrets.

## Phase 3: Plugin And Marketplace Distribution

Goal: make host-specific installation as direct as Superpowers-style plugin install flows.

Artifacts:

```bash
apex pack --profile core --target codex-plugin --output dist
apex pack --profile core --target claude-plugin --output dist
apex pack --profile full --target local --output dist
```

Marketplace readiness:

- Plugin manifests remain thin.
- Plugin manifests do not declare hooks.
- Artifact contains `manifest.json`, `INSTALL.md`, `SBOM-lite.json`, `SHA256SUMS`, and `doctor-expected-output.json`.
- `apex doctor --json` expected output is documented.
- Hook installation is documented as opt-in after plugin install.

Host docs should eventually split into:

- Install for Codex
- Install for Claude Code
- Install for Cursor or other harnesses
- Install from npm
- Install from PyPI
- Install from GitHub release artifact

## Public vs Private Profiles

Keep public profiles broadly useful and low-surprise:

- `core`
- `frontend`
- `planning`
- `research`
- `quality`
- `gsap`
- `hooks`

Avoid publishing private project state, local loop state, credentials, customer-specific agents, or internal review policies unless they are intentionally generalized.

Recommended `.gitignore` for consumer projects that should not commit Apex state:

```gitignore
.apex/
.codex/skills/apex-*
.claude/skills/apex-*
.agents/
.codex/agents/
.claude/agents/
commands/apex-*.toml
tasks/loops/
tasks/reviews/
tasks/lessons.md
```
