"""Block 02 - STARTER. Build the agent loop by hand.

Run:  python 02-tools/starter.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_core.messages import SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from common.config import get_llm
from common.helpdesk import ALL_TOOLS, SYSTEM_PROMPT
from common.tracing import flush, langfuse_config, trace_attributes


def build_graph(llm=None):
    # TODO 1: give the model the tool schemas -> llm.bind_tools(ALL_TOOLS)
    llm_with_tools = ...

    def call_model(state: MessagesState):
        messages = [SystemMessage(SYSTEM_PROMPT)] + state["messages"]
        # TODO 2: invoke the model and return {"messages": [response]}
        ...

    g = StateGraph(MessagesState)
    g.add_node("model", call_model)
    # TODO 3: add a "tools" node using ToolNode(ALL_TOOLS)
    g.add_edge(START, "model")
    # TODO 4: add a conditional edge from "model" using tools_condition
    # TODO 5: add the edge that turns this into a LOOP (tools -> ?)
    return g.compile()


def main():
    graph = build_graph(get_llm())
    print(graph.get_graph().draw_mermaid())
    q = "Is the VPN down right now? It keeps dropping."
    with trace_attributes(tags=["block-02", "starter"]):
        result = graph.invoke({"messages": [{"role": "user", "content": q}]},
                              config=langfuse_config(recursion_limit=12))
    print(result["messages"][-1].content)
    flush()


if __name__ == "__main__":
    main()
