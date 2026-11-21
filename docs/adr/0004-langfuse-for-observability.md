# ADR-004: Langfuse for observability and evals

- **Status:** Accepted
- **Date:** 2026-11-20

## Context
We need traces of every step, cost and latency per request, eval datasets, and comparison between runs.

## Options considered
| Option | Pros | Cons |
| --- | --- | --- |
| Langfuse (cloud or self-hosted) | Open source, self-hostable, OpenTelemetry-compatible; tracing, metrics, evals, prompt management | Another service to run if self-hosted |
| LangSmith | Tight LangChain integration | Hosted SaaS by default |
| Vendor APM only | Existing tooling | Weak on prompts, generations and evals |

## Decision
Langfuse, because it covers tracing, metrics, evals and prompt management in one open-source, self-hostable tool.

## Autonomy and risk
Prompts and user messages are sent to the tracing backend. Mask PII or self-host before using real data.

## How we will measure it
Every request traced; eval runs compared before each prompt or model change.

## Consequences
Trace volume costs at scale; a self-hosted deployment must be operated.

## Revisit when
The company standardises on another observability platform.
