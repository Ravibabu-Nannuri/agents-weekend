"""Block 02 - Tools, and "opening the box" of the prebuilt agent.

Part A: prebuilt agent with tools (create_agent).
Part B: the SAME agent hand-built as a LangGraph StateGraph, so you can see the loop.

Run:  python 02-tools/solution.py          (runs both)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain.agents import create_agent
from langchain_core.messages import SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from common.config import get_llm
from common.helpdesk import ALL_TOOLS, SYSTEM_PROMPT
from common.tracing import flush, langfuse_config, trace_attributes


# ---------------------------------------------------------------- Part A
def build_prebuilt(llm=None):
    return create_agent(model=llm or get_llm(), tools=ALL_TOOLS, system_prompt=SYSTEM_PROMPT)


# ---------------------------------------------------------------- Part B
def build_graph(llm=None, max_tool_rounds: int = 5):
    """model -> (tool calls?) -> tools -> model -> ... -> END

    This is the ReAct loop: Reason (model) -> Act (tools) -> Observe (tool result) -> repeat.
    """
    llm_with_tools = (llm or get_llm()).bind_tools(ALL_TOOLS)

    def call_model(state: MessagesState):
        # The model sees the whole conversation so far, including tool results.
        messages = [SystemMessage(SYSTEM_PROMPT)] + state["messages"]
        return {"messages": [llm_with_tools.invoke(messages)]}

    g = StateGraph(MessagesState)
    g.add_node("model", call_model)
    g.add_node("tools", ToolNode(ALL_TOOLS))
    g.add_edge(START, "model")
    # tools_condition: if the last AI message has tool_calls -> "tools", else -> END
    g.add_conditional_edges("model", tools_condition)
    g.add_edge("tools", "model")  # <- this edge is what makes it a LOOP
    return g.compile(name="helpdesk-handbuilt")


QUESTIONS = [
    "Is the VPN down right now? It keeps dropping.",
    "What's the status of ticket INC-1002?",
    "The 3rd floor printer isn't working, can you open a ticket for bob?",
]


def run(agent, label):
    for q in QUESTIONS:
        with trace_attributes(tags=["block-02", label]):
            # recursion_limit = hard cap on loop steps (safety net against runaway agents)
            result = agent.invoke(
                {"messages": [{"role": "user", "content": q}]},
                config=langfuse_config(recursion_limit=12),
            )
        tool_calls = [tc["name"] for m in result["messages"] for tc in getattr(m, "tool_calls", []) or []]
        print(f"\n[{label}] Q: {q}\n  tools used: {tool_calls}\n  A: {result['messages'][-1].text}")


def main():
    run(build_prebuilt(), "prebuilt")
    graph = build_graph()
    print("\nGraph structure (paste into mermaid.live):\n")
    print(graph.get_graph().draw_mermaid())
    run(graph, "handbuilt")
    flush()


if __name__ == "__main__":
    main()
