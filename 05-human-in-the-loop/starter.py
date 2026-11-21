"""Block 05 - STARTER. Add human approval before a password reset.

Run:  python 05-human-in-the-loop/starter.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command, interrupt  # noqa: F401  (you'll need both)

from common.config import get_llm
from common.graphs import build_tool_agent
from common.helpdesk import do_password_reset, lookup_user
from common.loader import load_block
from common.tracing import flush, langfuse_config

sol = load_block("05-human-in-the-loop")


@tool
def reset_password(username: str, reason: str) -> str:
    """Reset a user's password and email them a temporary one.
    This is a sensitive action: a human admin must approve it."""
    # TODO 1: call interrupt({...}) with the username and reason, and store the
    #         human's answer in `decision` (a dict like {"approved": True})
    decision = {"approved": True}  # <- right now it just resets. Dangerous!
    if decision.get("approved"):
        return do_password_reset(username)
    return f"Password reset for {username} was DENIED by admin."


def main():
    # TODO 2: why does interrupt() need a checkpointer? Try removing it and see the error.
    graph = build_tool_agent(get_llm(), [lookup_user, reset_password], sol.ACCOUNT_PROMPT,
                             checkpointer=InMemorySaver())
    config = langfuse_config(thread_id="starter-1", recursion_limit=15)
    result = graph.invoke({"messages": [{"role": "user", "content": "I'm bob, reset my password please"}]},
                          config=config)

    # TODO 3: while "__interrupt__" in result: show result["__interrupt__"][0].value,
    #         ask for y/n with input(), then resume with graph.invoke(Command(resume={...}), config=config)

    print(result["messages"][-1].text)
    flush()


if __name__ == "__main__":
    main()
