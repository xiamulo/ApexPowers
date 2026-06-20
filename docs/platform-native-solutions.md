# Platform-Native Solutions For Apex Review

This document is a review aid for ApexPowers. It helps agents ask whether the platform already covers a requested feature before adding dependencies, abstractions, or custom infrastructure.

The rule is conservative: prefer native capabilities when they fully satisfy the requirement, but keep a library when compatibility, ergonomics, accessibility, security, or domain complexity justify owning that dependency.

## HTML And Form Controls

| Requirement | Native option to check first | Keep a library when |
| --- | --- | --- |
| Date, time, color, range inputs | `input` types: `date`, `time`, `color`, `range` | You need custom cross-browser UX, complex validation, or locale behavior the native control cannot provide. |
| Modal dialog | `dialog` with `showModal()` | You need a design-system modal with focus traps already standardized and tested. |
| Disclosure / accordion | `details` and `summary` | You need analytics, controlled state, or complex nested composition. |
| Progress / meter | `progress`, `meter` | You need custom visualization that communicates more than a scalar value. |
| Search suggestions | `datalist` | You need remote search, virtualization, fuzzy matching, or keyboard behavior beyond browser support. |

## CSS Capabilities

| Requirement | Native option to check first | Keep JavaScript or a library when |
| --- | --- | --- |
| Responsive layout | Grid, flexbox, container queries, `minmax()` | Layout state depends on runtime data or virtualized measurement. |
| Responsive sizes | `clamp()`, custom properties, media queries | Values depend on measured content or user settings not expressible in CSS. |
| Sticky / snapping UI | `position: sticky`, scroll snap | Behavior requires route state, accessibility-managed focus, or complex physics. |
| Motion preferences | `prefers-reduced-motion` | Animation orchestration is part of product behavior and has a tested reduced-motion fallback. |
| Parent-state styling | `:has()` where supported | Browser support constraints require a fallback. |

## Browser APIs

| Requirement | Native option to check first | Keep a dependency when |
| --- | --- | --- |
| Query string parsing | `URL` and `URLSearchParams` | You need legacy browser support or custom nested object syntax. |
| Deep clone | `structuredClone` | You need class instances, custom serialization, or unsupported values. |
| IDs | `crypto.randomUUID()` | You need deterministic IDs, shorter IDs, or a specific UUID version. |
| Formatting | `Intl.NumberFormat`, `Intl.DateTimeFormat`, `Intl.RelativeTimeFormat`, `Intl.PluralRules` | You need domain-specific calendar, parsing, or formatting behavior. |
| Clipboard / share | `navigator.clipboard`, `navigator.share` | You need fallback UX for unsupported platforms. |
| Observers | `IntersectionObserver`, `ResizeObserver`, `MutationObserver` | You need virtualization or scheduling semantics beyond observer events. |
| Fetch timeout | `AbortSignal.timeout()` where available | You need retries, backoff, circuit breakers, or cross-runtime support. |

## Node.js Standard Library

| Requirement | Native option to check first | Keep a dependency when |
| --- | --- | --- |
| Recursive directory creation | `fs.mkdirSync(path, { recursive: true })` | You need a cross-runtime abstraction already used project-wide. |
| Recursive removal | `fs.rmSync(path, { recursive: true, force: true })` | You need safety prompts, trash semantics, or dry-run planning. |
| Path handling | `path`, `path.posix`, `path.win32` | You need URL/path interop beyond stdlib ergonomics. |
| JSON file read/write | `fs.readFileSync` plus `JSON.parse` / `JSON.stringify` | You need comments, schemas, migrations, or atomic writes. |
| Sets and flattening | `Set`, `Array.prototype.flat`, `Object.groupBy` where available | You target runtimes without support or need stable polyfills. |

## Python Standard Library

| Requirement | Native option to check first | Keep a dependency when |
| --- | --- | --- |
| CLI parsing | `argparse` | You need a rich CLI framework, plugin commands, shell completion, or nested UX. |
| Data objects | `dataclasses` | You need validation, parsing, or runtime schemas. |
| Dates and time zones | `datetime`, `zoneinfo` | You need fuzzy parsing, recurrence rules, or legacy Python support. |
| Paths | `pathlib` | You need virtual filesystems or cloud storage adapters. |
| Caching | `functools.lru_cache` | You need TTL, eviction visibility, distributed cache, or invalidation hooks. |
| Collections / iteration | `collections`, `itertools`, `functools` | You need a project-standard functional toolkit already installed. |

## Database Capabilities

| Requirement | Native option to check first | Keep application code when |
| --- | --- | --- |
| Uniqueness and ranges | `UNIQUE`, `CHECK`, foreign keys | The rule depends on external systems or user-specific policy. |
| Deduplication | `DISTINCT`, `ON CONFLICT`, unique indexes | The dedupe rule is fuzzy or domain-specific. |
| Pagination and sorting | `LIMIT`, `OFFSET`, keyset pagination | The data source is not a database or requires search-engine ranking. |
| Aggregation | `GROUP BY`, window functions, conditional aggregation | Aggregation spans services or needs cached materialized views. |
| JSON and full-text search | Database JSON / FTS features | Search quality, language support, or ranking needs a dedicated engine. |

## Review Checklist

When reviewing a proposed dependency or custom abstraction, ask:

1. Does the requested behavior need to exist now?
2. Does the language, browser, runtime, framework, or database already provide it?
3. Is an installed dependency already the project-standard solution?
4. Does the custom code add safety, accessibility, compatibility, or domain behavior the native option lacks?
5. Is the added abstraction serving more than one real caller today?
6. Is there one focused test or self-check that proves the simplified path still works?

If the native option is enough, recommend it. If it is not enough, document the missing requirement that earns the dependency.
