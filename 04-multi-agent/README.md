# Block 04 – Multi-agent: supervisor + specialists (45 min)

**Goal:** split one "do everything" agent into a router and focused specialists.

```
          +--> kb_agent      (search_kb, check_system_status)
 router --+--> ticket_agent  (get_ticket, create_ticket, lookup_user)   --> END
          +--> general       (no tools)
```

## Steps
1. Run `python 04-multi-agent/solution.py`. Paste the printed Mermaid into mermaid.live.
2. Read how the router works: a **cheap model + structured output** (`Route` Pydantic model).
3. `starter.py`: wire the edges yourself (3 TODOs).

## What to look at in Langfuse
- The **router generation**: input is the conversation, output is JSON `{"agent": ..., "reason": ...}`.
  The `reason` field is free debugging – you can read *why* it routed that way.
- Nested spans: `router` → `ticket_agent` → its own model/tool loop inside.
- Compare the **router's model and cost** against the specialists'. Routing on a cheap model is a big cost lever.
- The biryani question: does it go to `general`? This is your first guardrail (more in block 07).

## Break it on purpose
- Make the `Route` field descriptions vague ("which agent"). Re-run the 6 questions. Count the wrong routes.
  This is exactly what block 06 will measure automatically.

## Key ideas
- **Why split?** Each specialist has fewer tools and a focused prompt → better tool choice, cheaper prompts,
  easier to test, and teams can own different agents.
- **Two common patterns:**
  - *Router / handoff* (this block): pick one specialist, it owns the answer.
  - *Supervisor with agents-as-tools*: a manager agent calls specialists like tools and combines results.
    Better when one question needs several specialists ("is VPN down AND what's my ticket?").
- **Cost of multi-agent:** more LLM calls and more latency. Don't split until one agent actually struggles.

## Interview Q&A
**Q: When do you use multi-agent instead of one agent with many tools?**
A: When one agent has too many tools (selection accuracy drops – often noticeable beyond ~10–15),
when different tasks need different prompts/models/permissions, or when teams need to own parts
independently. Otherwise one agent is simpler, cheaper and faster.

**Q: Router vs supervisor (agents-as-tools)?**
A: Router hands the conversation to one specialist – simple and cheap. Supervisor keeps control,
can call several specialists and merge their outputs – more flexible, more tokens and latency.

**Q: How do you make routing reliable?**
A: Structured output with an enum of valid targets, clear descriptions per target, a cheap model,
a fallback route, and an eval dataset measuring routing accuracy on every prompt change.

**Q: How do agents share context?**
A: Through shared graph state (here, the message list and `route`). You decide what each
specialist sees – full history, a summary, or just the task – which is a cost and privacy decision.

## Hands-on interview questions

Questions only someone who has run and broken this code can answer well. Try each one yourself before reading the answer.

**Q: How do you know why the router picked a specialist?**
The `reason` field in the `Route` structured output appears in the router generation in Langfuse. It costs a few tokens and saves debugging time.

**Q: Why is `agent` a `Literal[...]` and not a `str`?**
With `str` the model can invent a route name ("network_agent") and the conditional edge has nowhere to go. A `Literal` restricts output to valid node names.

**Q: What share of total cost per request is the router in your traces?**
Read it off the trace: router generation cost vs specialists. On a cheap model it should be a small fraction; if not, the routing prompt or history is too large.

**Q: You made the Route descriptions vague. What happened?**
Misroutes increase (e.g. ticket questions to the KB agent). Block 06 measures this automatically as `route_correct`.

**Q: "Is VPN down, and what's the status of INC-1001?" What does your router do?**
It picks one specialist, so half the question goes unanswered. That's the limit of a router; a supervisor that calls several specialists as tools handles it.

**Q: The specialist sees the whole conversation. Is that always right?**
No. It's a cost and privacy decision: you could pass only the latest question or a summary.
