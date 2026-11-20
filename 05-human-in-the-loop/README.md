# Block 05 – Human-in-the-loop approval (40 min)

**Goal:** the agent may *propose* a risky action, but a human must approve before it runs.

## Steps
1. Run `starter.py` as-is – it resets bob's password with **no approval**. That's the problem.
2. Fill in the 3 TODOs.
3. Run `solution.py`. Approve once (`y`), run again and deny once (`n` + a reason). Compare both answers.

## What to look at in Langfuse
- Approved run: model → `reset_password` tool (interrupted) → *(pause)* → tool runs again on resume → model.
- The trace shows the gap where it waited for a human, then continued.
- Denied run: the model receives the denial as the tool result and handles it gracefully.
- Session view groups the before-pause and after-resume parts.

## Key ideas
- `interrupt(payload)` = save state and stop. `Command(resume=value)` = continue from that exact point.
- **Requires a checkpointer.** The paused state must live somewhere; in production that's Postgres,
  so the approval can come hours later, from a Slack button or web UI, handled by a different pod.
- On resume the interrupted node **re-runs from the top**, so code before `interrupt()` must be
  safe to run twice (no side effects before it!).
- Put approvals on actions that are **irreversible, costly or sensitive**: resets, refunds, deletes,
  sending emails, production changes. Read-only tools don't need them.

## Plug it into block 04
Add an `account_agent` specialist with `[lookup_user, reset_password]` and a new `Route` option.
Compile the supervisor with a checkpointer. Try it as a stretch exercise.

## Interview Q&A
**Q: How do you make agents safe for actions with real consequences?**
A: Layers: least-privilege tools (the agent can only do what its tools allow), input/output
guardrails, human approval for irreversible or high-impact actions, idempotent tools, audit logs
(traces), and limits on spend/steps. Approval is enforced in code, not just requested in the prompt.

**Q: How would you implement approval that comes from Slack hours later?**
A: Interrupt the graph with a durable checkpointer (Postgres). Post the payload to Slack with
approve/deny buttons carrying the thread_id. The button webhook calls the graph with
`Command(resume=decision)` for that thread. State survives restarts, and any worker can resume it.

**Q: Why not just tell the model in the prompt "always ask before resetting"?**
A: Prompts are guidance, not enforcement – a model can ignore them or be prompt-injected.
Safety-critical controls must live in code paths the model can't bypass.
