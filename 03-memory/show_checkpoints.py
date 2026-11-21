"""Block 03 - Look inside the checkpointer: print every save point for one question.

Run:  .venv/bin/python 03-memory/show_checkpoints.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langgraph.checkpoint.memory import InMemorySaver

from common.config import get_llm
from common.graphs import build_tool_agent
from common.helpdesk import ALL_TOOLS, SYSTEM_PROMPT


def describe(m) -> str:
    kind = type(m).__name__.replace("Message", "")
    if getattr(m, "tool_calls", None):
        return f"{kind}(asks for {[tc['name'] for tc in m.tool_calls]})"
    text = (m.text or "").replace("\n", " ")
    return f"{kind}({text[:40]}{'...' if len(text) > 40 else ''})"


def show(graph, thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    history = list(graph.get_state_history(config))     # newest first
    print(f"\n{len(history)} checkpoints for thread '{thread_id}' (oldest first):\n")
    for cp in reversed(history):
        step = cp.metadata.get("step")
        msgs = cp.values.get("messages", [])
        nxt = cp.next or ("END",)
        print(f"  step {step:>2} | next: {', '.join(nxt):<6} | {len(msgs)} messages | last: "
              f"{describe(msgs[-1]) if msgs else '-'}")


def main(llm=None):
    saver = InMemorySaver()
    graph = build_tool_agent(llm or get_llm(), ALL_TOOLS, SYSTEM_PROMPT, checkpointer=saver)
    config = {"configurable": {"thread_id": "demo-1"}}

    graph.invoke({"messages": [{"role": "user", "content": "Is the VPN down?"}]}, config)
    show(graph, "demo-1")

    # Peek at the raw storage: a dict keyed by thread_id
    print(f"\nRaw storage keys (thread ids): {list(saver.storage.keys())}")
    latest = saver.get_tuple(config)
    print(f"Latest checkpoint id: {latest.checkpoint['id']}")
    print(f"Its parent:           {latest.parent_config['configurable']['checkpoint_id']}")


if __name__ == "__main__":
    main()
