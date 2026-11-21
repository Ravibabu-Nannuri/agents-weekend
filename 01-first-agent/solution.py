"""Block 01 - Your first agent, traced in Langfuse.

Run:  python 01-first-agent/solution.py
Then open Langfuse -> Tracing and click the newest trace.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain.agents import create_agent

from common.config import get_llm
from common.helpdesk import SYSTEM_PROMPT
from common.tracing import flush, langfuse_config, trace_attributes


def build_agent(llm=None):
    # An "agent" with no tools is just: model + instructions + a loop.
    # With nothing to act on, the loop runs exactly once.
    return create_agent(
        model=llm or get_llm(),
        tools=[],
        system_prompt=SYSTEM_PROMPT,
        name="helpdesk-v1",
    )


def main():
    agent = build_agent()
    question = "My VPN keeps disconnecting. What should I do?"

    with trace_attributes(tags=["block-01"], user_id="alice"):
        result = agent.invoke(
            {"messages": [{"role": "user", "content": question}]},
            config=langfuse_config(),
        )

    print("Q:", question)
    print("A:", result["messages"][-1].text)
    flush()


if __name__ == "__main__":
    main()
