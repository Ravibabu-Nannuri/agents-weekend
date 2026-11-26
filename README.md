# Agents Weekend: building autonomous agents with LangGraph and Langfuse

A hands-on weekend workshop for learning to build, observe and evaluate AI agents, and to prepare
for **GenAI engineer and architect interviews**.

We build one **IT helpdesk agent** step by step. Each block adds one concept, and after each run
you check what changed in the Langfuse trace.

```
 user ─► redact secrets ─► guardrail ─► router ─┬─► kb_agent      ─► search_kb, check_system_status
                               │                ├─► ticket_agent  ─► get_ticket, create_ticket, lookup_user
                               ▼                └─► general
                            refuse              (+ account_agent with human approval for password resets)

                    every step traced in Langfuse  ·  scored by evals
```

Runs on **Claude** by default (`LLM_PROVIDER=anthropic`). OpenAI also works by changing one line in `.env`.
All data is fake, so the repo is safe to keep public.

## Quick start
```bash
git clone <this repo> && cd agents-weekend
make setup          # creates .venv, installs everything, creates .env
# edit .env: ANTHROPIC_API_KEY + LANGFUSE_* keys
make check          # ✅ for every line = ready
make test           # offline tests with a fake model (no keys needed)
```
You need Python 3.11+, an [Anthropic API key](https://console.anthropic.com) (about $5 of credit is plenty), and a free
[Langfuse Cloud](https://cloud.langfuse.com) account (create a project, then Settings → API keys).

## The blocks
Each folder has a `README.md` with the goal, what to look for in Langfuse, things to break on purpose,
and **interview Q&A**. Code blocks have a `starter.py` (TODOs) and a `solution.py`.

| # | Block | Concept | Run |
|---|---|---|---|
| 00 | [Fundamentals](00-fundamentals/) | ML → LLMs → agents; screening-question drill | – |
| 01 | [First agent](01-first-agent/) | agent = model + instructions + loop; first trace | `make b01` |
| 02 | [Tools](02-tools/) | tool calling, ReAct loop, hand-built graph | `make b02` |
| 03 | [Memory](03-memory/) | state, checkpointer, sessions, context growth | `make b03` |
| 04 | [Multi-agent](04-multi-agent/) | router + specialists, structured output | `make b04` |
| 05 | [Human-in-the-loop](05-human-in-the-loop/) | `interrupt()` / resume, approval for risky actions | `make b05` |
| 06 | [Evals](06-evals/) | datasets, deterministic checks, LLM-as-judge | `make b06` |
| 07 | [Guardrails, cost, latency](07-cost-latency-guardrails/) | redaction, input classifier, model routing | `make b07` |
| 08 | [Agents SDK comparison](08-agents-sdk-comparison/) | same agent in the OpenAI Agents SDK | `make b08` |
| 09 | [Mock interviews](09-mock-interview/) | system-design prompts, rubric, coding drills | – |
| 10 | [Serving and durability](10-serving/) | FastAPI, streaming, durable checkpointer, Docker + Postgres | `make serve` |

**[Learning notes](docs/LEARNING_NOTES.md)**: concepts, trade-offs and interview Q&A for each block, in plain words.
**[Walkthrough notebooks](notebooks/)**: run blocks 01-05 one step per cell and inspect the state between steps.
**[Architecture decisions](docs/adr/)**: what to decide when building agent systems, plus ADRs for this repo.

## Weekend agenda
**Saturday: build (about 4h)**: 00 → 01 → 02 → 03 → 04 → 05, with 5 minutes of interview Q&A after each block.
**Sunday: production and interviews (about 3–4h)**: 06 → 07 → 08 → 09 (mock interviews), then each person explains one block as if answering an interviewer.

How to run it as a group:
- **Rotate the driver.** One person shares their screen and types each block while the others guide.
- **Break things on purpose** (every block README suggests something) and debug from the trace.
- Everyone pushes **their own copy** to their personal GitHub and adds a "Lessons learned" section.

## Repo layout
```
common/       config (models), tracing (Langfuse), helpdesk (fake backend + tools), graphs
0X-*/         one folder per block: README, starter.py, solution.py
06-evals/     dataset.json + run_evals.py
tests/        offline tests with a scripted fake model
scripts/      check_setup.py
```

## Lessons learned
_Add your own after the weekend: what surprised you in the traces, what broke, what you'd do differently._
