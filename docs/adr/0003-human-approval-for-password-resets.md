# ADR-003: Human approval for password resets

- **Status:** Accepted
- **Date:** 2026-11-20

## Context
Password reset is sensitive and abuse-prone (social engineering). The agent must not do it alone.

## Options considered
| Option | Pros | Cons |
| --- | --- | --- |
| Prompt instruction only ("ask first") | No extra code | Not enforced; can be ignored or prompt-injected |
| Approval in code via `interrupt()` | Enforced; durable pause; auditable | Users wait; needs an approval channel |
| Remove the tool | No risk | No automation benefit |

## Decision
The `reset_password` tool calls `interrupt()`. An admin approves or denies, and the run resumes by thread ID from a durable checkpointer.

## Autonomy and risk
Level 3 (act with approval). Worst case without it: account takeover through social engineering.

## How we will measure it
100% of resets have a recorded approver; median approval time.

## Consequences
Users wait for an admin. Production needs an approval UI (e.g. Slack buttons) and timeout handling; the demo uses a terminal prompt and an in-memory checkpointer.

## Revisit when
Identity verification is automated strongly enough to move resets to act-within-limits.
