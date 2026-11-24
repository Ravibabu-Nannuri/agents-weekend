"""Block 03 - Watch the messages list grow, step by step, across 3 turns of one conversation.

Run:  .venv/bin/python 03-memory/watch_messages.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langgraph.checkpoint.memory import InMemorySaver

from common.config import get_llm
from common.graphs import build_tool_agent
from common.helpdesk import ALL_TOOLS, SYSTEM_PROMPT
from common.tracing import flush, langfuse_config, trace_attributes

TURNS = [
    "Hi, I'm alice. My VPN keeps dropping.",
    "Is there an outage for it?",
    "OK. And what laptop do I have on record?",
]


def describe(m) -> str:
    kind = type(m).__name__.replace("Message", "")
    if getattr(m, "tool_calls", None):
        calls = ", ".join(f"{tc['name']}({', '.join(str(v) for v in tc['args'].values())})" for tc in m.tool_calls)
        return f"{kind:<6} asks for tools: {calls}"
    text = (m.text or "").replace("\n", " ")
    return f"{kind:<6} {text[:70]}{'...' if len(text) > 70 else ''}"


def main(llm=None):
    graph = build_tool_agent(llm or get_llm(), ALL_TOOLS, SYSTEM_PROMPT,
                             checkpointer=InMemorySaver(), name="watch-messages")
    thread = "ravi-watch-1"
    config = langfuse_config(thread_id=thread, recursion_limit=12)
    total = 0

    for n, text in enumerate(TURNS, start=1):
        saved = graph.get_state({"configurable": {"thread_id": thread}}).values.get("messages", [])
        print(f"\n{'=' * 78}\nTURN {n}: \"{text}\"")
        print(f"  checkpointer loaded {len(saved)} saved messages for thread '{thread}'")
        print(f"  you send 1 new message -> Claude will see {len(saved) + 1} (+ the system prompt)\n")
        total = len(saved)
        print(f"  your input     +1 -> {total + 1} messages")
        print(f"      [{total}] Human  {text}")
        total += 1

        with trace_attributes(session_id=thread, user_id="alice", tags=["block-03", "watch"]):
            # stream_mode="updates" yields what each box added, one step at a time
            for chunk in graph.stream({"messages": [{"role": "user", "content": text}]},
                                      config, stream_mode="updates"):
                for node, update in chunk.items():
                    if not update or "messages" not in update:
                        continue
                    new = update["messages"]
                    if node == "__start__":
                        node = "input"
                    print(f"  after {node:<6}  +{len(new)} -> {total + len(new)} messages")
                    for m in new:
                        print(f"      [{total}] {describe(m)}")
                        total += 1

    print(f"\n{'=' * 78}\nFINAL STATE of '{thread}': {total} messages")
    final = graph.get_state({"configurable": {"thread_id": thread}}).values["messages"]
    for i, m in enumerate(final):
        print(f"  [{i:>2}] {describe(m)}")
    print(f"\nresult['messages'][-1] is always the last one: [{len(final) - 1}]")
    flush()


if __name__ == "__main__":
    main()
