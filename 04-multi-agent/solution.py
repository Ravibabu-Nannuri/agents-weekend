"""Block 04 - Multi-agent: a supervisor (router) + specialist agents.

           +--> kb_agent      (search_kb, check_system_status) --+
  router --+--> ticket_agent  (get_ticket, create_ticket, lookup_user) --> END
           +--> general       (no tools, polite small talk / off-topic) --+

Run:  python 04-multi-agent/solution.py
"""

import sys
from pathlib import Path
from typing import Literal

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_core.messages import AIMessage, SystemMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from pydantic import BaseModel, Field

from common.config import get_cheap_llm, get_llm
from common.graphs import build_tool_agent
from common.helpdesk import KB_TOOLS, TICKET_TOOLS
from common.tracing import flush, langfuse_config, trace_attributes

Specialist = Literal["kb_agent", "ticket_agent", "general"]


class Route(BaseModel):
    """Which specialist should handle the user's latest message."""
    agent: Specialist = Field(description=(
        "kb_agent: how-to questions or 'is X down?'. "
        "ticket_agent: look up / create tickets or user profiles. "
        "general: greetings, thanks, or anything not about IT."))
    reason: str = Field(description="One short sentence explaining the choice.")


class HelpdeskState(MessagesState):
    route: str  # extra state field: which specialist was chosen (handy in traces + evals)


ROUTER_PROMPT = "You are the triage desk of an IT helpdesk. Pick the best specialist for the user's latest message."
KB_PROMPT = "You are the IT knowledge specialist. Check system status and the knowledge base, then give clear steps."
TICKET_PROMPT = ("You are the IT ticket specialist. Look up or create tickets and user profiles. "
                 "Ask for the username if you need it. Always quote the ticket ID.")
GENERAL_PROMPT = ("You are the front desk of an IT helpdesk. Reply politely in one or two sentences. "
                  "If the request is not about IT, say you can only help with IT topics.")


def build_router(llm=None):
    # Routing is a classification task -> cheap, fast model + structured output.
    router_llm = (llm or get_cheap_llm()).with_structured_output(Route)

    def router(state: HelpdeskState):
        decision: Route = router_llm.invoke([SystemMessage(ROUTER_PROMPT)] + state["messages"])
        return {"route": decision.agent}

    return router


def build_graph(llm=None, router_llm=None, checkpointer=None):
    llm = llm or get_llm()
    kb_agent = build_tool_agent(llm, KB_TOOLS, KB_PROMPT, name="kb_agent")
    ticket_agent = build_tool_agent(llm, TICKET_TOOLS, TICKET_PROMPT, name="ticket_agent")

    def run_specialist(agent):
        def node(state: HelpdeskState):
            out = agent.invoke({"messages": state["messages"]})
            return {"messages": out["messages"][len(state["messages"]):]}  # only the new messages
        return node

    def general(state: HelpdeskState):
        reply = llm.invoke([SystemMessage(GENERAL_PROMPT)] + state["messages"])
        return {"messages": [AIMessage(content=reply.text)]}

    g = StateGraph(HelpdeskState)
    g.add_node("router", build_router(router_llm))
    g.add_node("kb_agent", run_specialist(kb_agent))
    g.add_node("ticket_agent", run_specialist(ticket_agent))
    g.add_node("general", general)
    g.add_edge(START, "router")
    g.add_conditional_edges("router", lambda s: s["route"], ["kb_agent", "ticket_agent", "general"])
    for n in ["kb_agent", "ticket_agent", "general"]:
        g.add_edge(n, END)
    return g.compile(checkpointer=checkpointer, name="helpdesk-supervisor")


QUESTIONS = [
    "How do I set up email on my phone?",
    "Wi-Fi in the office is broken again",
    "What's happening with INC-1001?",
    "Please open a ticket for carol: Slack crashes on startup",
    "Thanks, you're great!",
    "What's a good recipe for biryani?",
]


def main():
    graph = build_graph(router_llm=get_cheap_llm(), llm=get_llm(), checkpointer=InMemorySaver())
    print(graph.get_graph(xray=True).draw_mermaid())
    for i, q in enumerate(QUESTIONS):
        with trace_attributes(tags=["block-04"], session_id=f"demo-{i}"):
            result = graph.invoke({"messages": [{"role": "user", "content": q}]},
                                  config=langfuse_config(thread_id=f"demo-{i}", recursion_limit=20))
        print(f"\nQ: {q}\n  route: {result['route']}\n  A: {result['messages'][-1].text}")
    flush()


if __name__ == "__main__":
    main()
