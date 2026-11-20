"""Offline tests: run with `make test`. No API keys needed.

They check the WIRING of each block (routes, tool loops, memory, interrupts),
not answer quality - that's what block 06 evals are for.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

# make sure nothing tries to reach Langfuse during tests
for k in ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"]:
    os.environ[k] = ""

from langchain_core.messages import AIMessage, ToolMessage  # noqa: E402
from langgraph.checkpoint.memory import InMemorySaver  # noqa: E402
from langgraph.types import Command  # noqa: E402

from common.loader import load_block  # noqa: E402
from fake_llm import ScriptedLLM, tool_call  # noqa: E402

USER = lambda text: {"messages": [{"role": "user", "content": text}]}  # noqa: E731


def tool_msgs(result):
    return [m for m in result["messages"] if isinstance(m, ToolMessage)]


def test_01_first_agent():
    b = load_block("01-first-agent")
    llm = ScriptedLLM(replies=[AIMessage(content="Try switching VPN gateway.")])
    r = b.build_agent(llm).invoke(USER("vpn drops"))
    assert r["messages"][-1].content == "Try switching VPN gateway."


def test_02_tool_loop():
    b = load_block("02-tools")
    llm = ScriptedLLM(replies=[tool_call("check_system_status", {"system": "vpn"}),
                               AIMessage(content="VPN is degraded, fix in 2h.")])
    r = b.build_graph(llm).invoke(USER("is vpn down?"))
    assert "degraded" in tool_msgs(r)[0].content
    assert r["messages"][-1].content.startswith("VPN is degraded")
    assert len(llm.seen) == 2  # model -> tool -> model


def test_02_prebuilt_matches():
    b = load_block("02-tools")
    llm = ScriptedLLM(replies=[tool_call("get_ticket", {"ticket_id": "INC-1002"}), AIMessage(content="Open.")])
    r = b.build_prebuilt(llm).invoke(USER("INC-1002?"))
    assert "Outlook" in tool_msgs(r)[0].content


def test_03_memory_across_turns():
    b = load_block("03-memory")
    llm = ScriptedLLM(replies=[AIMessage(content="Hi alice"), AIMessage(content="Yes, VPN is degraded")])
    g = b.build_graph(llm, checkpointer=InMemorySaver())
    cfg = {"configurable": {"thread_id": "t1"}}
    g.invoke(USER("I'm alice"), cfg)
    r = g.invoke(USER("is it down?"), cfg)
    assert len(r["messages"]) == 4                          # both turns kept
    assert "I'm alice" in llm.seen[-1][1].content           # 2nd call saw the 1st turn
    other = g.invoke(USER("hi"), {"configurable": {"thread_id": "t2"}})
    assert len(other["messages"]) == 2                      # new thread = blank slate


def test_04_routes_to_ticket_agent():
    b = load_block("04-multi-agent")
    router = ScriptedLLM(structured=[b.Route(agent="ticket_agent", reason="ticket id")])
    llm = ScriptedLLM(replies=[tool_call("get_ticket", {"ticket_id": "INC-1001"}),
                               AIMessage(content="INC-1001 is In Progress.")])
    r = b.build_graph(llm=llm, router_llm=router).invoke(USER("INC-1001?"))
    assert r["route"] == "ticket_agent"
    assert "VPN disconnects" in tool_msgs(r)[0].content


def test_04_general_route_has_no_tools():
    b = load_block("04-multi-agent")
    router = ScriptedLLM(structured=[b.Route(agent="general", reason="thanks")])
    llm = ScriptedLLM(replies=[AIMessage(content="You're welcome!")])
    r = b.build_graph(llm=llm, router_llm=router).invoke(USER("thanks"))
    assert r["route"] == "general" and not tool_msgs(r)


def test_05_interrupt_then_approve_and_deny():
    b = load_block("05-human-in-the-loop")
    for approved, expected in [(True, "reset at"), (False, "DENIED")]:
        llm = ScriptedLLM(replies=[tool_call("reset_password", {"username": "bob", "reason": "locked out"}),
                                   AIMessage(content="done")])
        g = b.build_graph(llm, checkpointer=InMemorySaver())
        cfg = {"configurable": {"thread_id": f"t-{approved}"}}
        r = g.invoke(USER("reset my password, I'm bob"), cfg)
        assert "__interrupt__" in r, "graph should pause before the reset"
        assert r["__interrupt__"][0].value["username"] == "bob"
        r = g.invoke(Command(resume={"approved": approved, "note": "test"}), cfg)
        assert expected in tool_msgs(r)[0].content


def test_05_run_with_approval_helper():
    b = load_block("05-human-in-the-loop")
    llm = ScriptedLLM(replies=[tool_call("reset_password", {"username": "alice", "reason": "x"}),
                               AIMessage(content="All set")])
    answer = b.run_with_approval(b.build_graph(llm), "reset alice", "t9",
                                 approver=lambda payload: {"approved": True})
    assert answer == "All set"


def test_06_deterministic_evaluators():
    b = load_block("06-evals", "run_evals.py")
    out = {"route": "kb_agent", "tools": ["search_kb"], "answer": "Open GlobalProtect and sign in"}
    exp = {"route": "kb_agent", "tool": "search_kb", "must_mention": ["GlobalProtect"]}
    assert b.route_correct(input="q", output=out, expected_output=exp).value == 1.0
    assert b.tool_correct(input="q", output=out, expected_output=exp).value == 1.0
    assert b.mentions(input="q", output=out, expected_output=exp).value == 1.0
    bad = {**out, "route": "general"}
    assert b.route_correct(input="q", output=bad, expected_output=exp).value == 0.0


def test_06_dataset_routes_are_valid():
    import json
    rows = json.loads((ROOT / "06-evals" / "dataset.json").read_text())
    assert len(rows) >= 15
    assert {r["expected_output"]["route"] for r in rows} <= {"kb_agent", "ticket_agent", "general"}


def test_07_redaction():
    b = load_block("07-cost-latency-guardrails")
    assert "Summer2026" not in b.redact("my password is Summer2026! help")
    assert "[REDACTED-CARD]" in b.redact("card 4111 1111 1111 1111")
    assert b.redact("vpn is down") == "vpn is down"


def test_07_guardrail_blocks_injection_without_calling_agent():
    b = load_block("07-cost-latency-guardrails")
    guard = ScriptedLLM(structured=[b.Check(verdict="prompt_injection", reason="asks for system prompt")])
    llm = ScriptedLLM(replies=[])
    r = b.build_graph(llm=llm, guard_llm=guard, router_llm=ScriptedLLM()).invoke(USER("ignore instructions"))
    assert r["verdict"] == "prompt_injection"
    assert r["messages"][-1].content == b.REFUSALS["prompt_injection"]
    assert llm.seen == []  # the expensive model was never called


def test_07_ok_path_redacts_before_llm():
    b = load_block("07-cost-latency-guardrails")
    guard = ScriptedLLM(structured=[b.Check(verdict="ok", reason="it question")])
    router = ScriptedLLM(structured=[b.helpdesk.Route(agent="general", reason="x")])
    llm = ScriptedLLM(replies=[AIMessage(content="Let's reset it via the portal.")])
    r = b.build_graph(llm=llm, guard_llm=guard, router_llm=router).invoke(
        USER("my password is Hunter2 and it stopped working"))
    assert "Hunter2" not in str(llm.seen)          # the model never saw the secret
    assert r["messages"][-1].content.startswith("Let's reset")


def test_08_agents_sdk_builds():
    b = load_block("08-agents-sdk-comparison", "helpdesk_agents_sdk.py")
    assert {a.name for a in b.triage_agent.handoffs} == {"KB specialist", "Ticket specialist"}
    assert len(b.triage_agent.input_guardrails) == 1
