---
name: apex-lean-review
description: Review a diff or module for over-engineering. Finds unnecessary abstractions, dependencies, custom code, and platform-native replacements while preserving safety, validation, accessibility, tests, and explicit requirements.
---

# Apex Lean Review

Use this skill when the user asks for an over-engineering review, lean review, simplification pass, YAGNI audit, dependency audit, or "what can we delete".

This is a review skill, not an always-on coding mode. Do not change files unless the user separately asks for implementation.

## Scope

Review only whether the current diff or target module is larger, more abstract, or more dependency-heavy than the requirement needs. Do not replace the normal code-reviewer for correctness, security, maintainability, or test-quality review.

## Evidence To Gather

1. Read the request or active `tasks/todo+*.md`.
2. Inspect the diff or named files.
3. Check existing project patterns before recommending a new style.
4. Consult `docs/platform-native-solutions.md` when available.
5. Identify whether an installed dependency or standard library already solves the same job.

## Review Ladder

Stop at the first applicable simplification:

1. The behavior is speculative or unused today: delete it.
2. The language or runtime standard library already covers it: use that.
3. Browser, CSS, database, or platform-native capability covers it: use that.
4. An already-installed project dependency is the established local pattern: use it.
5. The abstraction has one real caller or one implementation: inline it or defer it.
6. The code is necessary but too large: split only around real responsibilities.

## Never Cut

Do not simplify away:

- input validation at trust boundaries
- error handling that prevents data loss
- security controls
- accessibility basics
- user explicitly requested behavior
- a focused test or self-check for non-trivial logic
- compatibility behavior that the project already needs

## Output Format

Findings first, one per line:

`L<line or file>: <tag> <what to cut or shrink>. Replacement: <specific alternative>. Keep if: <condition>.`

Allowed tags:

- `delete`: dead code, speculative feature, unused path
- `stdlib`: custom code replaced by standard library
- `native`: dependency or custom UI replaced by platform-native capability
- `yagni`: abstraction without a current second use
- `shrink`: same behavior with fewer moving parts
- `dependency`: package can be removed or avoided

End with:

- `Net removable:` estimated files, lines, dependencies, or concepts
- `Do not cut:` safety or requirement boundaries that must remain

If no findings:

`Lean already. Ship.`

## Boundaries

Prefer concrete deletions over taste comments. If the recommendation depends on runtime support, name the compatibility requirement that must be verified.
