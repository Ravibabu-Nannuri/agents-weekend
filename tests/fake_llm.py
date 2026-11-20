"""A scripted fake chat model: returns pre-written replies in order.

Lets us test graph wiring (routing, tool loops, interrupts) offline, with no keys and no cost.
"""

from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import RunnableLambda


class ScriptedLLM(BaseChatModel):
    replies: list = []          # AIMessages, consumed in order
    structured: list = []       # pydantic objects for with_structured_output, consumed in order
    seen: list = []             # every message list the model was called with

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs: Any) -> ChatResult:
        self.seen.append(messages)
        reply = self.replies.pop(0) if self.replies else AIMessage(content="(no more scripted replies)")
        return ChatResult(generations=[ChatGeneration(message=reply)])

    def bind_tools(self, tools, **kwargs):
        return self

    def with_structured_output(self, schema, **kwargs):
        return RunnableLambda(lambda _input: self.structured.pop(0))


def tool_call(name: str, args: dict, call_id: str = "call_1") -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])
