# ApexPowers Benchmark Method

This directory measures ApexPowers distribution and guardrail paths. It does not reuse Ponytail benchmark results and does not claim that ApexPowers saves lines, tokens, cost, or time compared with another agent mode.

## No comparative savings claim

Ponytail benchmarks are about a code-minimization behavior skill. ApexPowers is a private workflow, hook, agent mirror, and distribution package. The correct benchmark for ApexPowers is operational reliability: can the install, doctor, route renderer, and distribution checks run quickly and deterministically without network or model calls?

## What This Measures

- `scripts/check_apex_distribution.py --json`
- `apex-doctor` with isolated Codex and Claude homes
- `apex-init-project-hooks` dry-run JSON planning
- Codex TOML route config rendering
- Claude JSON route config rendering

All cells are offline. No paid model, external API, browser, server, or real host config is required.

## How To Run

```powershell
python benchmarks\apex_distribution_benchmark.py --runs 5 --json
```

Use `--runs 1` for quick smoke checks in local development.

## Reading Results

The output includes raw `elapsed_ms` samples and min / median / max per cell. Treat these as local machine measurements only. A regression is meaningful when the same machine and Python runtime show a large repeated increase.

## Production Gates

- Every cell exits 0.
- JSON output is parseable.
- No command writes to the repository or user host config.
- The benchmark does not report made-up savings against a baseline that was never run.
