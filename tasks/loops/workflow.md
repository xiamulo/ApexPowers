# Apex Workflow

This file is intentionally editable. Apex loop hooks read the matching state block and inject it into session context.

[apex-state:no_task]
No active `tasks/todo+*.md` file was found. Answer direct questions normally; when work starts, create or select a todo before implementation.
[/apex-state:no_task]

[apex-state:planning]
An active todo exists, but implementation evidence is still thin. Clarify scope, constraints, acceptance criteria, and expected validation before changing code.
[/apex-state:planning]

[apex-state:implementing]
Implementation is in progress. Keep changes scoped to the active todo, preserve existing user edits, and update loop state as evidence changes.
[/apex-state:implementing]

[apex-state:review_required]
Code changes require review. Inspect the diff and active todo, then create or update `tasks/reviews/<slug>.md` with review status.
[/apex-state:review_required]

[apex-state:validation_required]
Review is ready, but validation evidence is incomplete. Run the relevant lint, type-check, then record `> **Validation**: Pass` with command summaries.
[/apex-state:validation_required]

[apex-state:done]
Review and validation are complete. Summarize the change, mention verification, and leave commit/push decisions to the user unless explicitly requested.
[/apex-state:done]
