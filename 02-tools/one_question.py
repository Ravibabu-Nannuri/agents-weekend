"""Block 02 - ONE question, printed step by step, so you can watch the loop.

Run:  .venv/bin/python 02-tools/one_question.py
      .venv/bin/python 02-tools/one_question.py "What's the status of ticket INC-1002?"
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from common.config import get_llm
from common.helpdesk import ALL_TOOLS, SYSTEM_PROMPT
from common.tracing import flush, langfuse_config, trace_attributes

question = sys.argv[1] if len(sys.argv) > 1 else "Is the VPN down right now?"

agent = create_agent(model=get_llm(), tools=ALL_TOOLS, system_prompt=SYSTEM_PROMPT, name="one-question")

with trace_attributes(tags=["block-02", "one-question"]):
    result = agent.invoke({"messages": [{"role": "user", "content": question}]},
                          config=langfuse_config(recursion_limit=12))

step = 0
for m in result["messages"]:
    step += 1
    if isinstance(m, HumanMessage):
        print(f"\nStep {step}  YOU asked:\n         {m.text}")
    elif isinstance(m, AIMessage) and m.tool_calls:
        for tc in m.tool_calls:
            print(f"\nStep {step}  CLAUDE asked your code to run a tool:\n         {tc['name']}({tc['args']})")
    elif isinstance(m, ToolMessage):
        print(f"\nStep {step}  YOUR CODE ran it and sent back:\n         {m.text}")
    elif isinstance(m, AIMessage):
        answer = m.text if len(m.text) < 400 else m.text[:400] + " ..."
        print(f"\nStep {step}  CLAUDE answered you:\n         {answer}")

print(f"\nModel calls in this run: {sum(isinstance(m, AIMessage) for m in result['messages'])}")
flush()
