# Block 07 – Guardrails, cost and latency (45 min)

**Goal:** protect the agent from bad input, then use traces to make it cheaper and faster.

```
START -> redact_secrets -> input_guardrail --blocked--> refuse   -> END
                                           \--ok-----> helpdesk -> END   (block 04 graph)
```

## Steps
1. Run `python 07-cost-latency-guardrails/solution.py`. It runs 5 questions twice:
   - **Config A:** cheap model for guardrail + router, main model for answers
   - **Config B:** main model everywhere
2. Compare A vs B in the terminal table and in Langfuse (filter by tag `block-07`).

## What to look at in Langfuse
- Question 2 contains a password. Open its trace: the model **never saw the password**. It was
  redacted in code before any LLM call. (Check the router and guardrail inputs.)
- The prompt-injection and biryani traces stop at `refuse`: **one cheap LLM call** instead of 3–5.
- **Latency breakdown:** which span is slowest? Usually the specialist's model calls, not the guardrail.
- **Cost A vs B:** sum the cost of the guard + router generations in each config.

## Two kinds of guardrails
| | Code (regex, rules, allow-lists) | LLM classifier |
|---|---|---|
| Speed / cost | ~0 ms, free | 0.3–1 s, costs tokens |
| Good for | secrets, card numbers, emails, blocked words | intent: off-topic, injection, abuse |
| Weakness | misses anything it wasn't written for | can be wrong, can itself be attacked |

Use both: code first (cheap, certain), LLM second (flexible). Add **output** guardrails too –
e.g. check the answer doesn't leak internal data before returning it.

## Cost and latency levers (interview gold)
1. **Model routing:** cheap model for classify/route/guard, strong model only where reasoning matters.
2. **Fail fast:** block bad input before the expensive part runs.
3. **Fewer steps:** better tool descriptions → fewer wrong tool calls → fewer loops.
4. **Smaller context:** trim history (block 03), short tool outputs, short system prompts.
5. **Caching:** prompt caching for long static system prompts; cache common answers.
6. **Parallelism:** run independent tool calls / guardrails at the same time.
7. **Streaming:** doesn't reduce total time, but users see the first words much sooner.

## Interview Q&A
**Q: Your agent costs too much. How do you cut it by 50%?**
A: First measure: per-trace cost by step in the observability tool. Then attack the biggest items:
route cheap tasks to small models, block junk early, cut context size (history trimming, shorter tool
outputs), use prompt caching, reduce loop iterations with better tool descriptions. Verify with evals
that quality didn't drop.

**Q: How do you defend against prompt injection?**
A: No single fix. Layers: classify input, keep secrets and permissions out of the model's reach
(least-privilege tools), treat tool outputs and documents as untrusted data, require human approval
for sensitive actions, validate outputs, and monitor traces for anomalies.

**Q: Where should PII redaction happen?**
A: Before anything leaves your boundary – before the LLM call *and* before traces are exported.
(Langfuse supports a `mask` function on the client for exactly that.)
