# Security Policy

## Supported Versions

Security fixes target the latest released version of ApexPowers. Until `1.0.0`, APIs and profile names may change between minor versions.

## Reporting a Vulnerability

Please report security issues privately through GitHub Security Advisories when available. If advisories are unavailable, open a minimal issue that states a private report is needed without including exploit details.

Useful information:

- ApexPowers version: `apex version --json`
- Install channel: npm, pipx/PyPI, GitHub release, or checkout
- Host: Codex, Claude Code, or another harness
- Operating system
- Whether hooks were installed
- Redacted reproduction steps

## Security Boundaries

- ApexPowers plugin manifests must not install lifecycle hooks.
- Hooks are opt-in and installed only through `apex hooks install` or the hooks profile with `--write`.
- Hook install, update, and uninstall are manifest-managed.
- Default telemetry policy is no telemetry.
- User-modified files are not overwritten unless `--force` is explicit.
- Secret and path guard false positives should be reported with redacted examples.
