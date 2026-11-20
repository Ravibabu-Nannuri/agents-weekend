"""Shared configuration: loads .env and builds the chat models used by every block.

Works with Claude (default) or OpenAI - set LLM_PROVIDER in .env.
Each friend can use whichever key they have; the code doesn't change.
"""

import os

from dotenv import load_dotenv

load_dotenv()

PROVIDER = os.getenv("LLM_PROVIDER", "anthropic").lower()  # "anthropic" or "openai"

_DEFAULTS = {
    # Two models on purpose: a cheap/fast one for routing and guardrails,
    # a stronger one for the actual answers. (Block 07 talks about why.)
    "anthropic": {"main": "claude-sonnet-5-5", "cheap": "claude-haiku-5-5"},
    "openai": {"main": "gpt-4.1-mini", "cheap": "gpt-4.1-nano"},
}

DEFAULT_MODEL = os.getenv("MODEL", _DEFAULTS[PROVIDER]["main"])
CHEAP_MODEL = os.getenv("CHEAP_MODEL", _DEFAULTS[PROVIDER]["cheap"])


def get_llm(model: str | None = None, temperature: float | None = None):
    """Return a LangChain chat model for the configured provider.
    Imported lazily so the tests can run without any API key.

    Note: newer Claude models reject `temperature`, so we only send it when asked for.
    """
    from langchain.chat_models import init_chat_model

    kwargs = {"max_tokens": 1024}
    if temperature is not None:
        kwargs["temperature"] = temperature
    return init_chat_model(model or DEFAULT_MODEL, model_provider=PROVIDER, **kwargs)


def get_cheap_llm():
    return get_llm(CHEAP_MODEL)
