"""Block 03 - STARTER. Give the agent memory.

Run:  python 03-memory/starter.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langgraph.checkpoint.memory import InMemorySaver  # noqa: F401  (you'll need it)

from common.config import get_llm
from common.graphs import build_tool_agent
from common.helpdesk import ALL_TOOLS, SYSTEM_PROMPT
from common.tracing import flush, langfuse_config, trace_attributes


def build_graph(llm=None):
    # TODO 1: pass checkpointer=InMemorySaver() so state survives between invokes
    return build_tool_agent(llm or get_llm(), ALL_TOOLS, SYSTEM_PROMPT)


def chat(graph, thread_id: str, user_id: str, text: str) -> str:
    # TODO 2: add session_id=thread_id so Langfuse groups the turns into one Session
    with trace_attributes(user_id=user_id, tags=["block-03"]):
        # TODO 3: pass thread_id into langfuse_config(...) so the checkpointer
        #         knows which conversation to load
        result = graph.invoke({"messages": [{"role": "user", "content": text}]},
                              config=langfuse_config(recursion_limit=12))
    return result["messages"][-1].content


def main():
    graph = build_graph()
    for t in ["Hi, I'm alice. My VPN keeps dropping.", "Is there an outage for it?"]:
        print(f"\nalice: {t}\nagent: {chat(graph, 'alice-chat-1', 'alice', t)}")
    flush()


if __name__ == "__main__":
    main()
