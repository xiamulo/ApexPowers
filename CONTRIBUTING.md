# Contributing

Thanks for improving ApexPowers. This project treats install safety, clear ownership boundaries, and uninstallability as core product behavior.

## Development Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
apex version
```

Or run directly from the checkout:

```powershell
.\apex.ps1 version
```

## Before Opening a PR

Run the focused checks for the area you changed:

```powershell
python -m unittest tests.test_apex_cli
python scripts\check_apex_distribution.py --json
```

For hook changes:

```powershell
python -m unittest tests.test_apex_loop_hooks tests.test_apex_loop_installer
python -m unittest tests.apex_hooks.test_pre_tool_use_security tests.apex_hooks.test_post_tool_use_semantics tests.apex_hooks.test_stop_loop_safety
```

For distribution changes:

```powershell
python -m unittest tests.test_apex_distribution
python benchmarks\apex_distribution_benchmark.py --runs 1 --json
```

For broad changes:

```powershell
python -m unittest discover
```

## Contribution Rules

- Keep new install behavior dry-run by default unless the user passes `--write`.
- Do not install lifecycle hooks through plugin manifests.
- Keep hooks opt-in, manifest-managed, reviewable, and uninstallable.
- Preserve user-modified files unless `--force` is explicit.
- Update `NOTICE.md` when vendored third-party skill sources change.
- Update `docs/supply-chain-manifest.sha256` only after reviewing trust-critical artifact changes.

## Pull Request Checklist

- Tests or validation evidence are included.
- New user-facing behavior is documented.
- New files are included in distribution checks where appropriate.
- Security or hook behavior changes include threat-model notes.
