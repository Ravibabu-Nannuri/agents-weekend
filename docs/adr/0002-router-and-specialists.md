# ADR-002: Router + specialists, with a cheap routing model

- **Status:** Accepted
- **Date:** 2026-11-20

## Context
One agent with all tools is expected to grow past 15 tools across IT domains, which lowers tool-selection accuracy and raises cost per request.

## Options considered
| Option | Pros | Cons |
| --- | --- | --- |
| One agent, all tools | Simplest, one model call fewer | Accuracy drops as tools grow; one giant prompt |
| Router + specialists | Focused prompts and tools; testable per specialist | Extra routing call; routing becomes a failure point |
| Supervisor (agents as tools) | Handles questions needing several specialists | More tokens and latency; harder to debug |

## Decision
A router using structured output (`Route` with a fixed `Literal` of targets) on a Haiku-class model, sending each question to one specialist with 2-3 tools.

## Autonomy and risk
A wrong route gives an unhelpful answer, not a harmful action.

## How we will measure it
Target: routing accuracy of at least 95% on the eval set (block 06), and router cost under 10% of total cost per request. Not yet measured.

## Consequences
One extra model call per request; questions spanning two domains need a follow-up turn.

## Revisit when
Many requests need two specialists at once (consider a supervisor).
