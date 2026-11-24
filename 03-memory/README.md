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

## Hands-on interview questions

Questions only someone who has run and broken this code can answer well. Try each one yourself before reading the answer.

**Q: You compiled with a checkpointer but forgot the `thread_id`. What happens?**
`ValueError: Checkpointer requires one or more of the following 'configurable' keys: thread_id, ...`. A checkpointer must know which conversation to load and save.

**Q: Three questions stored 10 messages. What were the other 7?**
Claude's tool-request messages, the tool results, and Claude's answers. Everything is stored and re-sent next turn.

**Q: Why did turn 3 ("what laptop do I have?") need no tool call in one run but a `lookup_user` call in another?**
In one run Claude had already called `lookup_user` in turn 1, so the answer was in history. Behaviour depends on what's already in the conversation, which is why runs differ.

**Q: What is sent to the model on every call, and what is stored in `messages`?**
Every call: system prompt + tool cards + full history. Only the history (user, AI, tool results) is stored; the system prompt and tool cards are added fresh each call. That's the fixed overhead prompt caching targets.

**Q: Why did your 3-question session cost ~12k tokens?**
Each call re-sends system prompt, tool cards and growing history. Watch input tokens per turn in the trace to see it grow.

**Q: How many checkpoints did one question produce, and what's in each?**
One per graph step (5 for a single tool round: start, input, model, tools, model). Each holds the state, the next node to run, and a link to its parent checkpoint, which is what makes resume and time travel possible.

**Q: The script restarts and alice is forgotten. What do you change?**
Swap `InMemorySaver` for a durable saver (SQLite locally, Postgres in production). Same graph code.
