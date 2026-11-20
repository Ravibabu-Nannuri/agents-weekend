# Block 03 – State and memory (30 min)

**Goal:** multi-turn conversations. "Is there an outage for *it*?" only works if the agent remembers.

## Steps
1. Run `python 03-memory/starter.py` **before** filling the TODOs. Turn 2 fails – the agent has no idea what "it" is.
2. Fill the 3 TODOs and run again.
3. Run `solution.py` – 3 turns for alice, then a fresh thread for bob.

## What to look at in Langfuse
- **Sessions** view → `alice-chat-1`: all turns grouped as one conversation.
- Open turn 3's generation and look at the input: **the whole history is re-sent every turn.**
  Watch the input tokens grow turn by turn. That's the hidden cost of memory.
- **Users** view: cost per user (alice vs bob).

## Key ideas
- **State** = the data flowing through the graph (here: the message list).
- **Checkpointer** = saves state after every step, keyed by `thread_id`. Gives you:
  memory across turns, **resume after a crash**, human-in-the-loop (block 05), and time-travel debugging.
- **Short-term memory** (this thread's history) vs **long-term memory** (facts about the user
  across threads – LangGraph's `store`). Interviewers like this distinction.
- History grows forever → you need a strategy: trim to last N messages, summarise old turns,
  or move facts into long-term memory.

## Try it
- Swap `InMemorySaver` for SQLite so memory survives a restart:
  `pip install langgraph-checkpoint-sqlite`, then
  `from langgraph.checkpoint.sqlite import SqliteSaver` and
  `with SqliteSaver.from_conn_string("memory.db") as cp: graph = build_graph(checkpointer=cp)`

## Interview Q&A
**Q: How do you persist agent state in production?**
A: A checkpointer backed by a durable store (Postgres is the usual choice, Redis for speed),
keyed by thread/conversation ID. Every step is saved, so a crashed run can resume and a paused
run (waiting for a human) can continue hours later on a different pod.

**Q: The context window keeps growing. What do you do?**
A: Trim old messages, summarise earlier turns into a running summary, keep only tool results
that matter, and move durable facts into long-term memory retrieved on demand. Measure input
tokens per turn in traces to know when it matters.

**Q: Short-term vs long-term memory?**
A: Short-term is the current conversation's state (thread-scoped). Long-term is information
that persists across conversations (user preferences, past tickets), stored separately and retrieved when relevant.
