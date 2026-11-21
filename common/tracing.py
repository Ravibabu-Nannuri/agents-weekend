"""Langfuse wiring for LangGraph.

LangGraph/LangChain report every step (graph node, LLM call, tool call) to
"callbacks". Langfuse's CallbackHandler turns those into a nested trace.

Usage:
    from common.tracing import langfuse_config, trace_attributes

    with trace_attributes(user_id="alice", session_id="chat-1", tags=["block-03"]):
        graph.invoke(inputs, config=langfuse_config(thread_id="chat-1"))
    flush()
"""

import os
from contextlib import contextmanager, nullcontext

from dotenv import load_dotenv

# Load .env here too, so tracing works even if common.config wasn't imported first.
# The Langfuse SDK then reads LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_BASE_URL
# from the environment by itself - we never pass the keys in code.
load_dotenv()


def tracing_enabled() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))


def langfuse_config(thread_id: str | None = None, **extra) -> dict:
    """Build the `config` dict for graph.invoke(...).

    - callbacks: sends the run to Langfuse (skipped if keys are missing)
    - configurable.thread_id: tells a checkpointer which conversation this is (block 03+)
    """
    config: dict = {"callbacks": [], "configurable": {}}
    if tracing_enabled():
        from langfuse.langchain import CallbackHandler

        config["callbacks"].append(CallbackHandler())
    if thread_id:
        config["configurable"]["thread_id"] = thread_id
    config.update(extra)
    return config


def trace_attributes(**attrs):
    """Attach user_id / session_id / tags / metadata to every span created inside.

    Langfuse uses session_id to group multi-turn chats (Sessions view) and
    user_id for per-user cost (Users view).
    """
    if not tracing_enabled():
        return nullcontext()
    from langfuse import propagate_attributes

    return propagate_attributes(**attrs)


def flush():
    """Short scripts can exit before traces are sent. Always flush at the end."""
    if tracing_enabled():
        from langfuse import get_client

        get_client().flush()


@contextmanager
def traced_run(name: str, **attrs):
    """Convenience: a named root span + attributes, flushed on exit."""
    if not tracing_enabled():
        yield None
        return
    from langfuse import get_client, propagate_attributes

    lf = get_client()
    with lf.start_as_current_observation(as_type="span", name=name) as span:
        with propagate_attributes(trace_name=name, **attrs):
            yield span
    lf.flush()
