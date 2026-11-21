# Agents Weekend – Learning Notes

Concepts, trade-offs and interview Q&A for each block of this repo. Last updated Nov 20, 2026.

## Block 01: What is an agent?

An agent is the same LLM wrapped in a loop that lets it act. The intelligence comes from the model; the agency comes from your code around it.

```
Layer 1: LLM call   -> one request in, one response out. No memory, no actions.
Layer 2: Chatbot    -> LLM call + conversation history.
Layer 3: Agent      -> LLM + tools + a LOOP: the model decides what to do next,
                       does it, looks at the result, and decides again.
```

**The three ingredients**

| Ingredient | In code | Analogy |
| --- | --- | --- |
| Model | `model=get_llm()` (Claude Sonnet) | The brain: reads and writes text |
| Tools | `tools=[...]` (empty in block 01) | The hands: lets it act on real systems |
| System prompt | `system_prompt=SYSTEM_PROMPT` | The job description, read before every message |

**Key lesson: the model only knows what you send it.** In block 01 the prompt says "use the tools", but no tools are sent. Claude can't see the company's systems, so it honestly says it can't check outages. Your code must give it tools, and your code runs them; the model only asks for them.

**Why use a framework at all?** A single question and answer doesn't need one. Real agents need a loop (block 02), state across steps and turns (03), routing and branching (04), and pause/resume for human approval (05). LangGraph provides those pieces.

**State:** everything an agent knows lives in its state. Here that's just a dict with a `messages` list. After block 01 runs, it holds two messages: the user's and Claude's.

## Block 01: Configuration basics (common/config.py)

`config.py` has one job: hand the rest of the code a Claude model, so no other file deals with keys or model names.

1. **Reads `.env`** with `load_dotenv()`, so keys stay out of the code.
2. **Picks the models** from a lookup table: `_DEFAULTS[PROVIDER]["main"]` gives `claude-sonnet-5-5` (smart, for answers) and `["cheap"]` gives `claude-haiku-5-5` (fast and cheap, for routing and guardrails later). Changing `LLM_PROVIDER` switches to OpenAI without touching code.
3. **Builds the model** with `get_llm()` / `get_cheap_llm()`.

**Configuration over code:** anything that changes between environments or experiments (keys, model names, URLs) lives in `.env`. The commented `MODEL=` / `CHEAP_MODEL=` lines are optional overrides; `os.getenv("MODEL", default)` uses the `.env` value if present, otherwise the default.

**Tokens:** LLMs read and write tokens, not words. 1 token is about 3/4 of an English word, so 1,024 tokens is about 750 words. Cost, speed and limits are all counted in tokens.

**max_tokens:** the ceiling on the reply's length (here 1,024). The reply stops early if it's done, or gets cut off at the limit. It controls cost and speed, and Anthropic's API requires it. With newer Claude models, thinking tokens count toward it too.

**temperature:** how random the next-token choice is. 0 = predictable and repeatable (agents, extraction, evals); high = creative (brainstorming). Newer Claude models reject it entirely because their thinking step handles this, so the code only sends it when explicitly asked.

**`**kwargs`:** builds the model's settings as a dict and spreads it into named arguments, so `temperature` can be included only sometimes.

## Block 01: Tracing basics (Langfuse)

LangGraph fires callback events at every step; Langfuse's `CallbackHandler` listens and turns them into a trace.

```
Trace  (one user request; tags, user_id)
 └─ helpdesk-v1        span: the whole agent run
     └─ model          span: the graph node
         └─ Claude     GENERATION: prompt, response, tokens, cost, latency
```

- **Trace:** one end-to-end request.
- **Span:** one step inside it; spans nest.
- **Generation:** a span for an LLM call, with model, tokens and cost.
- **`trace_attributes(user_id=..., tags=[...])`** stamps that metadata on every span inside the `with` block.

**The three tracing helpers (common/tracing.py)**

| Function | Job | Needed for a trace to exist? | Why it still matters |
| --- | --- | --- | --- |
| `langfuse_config()` | Creates the trace (Langfuse listens via callbacks) | Yes, essential | No callbacks, no trace |
| `flush()` | Delivers the trace before the script exits | No (usually) | Reliability: guarantees delivery in scripts, crashes and serverless |
| `trace_attributes(...)` | Labels the trace (tags, user_id, session_id) | No | Usefulness: without labels, you can't filter, group by user or session, or see per-user cost |

Rule: `langfuse_config` decides *whether* there's a trace; `trace_attributes` only decides *what it's labelled*.

Analogy: `langfuse_config` = the camera is on; `flush` = the footage is saved; `trace_attributes` = the footage has a title and date on it.

Why `flush()` is "usually" optional: the SDK tries to send pending traces automatically when a script exits normally. Traces get lost when that can't run: a crash or kill, or serverless functions frozen right after responding. Calling `flush()` turns "probably delivered" into "definitely delivered".

**flush():** Langfuse sends traces in the background, in batches, so it doesn't slow the app. A short script can exit before the batch goes out. `flush()` means "send everything now". Call it at the end of every script; long-running servers rarely need it.

**Content blocks:** newer Claude models think before answering, so a reply's `.content` is a list of blocks (`thinking` + `text`). Use `.text` to get just the answer. Thinking tokens are still billed, which matters for cost.

## Interview Q&A so far

**Q: What's the difference between an LLM call and an agent?**
An LLM call is one request and one response. An agent wraps the model in a loop: it can decide to call tools, observe the results, and continue until it decides it's done.

**Q: Why does an agent need tools if the prompt already tells it what to do?**
The model only knows its training data and what's in the request. A prompt can't give it access to live systems; tools can. The model requests a tool call, and your code executes it.

**Q: What does temperature do?**
It controls randomness when sampling the next token. Low is deterministic, which suits agents, extraction and evals; high is more varied, for brainstorming. Some newer reasoning models don't expose it and manage sampling internally.

**Q: What is max_tokens and why set it?**
The maximum length of the reply in tokens. It caps cost and latency per call. With reasoning models it also has to leave room for thinking tokens.

**Q: Why do you need observability for LLM apps when you already have logs?**
Logs show that a request happened. A trace shows the full chain: the exact prompt, each model call, tool inputs and outputs, tokens, cost and latency per step. That's what you need to debug non-deterministic behaviour.

**Q: Trace vs span vs generation?**
A trace is one end-to-end request. Spans are the nested steps inside it. A generation is a span for an LLM call, with model, prompt, completion, tokens and cost.
