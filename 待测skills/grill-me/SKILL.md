---
name: grill-me
description: Relentlessly interview the user one question at a time to sharpen a plan, product requirement, design, decision, or idea until every relevant branch and dependency is resolved. Use when the user invokes $grill-me, asks to be grilled, wants iterative requirements discovery, needs assumptions stress-tested, or wants shared understanding before implementation.
---

# Grill Me

Interview the user relentlessly until reaching a shared understanding of the plan, decision, requirement, design, or idea.

## Workflow

1. Inspect the available environment, repository, files, and tools for relevant facts before asking questions.
2. Separate discoverable facts from decisions that belong to the user. Look up facts; ask the user for decisions.
3. Walk the decision tree branch by branch. Resolve dependencies in the order needed to make later answers meaningful.
4. Ask exactly one question per message and wait for the user's answer before continuing.
5. For every question, state a recommended answer and briefly explain why. Prefer concise, mutually exclusive options when useful, while allowing a free-form answer.
6. Challenge vague answers, hidden assumptions, contradictions, missing constraints, edge cases, and unclear success criteria with follow-up questions.
7. Periodically summarize only when it helps confirm resolved decisions or expose remaining uncertainty.
8. When no material branch remains unresolved, present the complete shared understanding: objective, users, scope, non-goals, constraints, key decisions, risks, and acceptance criteria.
9. Ask the user to confirm that the shared understanding is complete.

Do not implement, edit files, create plans, or take consequential action until the user explicitly confirms the shared understanding. Research and other read-only inspection needed to inform the interview are allowed.

If the user changes an earlier decision, revisit all downstream decisions affected by it before continuing.
