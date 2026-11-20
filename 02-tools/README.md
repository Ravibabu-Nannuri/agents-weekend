# Block 02 – Tools and the agent loop (45 min)

**Goal:** the agent starts *acting*. Then we open the prebuilt agent and build the same loop by hand.

## Steps
1. Read `common/helpdesk.py` – the fake IT backend and its 5 tools.
2. Run `python 02-tools/solution.py` – Part A uses the prebuilt `create_agent`, Part B the hand-built graph.
3. Paste the printed Mermaid diagram into https://mermaid.live – that's the loop.
4. Try `starter.py`: build the graph yourself (5 TODOs).

## What to look at in Langfuse
- Trace for "Is the VPN down?": **model → tool (check_system_status) → model**. Two generations now.
- Click the tool span: the **arguments the LLM chose** and the **tool output**.
- Click the 1st generation → look at the request: the **tool schemas** are sent with it.
  Your docstrings are literally part of the prompt.
- Compare the `prebuilt` and `handbuilt` traces – same shape, different node names.
- Compare token cost with block 01. Why is it higher? (tool schemas + 2 model calls)

## Break it on purpose
- In `common/helpdesk.py`, change the `check_system_status` docstring to `"""Does stuff."""`.
  Re-run. Does the agent still pick it? Look at the trace to see why.
- Set `recursion_limit=2`. What error do you get, and why does that limit exist?

## Key ideas
- **Tool calling:** the model doesn't run code. It outputs a structured request
  (`name` + `args`); your code runs the tool and feeds the result back.
- **ReAct loop:** Reason → Act → Observe → repeat. The `tools → model` edge *is* the loop.
- **Stop conditions:** the model stops calling tools (done), or you hit `recursion_limit` (safety).

## Interview Q&A
**Q: How does an LLM "call" a tool?**
A: Tool name, description and JSON schema are sent with the request. The model replies with a
structured tool call (name + arguments) instead of text. The application executes it, appends the
result as a tool message, and calls the model again.

**Q: The agent keeps choosing the wrong tool. How do you debug it?**
A: Open the trace, look at the exact tool schemas and the model's reasoning/arguments. Usually the
fix is clearer tool names/descriptions, fewer overlapping tools, or examples in the system prompt.
Then add the failing case to an eval set (block 06) so it doesn't regress.

**Q: How do you stop an agent looping forever?**
A: Hard limits (max steps / recursion limit, timeouts, token budget), tools that return clear
errors instead of hanging, and alerting on traces with unusually many steps.

**Q: Prebuilt agent vs hand-built graph – when would you use each?**
A: Prebuilt for a standard tool-calling loop. Hand-built when you need custom routing,
extra steps (validation, approval, guardrails), or parallel branches – which is most production systems.
