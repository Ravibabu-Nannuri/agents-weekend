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

## Hands-on interview questions

Questions only someone who has run and broken this code can answer well. Try each one yourself before reading the answer.

**Q: You printed `result["messages"][-1].content` and got a list with a `thinking` block whose text was empty. What does that tell you?**
The model did reason, but the API returned only an encrypted signature, not the reasoning text. The tokens are still billed. Use `.text` for the answer and keep thinking blocks in history so later turns stay consistent.

**Q: Your Langfuse cost looked about twice what you expected. What did you find?**
Each Claude call appeared twice: a `ChatAnthropic` generation from LangChain's callback and an `anthropic.messages` generation from the Anthropic SDK's own OpenTelemetry tracing. Fix: `ANTHROPIC_OPEN_TELEMETRY=false`. Lesson: instrument one layer.

**Q: You removed `flush()` and the trace still appeared. So is it useless?**
No. On a normal exit the SDK sends pending data automatically. With `os._exit(0)` (simulating a crash or a serverless freeze) the trace was lost unless `flush()` ran first.

**Q: A newer model rejected your request with "temperature is deprecated". How did you fix it without breaking other providers?**
Only send `temperature` when explicitly asked: build the kwargs dict conditionally and unpack it with `**kwargs`.

**Q: In the trace tree, `helpdesk-v1`, `model` and `ChatAnthropic` all showed 5.21s. What does that tell you?**
Parent times include children, so nearly all latency was the model call itself, not LangGraph or your code.

**Q: You replaced the system prompt with "Answer like a pirate". What changed besides the tone?**
The agent lost its role, context and rules: it gave consumer VPN advice and forgot tickets and outages. The system prompt is the agent's job description, so changes need evals.
