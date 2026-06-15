---
name: apex-grill-with-docs
description: Apex 需求烤问工作流。第一个问题先确认用户最多愿意回答多少个后续问题，再只追问会影响项目走向的关键问题，并同步维护 CONTEXT.md 与 ADR。
---

<what-to-do>

First ask exactly one budget question before any other grilling question: "这轮你最多愿意回答多少个后续澄清问题？我会只挑会影响项目走向的问题来问。" Wait for the user's answer before continuing.

After the user gives the question budget, interview me relentlessly within that budget until we reach a shared understanding. Walk down the highest-impact branches of the design tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer.

Ask the questions one at a time, waiting for feedback on each question before continuing.

If a question can be answered by exploring the codebase, explore the codebase instead.

Never exceed the user's question budget. Treat the budget as the maximum number of follow-up grilling questions after the initial budget question. If the user gives zero, no number, or refuses a budget, proceed from existing context and code exploration only, then summarize assumptions instead of asking more questions.

Before asking any follow-up question, score it against this filter: would a different answer materially change architecture, data model, user workflow, risk posture, delivery scope, or issue slicing? Ask it only if the answer is yes. Skip nice-to-know, wording-only, or low-impact questions.

Prefer one-shot, high-leverage questions that force a clear decision. Each question should expose a fork in the road, a hidden constraint, a domain boundary, a trade-off, or a risk that would be expensive to discover later.

</what-to-do>

<supporting-info>

## Domain awareness

During codebase exploration, also look for existing documentation:

### File structure

Most repos have a single context:

```
/
├── CONTEXT.md
├── docs/
│   └── adr/
│       ├── 0001-event-sourced-orders.md
│       └── 0002-postgres-for-write-model.md
└── src/
```

If a `CONTEXT-MAP.md` exists at the root, the repo has multiple contexts. The map points to where each one lives:

```
/
├── CONTEXT-MAP.md
├── docs/
│   └── adr/                          ← system-wide decisions
├── src/
│   ├── ordering/
│   │   ├── CONTEXT.md
│   │   └── docs/adr/                 ← context-specific decisions
│   └── billing/
│       ├── CONTEXT.md
│       └── docs/adr/
```

Create files lazily — only when you have something to write. If no `CONTEXT.md` exists, create one when the first term is resolved. If no `docs/adr/` exists, create it when the first ADR is needed.

## During the session

### Challenge against the glossary

When the user uses a term that conflicts with the existing language in `CONTEXT.md`, call it out immediately. "Your glossary defines 'cancellation' as X, but you seem to mean Y — which is it?"

### Sharpen fuzzy language

When the user uses vague or overloaded terms, propose a precise canonical term. "You're saying 'account' — do you mean the Customer or the User? Those are different things."

### Discuss concrete scenarios

When domain relationships are being discussed, stress-test them with specific scenarios. Invent scenarios that probe edge cases and force the user to be precise about the boundaries between concepts.

### Cross-reference with code

When the user states how something works, check whether the code agrees. If you find a contradiction, surface it: "Your code cancels entire Orders, but you just said partial cancellation is possible — which is right?"

### Update CONTEXT.md inline

When a term is resolved, update `CONTEXT.md` right there. Don't batch these up — capture them as they happen. Use the format in [CONTEXT-FORMAT.md](./CONTEXT-FORMAT.md).

`CONTEXT.md` should be totally devoid of implementation details. Do not treat `CONTEXT.md` as a spec, a scratch pad, or a repository for implementation decisions. It is a glossary and nothing else.

### Offer ADRs sparingly

Only offer to create an ADR when all three are true:

1. **Hard to reverse** — the cost of changing your mind later is meaningful
2. **Surprising without context** — a future reader will wonder "why did they do it this way?"
3. **The result of a real trade-off** — there were genuine alternatives and you picked one for specific reasons

If any of the three is missing, skip the ADR. Use the format in [ADR-FORMAT.md](./ADR-FORMAT.md).

</supporting-info>
