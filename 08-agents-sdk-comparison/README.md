# Block 08 – Same agent, OpenAI Agents SDK (40 min)

**Goal:** rebuild the block 04/07 helpdesk in a second framework, then compare with data, not opinions.

Yes, it runs on **Claude**. The Agents SDK is model-agnostic through its LiteLLM extension
(`LitellmModel("anthropic/...")`), so it uses the same `LLM_PROVIDER` setting as everything else.

## Steps
1. Read `helpdesk_agents_sdk.py` next to `04-multi-agent/solution.py` + `07-.../solution.py`.
2. Run it: `python 08-agents-sdk-comparison/helpdesk_agents_sdk.py`
3. Open both traces for the same question in Langfuse and fill in the table below together.

## Concept mapping
| Concept | LangGraph (blocks 02–07) | Agents SDK (this block) |
|---|---|---|
| Agent loop | You build it: `model → tools → model` edges | Built in: `Runner.run` |
| Tools | `@tool` + `ToolNode` | `@function_tool` |
| Routing | Router node + structured output + conditional edges | `handoffs=[...]` (the model calls a transfer tool) |
| Guardrails | Your own nodes before/after | `input_guardrails=[...]`, `output_guardrails=[...]` |
| Memory | Checkpointer + `thread_id` | `Session` (e.g. `SQLiteSession`) |
| Human approval | `interrupt()` / `Command(resume=)` – pause for days | Possible, but you build more of the pause/resume yourself |
| Loop limit | `recursion_limit` | `max_turns` |
| Langfuse | LangChain `CallbackHandler` | OpenTelemetry via OpenInference instrumentor |

## Fill this in from your own runs
| | LangGraph | Agents SDK |
|---|---|---|
| Lines of code (helpdesk + guard) | | |
| LLM calls for "What's happening with INC-1001?" | | |
| Latency for that question (s) | | |
| Cost for that question ($) | | |
| How easy was it to read the trace? | | |
| How would you add "approve before reset"? | | |

## Things to notice
- **Handoffs are tool calls.** In the trace, Triage calls a `transfer_to_...` tool. Routing is decided by
  the LLM inside the loop, not by your code. Flexible, but harder to test than an explicit router.
- **Guardrail runs in parallel** with the triage agent by default – faster, but the main agent may
  already have spent tokens when the tripwire fires.
- **Less code, less control.** The SDK hides the graph. Great until you need custom flow, durable
  pauses, or step-level retries.

## Interview Q&A
**Q: LangGraph vs Agents SDK vs CrewAI – how do you choose?**
A: Agents SDK: fastest path for tool use + handoffs, minimal abstraction. CrewAI: role-based multi-agent
prototypes, very quick to start. LangGraph: explicit, stateful graphs with checkpointing, human-in-the-loop
and durable execution – the usual choice for complex production workflows. I'd prototype in whatever's
fastest and move to LangGraph when I need control over flow and state.

**Q: Would you lock in to one framework?**
A: Keep the valuable parts framework-independent: tools behind MCP or plain functions, prompts in a
prompt manager, evals and observability on OpenTelemetry (Langfuse works with both). Then switching
the orchestration layer is a contained change – exactly what this block did.

## Hands-on interview questions

Questions only someone who has run and broken this code can answer well. Try each one yourself before reading the answer.

**Q: How did you run the OpenAI Agents SDK on Claude?**
Through its LiteLLM extension: `LitellmModel(model="anthropic/<model>")`, reading `ANTHROPIC_API_KEY`.

**Q: Why call `set_trace_processors([])` before instrumenting?**
The SDK's default exporter sends traces to OpenAI's dashboard. Removing it avoids duplicate exports (and failures without an OpenAI key); OpenInference then exports spans to Langfuse.

**Q: In the trace, how does a handoff appear?**
As a tool call (`transfer_to_...`) made by the triage agent. Routing is decided by the model inside the loop, not by your code.

**Q: The guardrail tripped, but the trace shows the triage agent had already started. Why?**
Input guardrails run in parallel with the agent by default: faster, but some tokens may be spent before the tripwire fires.

**Q: Which was easier to read in Langfuse, and which was easier to change?**
Answer from your own comparison table: lines of code, LLM calls, latency and cost for the same question, and how you'd add approval before a reset.
