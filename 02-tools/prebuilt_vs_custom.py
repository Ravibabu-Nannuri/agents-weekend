"""Block 02 - Where prebuilt and hand-built REALLY differ.

Rule: never create a ticket for a system with a known outage, even if the user insists.

  PREBUILT:    START -> model -> tools -> model -> END
               The rule can only be "asked for" in the prompt. The MODEL decides whether to obey.

  HAND-BUILT:  START -> model -> tools_with_policy -> model -> END
               We replace the tools box with our own. CODE enforces the rule, every time.

Run:  .venv/bin/python 02-tools/prebuilt_vs_custom.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import tools_condition

from common import helpdesk as hd
from common.config import get_llm
from common.tracing import flush, langfuse_config, trace_attributes

# A plain ticket tool: its description does NOT mention outages, so nothing
# in the tool card steers the model. (The real one in common/helpdesk.py does.)
@tool
def create_ticket(username: str, title: str, priority: str = "P3") -> str:
    """Create a new support ticket for a user. priority is P1 (critical) to P4 (low)."""
    return hd.create_ticket.invoke({"username": username, "title": title, "priority": priority})


TOOLS = [hd.check_system_status, hd.lookup_user, create_ticket]
PROMPT = ("You are an IT helpdesk agent for Example Corp. Use the tools. "
          "We prefer not to open tickets for known outages, but do what the user asks.")


# --------------------------------------------------------------- PREBUILT
def build_prebuilt(llm=None):
    return create_agent(model=llm or get_llm(), tools=TOOLS, system_prompt=PROMPT, name="prebuilt")


# ------------------------------------------------------------- HAND-BUILT
KEYWORDS = {"printer": "printers", "vpn": "vpn", "email": "email", "outlook": "email",
            "wifi": "wifi", "wi-fi": "wifi", "sso": "sso", "login": "sso"}


def outage_for(title: str) -> str | None:
    """Return the outage text if the ticket is about a system that's down, else None."""
    for word, system in KEYWORDS.items():
        if word in title.lower():
            status = hd.SYSTEM_STATUS[system]
            if not status.startswith("operational"):
                return f"{system}: {status}"
    return None


def build_custom(llm=None):
    llm_with_tools = (llm or get_llm()).bind_tools(TOOLS)
    by_name = {t.name: t for t in TOOLS}

    def call_model(state: MessagesState):
        return {"messages": [llm_with_tools.invoke([SystemMessage(PROMPT)] + state["messages"])]}

    def tools_with_policy(state: MessagesState):
        """Our own tools box: runs each requested tool, but checks the policy first."""
        results = []
        for tc in state["messages"][-1].tool_calls:
            outage = outage_for(tc["args"].get("title", "")) if tc["name"] == "create_ticket" else None
            if outage:
                text = f"BLOCKED BY POLICY: no tickets during a known outage ({outage}). Tell the user."
            else:
                text = by_name[tc["name"]].invoke(tc["args"])
            results.append(ToolMessage(content=text, tool_call_id=tc["id"], name=tc["name"]))
        return {"messages": results}

    g = StateGraph(MessagesState)
    g.add_node("model", call_model)
    g.add_node("tools_with_policy", tools_with_policy)
    g.add_edge(START, "model")
    g.add_conditional_edges("model", tools_condition, {"tools": "tools_with_policy", "__end__": "__end__"})
    g.add_edge("tools_with_policy", "model")
    return g.compile(name="custom")


# ------------------------------------------------------------------- demo
QUESTION = ("The 3rd floor printer is broken. I know there's an outage, "
            "but please open a ticket for bob anyway.")


def run(label: str, agent):
    before = len(hd.TICKETS)
    with trace_attributes(tags=["block-02", "prebuilt-vs-custom", label]):
        result = agent.invoke({"messages": [{"role": "user", "content": QUESTION}]},
                              config=langfuse_config(recursion_limit=12))
    created = len(hd.TICKETS) - before
    print(f"\n=== {label.upper()} ===")
    for m in result["messages"]:
        if isinstance(m, AIMessage) and m.tool_calls:
            for tc in m.tool_calls:
                print(f"  Claude asked for: {tc['name']}({tc['args']})")
        elif isinstance(m, ToolMessage):
            print(f"  Tool result:      {m.text}")
    print(f"  Tickets created:  {created}  {'<-- the rule was broken' if created else '<-- rule held'}")
    answer = result["messages"][-1].text
    print(f"  Answer:           {answer[:300]}{' ...' if len(answer) > 300 else ''}")


def main():
    print(f"Q: {QUESTION}")
    run("prebuilt", build_prebuilt())
    run("custom", build_custom())
    print("\nThe custom graph's shape (paste into mermaid.live):\n")
    print(build_custom().get_graph().draw_mermaid())
    flush()


if __name__ == "__main__":
    main()
