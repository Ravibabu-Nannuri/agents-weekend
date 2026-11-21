"""Block 05 - Human-in-the-loop: pause before a risky action, wait for approval, resume.

Run:  python 05-human-in-the-loop/solution.py
      (it will stop and ask YOU to approve the password reset in the terminal)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command, interrupt

from common.config import get_llm
from common.graphs import build_tool_agent
from common.helpdesk import do_password_reset, lookup_user
from common.tracing import flush, langfuse_config, trace_attributes


@tool
def reset_password(username: str, reason: str) -> str:
    """Reset a user's password and email them a temporary one.
    This is a sensitive action: a human admin must approve it."""
    # interrupt() saves the graph state (needs a checkpointer!) and stops the run.
    # Whatever we pass here is shown to the human. The run resumes when someone
    # calls graph.invoke(Command(resume=...)) with the same thread_id -
    # seconds or days later, even from a different process.
    decision = interrupt({
        "action": "reset_password",
        "username": username,
        "reason": reason,
        "question": f"Approve password reset for '{username}'?",
    })
    if decision.get("approved"):
        return do_password_reset(username)
    return f"Password reset for {username} was DENIED by admin: {decision.get('note', 'no reason given')}"


ACCOUNT_PROMPT = (
    "You are the IT account specialist. You can look up users and reset passwords. "
    "Before resetting, make sure you know the username. If a reset is denied, "
    "tell the user politely and suggest the self-service portal id.example.com."
)


def build_graph(llm=None, checkpointer=None):
    return build_tool_agent(
        llm or get_llm(), [lookup_user, reset_password], ACCOUNT_PROMPT,
        checkpointer=checkpointer or InMemorySaver(), name="account-agent",
    )


def ask_human(payload: dict) -> dict:
    print("\n" + "=" * 60)
    print("⏸  APPROVAL NEEDED")
    for k, v in payload.items():
        print(f"   {k}: {v}")
    answer = input("   Approve? [y/N]: ").strip().lower()
    note = "" if answer == "y" else input("   Reason for denying: ").strip()
    print("=" * 60)
    return {"approved": answer == "y", "note": note}


def run_with_approval(graph, text: str, thread_id: str, approver=ask_human) -> str:
    config = langfuse_config(thread_id=thread_id, recursion_limit=15)
    with trace_attributes(session_id=thread_id, user_id="bob", tags=["block-05"]):
        result = graph.invoke({"messages": [{"role": "user", "content": text}]}, config=config)
        # While the graph is paused, the result contains "__interrupt__"
        while "__interrupt__" in result:
            payload = result["__interrupt__"][0].value
            decision = approver(payload)
            result = graph.invoke(Command(resume=decision), config=config)
    return result["messages"][-1].text


def main():
    graph = build_graph()
    text = "Hi, this is bob. I'm locked out of my account, please reset my password."
    print(f"bob: {text}")
    print(f"agent: {run_with_approval(graph, text, thread_id='bob-reset-1')}")

    # The paused state lived in the checkpointer. Show the history:
    history = list(graph.get_state_history({"configurable": {"thread_id": "bob-reset-1"}}))
    print(f"\n{len(history)} checkpoints saved for this thread (that's what made pause/resume possible).")
    flush()


if __name__ == "__main__":
    main()
