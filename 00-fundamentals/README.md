# Block 00 – AI fundamentals (25 min talk + 15 min Q&A drill)

Use the **AI Fundamentals** deck shared in the group (not in this repo). Then do the drill below:
each person answers 2–3 questions **out loud**, like a screening call. Aim for 30–60 seconds per answer.

## Bridge slide (add at the end of the deck)
> **Slide 14, in code: what we're building this weekend**
> An IT helpdesk agent: router → specialists → tools → human approval, with every step traced in Langfuse.
> Plan → Act → Observe = `model → tools → model` in LangGraph (block 02).
> Memory = checkpointer (03). Multi-agent = supervisor (04). Oversight = human-in-the-loop (05).
> Evaluation = Langfuse datasets (06). Guardrails, cost and latency (07).

## Screening-round drill

### ML basics
1. **AI vs ML vs deep learning vs GenAI?** Nested sets: AI is the goal; ML learns patterns from data;
   deep learning is ML with many-layered neural networks; GenAI is deep learning that creates new content.
2. **Supervised vs unsupervised vs reinforcement learning?** Labelled examples → predict; no labels →
   find structure (clusters, anomalies); trial and error with rewards (also used in RLHF for chat models).
3. **Why test on unseen data?** To check the model generalises instead of memorising (overfitting).
4. **What is model drift?** The world changes, so data in production stops looking like training data and
   accuracy drops. That's why you monitor and retrain.

### LLMs
5. **How does an LLM generate text?** It predicts the next token given all previous tokens, again and again.
6. **What is a token? Why care?** A chunk of text (~4 characters in English). Billing, speed and
   context limits are all counted in tokens.
7. **What is the context window?** The maximum tokens the model can consider at once: system prompt,
   history, tool results and its own answer.
8. **What does temperature do?** Controls randomness. Low = predictable (agents, extraction).
   Higher = more varied (brainstorming).
9. **Why do LLMs hallucinate?** They generate plausible text, not verified facts. Without grounding they fill gaps confidently.

### Working with LLMs
10. **RAG vs fine-tuning?** RAG adds knowledge at query time by retrieving documents – best for facts that
    change or private data. Fine-tuning changes the model's behaviour/style/format – best for a consistent
    skill or tone. Most teams start with prompting, then RAG, and fine-tune last.
11. **What makes a good prompt?** Role, context, a specific task, output format, examples; then iterate.
12. **How do you reduce hallucinations?** Grounding (RAG / tools), asking for citations, constrained
    output formats, lower temperature, evals, and human review for high-stakes output.

### Agents
13. **Chatbot vs agent?** A chatbot answers; an agent pursues a goal over several steps, choosing and
    calling tools, observing results, and deciding what to do next.
14. **Components of an agent?** LLM (reasoning), tools (actions), memory (state), and a loop with stop conditions.
15. **What is MCP?** Model Context Protocol – an open standard for connecting AI apps to tools and data
    sources, so a tool written once works with many agents and clients.
16. **Main risk with agents and the fix?** Wrong *actions*, not just wrong words. Fix: least-privilege
    tools, guardrails, human approval for risky steps, tracing and evals.

### Responsible AI
17. **What would you never paste into an AI tool?** Confidential, customer or personal data in an
    unapproved tool. Follow company policy.
18. **Who is accountable for an AI-assisted decision?** A human. AI assists; people own the outcome.

## Hands-on interview questions

Questions only someone who has run and broken this code can answer well. Try each one yourself before reading the answer.

**Q: You send the same question twice and get two different answers. Is something broken?**
No. Generation samples tokens, so wording varies run to run, and thinking models vary more. That's why agent tests check facts, routes and tools used, not exact text.

**Q: Roughly how many tokens is your system prompt, and why should you know?**
Count it (characters / 4 is a fair estimate, or read input tokens of a one-word question in the trace). It's sent on every call, so it's a fixed cost per call; long prompts are the first target for prompt caching.

**Q: The API "remembers" nothing between calls. How did your chatbot remember the user's name?**
The code re-sent the whole conversation every turn. Memory is the application's job, not the model's.

**Q: What's the first thing you look at when a model "ignores" an instruction?**
The exact request that was sent (in the trace): was the instruction actually there, in the system role, and not contradicted later in the conversation or by a tool result?
