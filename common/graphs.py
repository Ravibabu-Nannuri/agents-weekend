"""Reusable version of the hand-built ReAct graph from block 02."""

from langchain_core.messages import SystemMessage
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition


def build_tool_agent(llm, tools, system_prompt: str, checkpointer=None, name: str = "agent"):
    llm_with_tools = llm.bind_tools(tools)

    def call_model(state: MessagesState):
        return {"messages": [llm_with_tools.invoke([SystemMessage(system_prompt)] + state["messages"])]}

    g = StateGraph(MessagesState)
    g.add_node("model", call_model)
    g.add_node("tools", ToolNode(tools))
    g.add_edge(START, "model")
    g.add_conditional_edges("model", tools_condition)
    g.add_edge("tools", "model")
    return g.compile(checkpointer=checkpointer, name=name)
