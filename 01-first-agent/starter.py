"""Block 01 - STARTER. Fill in the TODOs, then compare with solution.py.

Run:  python 01-first-agent/starter.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain.agents import create_agent

from common.config import get_llm
from common.helpdesk import SYSTEM_PROMPT
from common.tracing import flush, langfuse_config, trace_attributes


def build_agent(llm=None):
    return create_agent(
        model=llm or get_llm(),
        tools=[],
        system_prompt=SYSTEM_PROMPT,
        name="helpdesk-v1",
    )



def main():
    agent = build_agent()
    question = "My VPN keeps disconnecting. What should I do?"

    with trace_attributes(tags=["ravi-01"], user_id="Ravi"):
        # TODO 2: call agent.invoke with {"messages": [...]} and
        #         config=langfuse_config() so the run is traced.
        result = agent.invoke(
                    {"messages": [{"role": "user", "content": question}]},
                    config=langfuse_config(),
                )

    print("A:", result["messages"][-1].text)
    # TODO 3: why do we need this line? (hint: short scripts)
    #flush()


if __name__ == "__main__":
    main()
