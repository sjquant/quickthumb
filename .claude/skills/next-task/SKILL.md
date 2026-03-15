---
name: next-task
description: Read TASKS.md and begin working on the next TODO task in order.
disable-model-invocation: true
---

Read @specs/TASKS.md and begin working on the next [TODO] task.

- TODO → DOING when starting
- Continue to the next task if the total is < 200 lines. Set to [REVIEW] once finished.
- If code changes exceed ~200 lines: stop and set status to [REVIEW]
- Wait for user confirmation
- After confirmation: set status to [DONE] **before** committing or pushing

Do not reorder tasks. Only update the status.
