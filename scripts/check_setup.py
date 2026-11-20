"""Run before the weekend:  make check   (or: python scripts/check_setup.py)

Checks Python version, packages, API keys, one tiny model call, and Langfuse auth.
"""

import importlib
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

OK, BAD = "✅", "❌"
failed = False


def check(label, fn):
    global failed
    try:
        detail = fn()
        print(f"{OK} {label}" + (f" – {detail}" if detail else ""))
    except Exception as e:  # noqa: BLE001
        failed = True
        print(f"{BAD} {label} – {type(e).__name__}: {str(e)[:200]}")


def py():
    if sys.version_info < (3, 11):
        raise RuntimeError(f"need Python 3.11+, you have {sys.version.split()[0]}")
    return sys.version.split()[0]


def packages():
    for mod in ["langgraph", "langchain", "langchain_anthropic", "langfuse", "agents", "dotenv"]:
        importlib.import_module(mod)
    return "all importable"


def env_file():
    if not Path(".env").exists():
        raise FileNotFoundError("no .env – run: cp .env.example .env  and fill in your keys")
    from common.config import PROVIDER
    key = "ANTHROPIC_API_KEY" if PROVIDER == "anthropic" else "OPENAI_API_KEY"
    missing = [k for k in [key, "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"]
               if not os.getenv(k) or os.getenv(k, "").endswith("...")]
    if missing:
        raise ValueError(f"fill in: {', '.join(missing)}")
    return f"provider={PROVIDER}"


def model_call():
    from common.config import CHEAP_MODEL, DEFAULT_MODEL, get_cheap_llm, get_llm
    for llm, name in [(get_cheap_llm(), CHEAP_MODEL), (get_llm(), DEFAULT_MODEL)]:
        llm.invoke("Reply with the single word: pong")
    return f"{CHEAP_MODEL} and {DEFAULT_MODEL} both answered"


def langfuse_auth():
    from langfuse import get_client
    if not get_client().auth_check():
        raise PermissionError("keys rejected – check LANGFUSE_* and LANGFUSE_BASE_URL region")
    return os.getenv("LANGFUSE_BASE_URL", "")


check("Python version", py)
check("Packages installed", packages)
check(".env and keys", env_file)
check("Model call", model_call)
check("Langfuse connection", langfuse_auth)

print("\n🎉 Ready for the weekend!" if not failed else "\nFix the ❌ items above, then run again.")
sys.exit(1 if failed else 0)
