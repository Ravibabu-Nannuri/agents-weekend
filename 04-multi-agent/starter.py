"""Block 04 - STARTER. Wire up the supervisor graph.

The specialists and the router are done for you. Your job: the edges.
Run:  python 04-multi-agent/starter.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_core.messages import AIMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from common.config import get_cheap_llm, get_llm
from common.graphs import build_tool_agent
from common.helpdesk import KB_TOOLS, TICKET_TOOLS
from common.loader import load_block
from common.tracing import flush, langfuse_config, trace_attributes

sol = load_block("04-multi-agent")  # reuse Route, prompts and build_router from the solution


def build_graph(llm=None, router_llm=None):
    llm = llm or get_llm()
    kb_agent = build_tool_agent(llm, KB_TOOLS, sol.KB_PROMPT, name="kb_agent")
    ticket_agent = build_tool_agent(llm, TICKET_TOOLS, sol.TICKET_PROMPT, name="ticket_agent")

    def run_specialist(agent):
        def node(state):
            out = agent.invoke({"messages": state["messages"]})
            return {"messages": out["messages"][len(state["messages"]):]}
        return node

    def general(state):
        reply = llm.invoke([SystemMessage(sol.GENERAL_PROMPT)] + state["messages"])
        return {"messages": [AIMessage(content=reply.content)]}

    g = StateGraph(sol.HelpdeskState)
    g.add_node("router", sol.build_router(router_llm))
    g.add_node("kb_agent", run_specialist(kb_agent))
    g.add_node("ticket_agent", run_specialist(ticket_agent))
    g.add_node("general", general)

    # TODO 1: START -> router
    # TODO 2: conditional edge from "router": read state["route"] and go to that node
    #         hint: g.add_conditional_edges("router", lambda s: ..., [list of node names])
    # TODO 3: every specialist -> END
    return g.compile()


def main():
    graph = build_graph(router_llm=get_cheap_llm())
    for q in ["How do I set up email on my phone?", "What's happening with INC-1001?", "Thanks!"]:
        with trace_attributes(tags=["block-04", "starter"]):
            r = graph.invoke({"messages": [{"role": "user", "content": q}]}, config=langfuse_config(recursion_limit=20))
        print(f"\nQ: {q}\n  route: {r['route']}\n  A: {r['messages'][-1].content}")
    flush()


if __name__ == "__main__":
    main()
