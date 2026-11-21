# Block 01 – Your first agent + Langfuse trace (30 min)

**Goal:** get an agent running end to end and see it in Langfuse. Nothing clever yet.

## Steps
1. Open `starter.py` and fill in the 3 TODOs (or read `solution.py` together).
2. Run it: `python 01-first-agent/starter.py`
3. Open Langfuse → **Tracing** → newest trace.

## What to look at in Langfuse
- One trace → one agent span → **one LLM generation**.
- Click the generation: see the **system prompt + user message** that were actually sent.
- Note the **tokens, cost and latency**. Write the numbers down; you'll compare later.
- The `block-01` tag and `alice` user id (from `trace_attributes`).

## Notice: content blocks
Newer Claude models "think" before answering. The reply's `.content` is a **list of blocks**
(`thinking` + `text`), not a plain string. That's why the code prints `.text`, which joins just the
text blocks. Try printing `result["messages"][-1].content` to see the raw blocks, and find the
thinking block in the Langfuse generation too.

## Break it on purpose
- Delete `flush()` and run again. Did the trace show up? (Sometimes yes, sometimes late.) Why?
- Change `SYSTEM_PROMPT` to "Answer like a pirate". Run again and compare both traces side by side.

## Key idea
An agent = **model + instructions + a loop**. With no tools there is nothing to act on, so the
loop runs once. That's why this looks exactly like a chatbot. Block 02 changes that.

## Interview Q&A
**Q: What's the difference between an LLM call and an agent?**
A: An LLM call is one request → one response. An agent wraps the model in a loop: the model can
decide to take actions (tool calls), observe the results, and continue until it decides it's done.

**Q: Why do you need observability for LLM apps when you already have logs?**
A: Logs show that a request happened. A trace shows the full chain – the exact prompt sent, each
model call, tool inputs/outputs, tokens, cost and latency per step – which is what you need to
debug non-deterministic behaviour.

**Q: What's in a trace vs a span vs a generation?**
A: A trace is one end-to-end request. Spans are the steps inside it (nested). A generation is a
span for an LLM call, with model, prompt, completion, tokens and cost.
