# ADR-001: Use LangGraph for orchestration

- **Status:** Accepted
- **Date:** 2026-11-20

## Context
The helpdesk needs a tool loop, multi-turn memory, routing to specialists, and pauses for human approval that may last hours.

## Options considered
| Option | Pros | Cons |
| --- | --- | --- |
| LangGraph | Checkpointing, `interrupt()`/resume, explicit testable graphs | More code; steeper learning curve |
| OpenAI Agents SDK | Minimal; tools, handoffs, guardrails built in | Less control over flow and durable pauses |
| CrewAI | Fastest role-based prototypes | Less control in production |
| Custom loop | Full control | Rebuild state, retries, tracing ourselves |

## Decision
LangGraph, because it provides checkpointing and `interrupt()`/resume natively, and its explicit graph makes routing testable.

## Autonomy and risk
No impact on its own; it enables the approval gate in ADR-003.

## How we will measure it
Compare eval scores, cost and latency with the Agents SDK version of the same agent (block 08).

## Consequences
More code than the Agents SDK; the team must learn graphs and state.

## Revisit when
A lighter framework gains durable pause/resume, or the graph grows beyond what the team can maintain.
