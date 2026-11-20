"""Block 03 - State and memory with a checkpointer.

Run:  python 03-memory/solution.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langgraph.checkpoint.memory import InMemorySaver

from common.config import get_llm
from common.graphs import build_tool_agent
from common.helpdesk import ALL_TOOLS, SYSTEM_PROMPT
from common.tracing import flush, langfuse_config, trace_attributes


def build_graph(llm=None, checkpointer=None):
    # The checkpointer saves the graph state after every step, keyed by thread_id.
    # InMemorySaver = lost on restart. In production: Postgres/Redis/SQLite saver.
    return build_tool_agent(
        llm or get_llm(), ALL_TOOLS, SYSTEM_PROMPT,
        checkpointer=checkpointer or InMemorySaver(), name="helpdesk-memory",
    )


def chat(graph, thread_id: str, user_id: str, text: str) -> str:
    # Only the NEW message is sent. The checkpointer loads the earlier ones.
    with trace_attributes(session_id=thread_id, user_id=user_id, tags=["block-03"]):
        result = graph.invoke(
            {"messages": [{"role": "user", "content": text}]},
            config=langfuse_config(thread_id=thread_id, recursion_limit=12),
        )
    return result["messages"][-1].content


def main():
    graph = build_graph()

    # Conversation 1: three turns that depend on each other
    turns = [
        "Hi, I'm alice. My VPN keeps dropping.",
        "Is there an outage for it?",                 # "it" = VPN, needs memory
        "OK. And what laptop do I have on record?",   # "I" = alice, needs memory
    ]
    for t in turns:
        print(f"\nalice: {t}\nagent: {chat(graph, 'alice-chat-1', 'alice', t)}")

    # Conversation 2: different thread_id = blank slate
    q = "What laptop do I have?"
    print(f"\n[new thread] bob: {q}\nagent: {chat(graph, 'bob-chat-1', 'bob', q)}")

    # Peek at what the checkpointer stored
    state = graph.get_state({"configurable": {"thread_id": "alice-chat-1"}})
    print(f"\nStored messages in alice-chat-1: {len(state.values['messages'])}")
    print(f"Checkpoints saved: {len(list(graph.get_state_history({'configurable': {'thread_id': 'alice-chat-1'}})))}")
    flush()


if __name__ == "__main__":
    main()
