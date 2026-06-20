# ApexPowers Notices

ApexPowers is currently a private distribution. The root plugin manifests declare `license: UNLICENSED`; confirm licensing and redistribution rights before publishing a public community package.

## Apex-Owned Content

- Source: this repository.
- Paths: `.codex/skills/apex-*`, `.claude/skills/apex-session-init-claude-code`, `.agents`, `commands`, `scripts`, `benchmarks`, `docs`.
- License evidence: project plugin manifests currently use `UNLICENSED`.

## Vendored Skill Groups

| Source group | Local paths | License evidence |
| --- | --- | --- |
| web-quality-skills | `.codex/skills/accessibility`, `.codex/skills/best-practices`, `.codex/skills/core-web-vitals`, `.codex/skills/performance`, `.codex/skills/seo`, `.codex/skills/web-quality-audit` | `license: MIT` and version metadata in each `SKILL.md`. |
| GSAP skill docs | `.codex/skills/gsap-*` | `license: MIT` in each `SKILL.md`. The GSAP runtime package is not vendored here. |
| Vercel React best practices | `.codex/skills/react-best-practices` | `license: MIT`, `author: vercel`, `version: 1.0.0` in `SKILL.md`. |
| Vercel web interface guidelines wrapper | `.codex/skills/web-design-guidelines` | `author: vercel`, `version: 1.0.0` metadata in `SKILL.md`; fetches the latest upstream guideline text at use time. |
| Next.js best practices bundle | `.codex/skills/next-best-practices` | No license field in local frontmatter; revalidate upstream source and redistribution rights before public release. |
| Anthropic bundled skills | `.codex/skills/frontend-design`, `.codex/skills/webapp-testing` | `LICENSE.txt` contains Apache-2.0 terms. |
| github-solution-research | `.codex/skills/github-solution-research` | `LICENSE` contains MIT terms. |

## Public Release Rule

Before publishing ApexPowers outside private use:

- keep this `NOTICE.md` with the distributed package,
- retain upstream license files that are already present,
- verify every vendored skill without embedded license evidence,
- update `docs/supply-chain-trust-security.md`,
- regenerate `docs/supply-chain-manifest.sha256`.
