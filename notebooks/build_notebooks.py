"""Generates the walkthrough notebooks. Run: .venv/bin/python notebooks/build_notebooks.py"""

from pathlib import Path

import nbformat as nbf

HERE = Path(__file__).parent

SETUP = '''# Setup: run this cell first. It finds the repo, makes it importable and loads .env
import os, sys, pathlib

def find_repo_root():
    starts = []
    if "__vsc_ipynb_file__" in globals():                 # VS Code tells us where this notebook is
        starts.append(pathlib.Path(globals()["__vsc_ipynb_file__"]).resolve().parent)
    starts.append(pathlib.Path.cwd().resolve())
    for start in starts:
        for folder in [start, *start.parents]:
            if (folder / "common" / "config.py").exists():
                return folder
            if (folder / "agents-weekend" / "common" / "config.py").exists():
                return folder / "agents-weekend"
    raise RuntimeError(f"Can't find the agents-weekend repo from {starts}. "
                       "Open the agents-weekend folder in VS Code, or set ROOT by hand.")

ROOT = find_repo_root()
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
print("repo:", ROOT)

from common.config import get_llm, get_cheap_llm, DEFAULT_MODEL, CHEAP_MODEL
from common.tracing import langfuse_config, trace_attributes, flush, tracing_enabled
print("main model:", DEFAULT_MODEL, "| cheap model:", CHEAP_MODEL, "| Langfuse:", tracing_enabled())'''

DESCRIBE = '''def describe(m):
    """One readable line per message."""
    kind = type(m).__name__.replace("Message", "")
    if getattr(m, "tool_calls", None):
        return f"{kind:<6} asks for: " + ", ".join(f"{tc['name']}({tc['args']})" for tc in m.tool_calls)
    text = (m.text or "").replace("\\n", " ")
    return f"{kind:<6} {text[:90]}{'...' if len(text) > 90 else ''}"'''


def nb(cells):
    book = nbf.v4.new_notebook()
    book.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    book.cells = [nbf.v4.new_markdown_cell(c[1]) if c[0] == "md" else nbf.v4.new_code_cell(c[1]) for c in cells]
    return book


NOTEBOOKS = {
"01-first-agent.ipynb": [
("md", """# Block 01 – Your first agent, one cell at a time

**You'll see:** what `create_agent` builds, what goes in and out, the raw content blocks vs `.text`, and the token count.

Select the `.venv` Python as the kernel (top right in VS Code), then run cells top to bottom."""),
("code", SETUP),
("md", "## 1. Build the agent\nNothing is sent to Claude yet. `create_agent` only builds a graph."),
("code", '''from langchain.agents import create_agent
from common.helpdesk import SYSTEM_PROMPT

agent = create_agent(model=get_llm(), tools=[], system_prompt=SYSTEM_PROMPT, name="helpdesk-v1")
print(type(agent).__name__)           # a LangGraph graph, even though we imported from langchain
print(agent.get_graph().draw_mermaid())'''),
("md", "## 2. Ask one question\nThe input is the **state**: a dict with a `messages` list."),
("code", '''question = "My VPN keeps disconnecting. What should I do?"
with trace_attributes(tags=["notebook-01"], user_id="notebook"):
    result = agent.invoke({"messages": [{"role": "user", "content": question}]}, config=langfuse_config())

for i, m in enumerate(result["messages"]):
    print(i, type(m).__name__)'''),
("md", "## 3. Raw content blocks vs `.text`\nNewer Claude models think first. `.content` is a list of blocks; `.text` is just the answer."),
("code", '''reply = result["messages"][-1]
print("block types:", [b["type"] for b in reply.content] if isinstance(reply.content, list) else "plain string")
print()
print(reply.text)'''),
("md", "## 4. Tokens\nThinking tokens are billed even though their text is hidden. Compare output tokens with the visible length."),
("code", '''usage = reply.usage_metadata
print(usage)
print("visible answer ~", len(reply.text) // 4, "tokens  vs  output_tokens =", usage["output_tokens"])'''),
("md", "## 5. Send the trace\nThen open Langfuse → Tracing → filter tag `notebook-01`."),
("code", "flush()"),
],

"02-tools.ipynb": [
("md", """# Block 02 – Tools and the loop, one step at a time

**You'll see:** a tool card, the loop running step by step, and where prebuilt and hand-built graphs really differ."""),
("code", SETUP),
("code", DESCRIBE),
("md", "## 1. A tool card\nClaude never sees your code, only this."),
("code", '''from common.helpdesk import check_system_status as t
print("NAME:       ", t.name)
print("DESCRIPTION:", t.description)
print("INPUTS:     ", t.args)'''),
("md", "## 2. Build the hand-built graph and look at it"),
("code", '''from common.loader import load_block
b02 = load_block("02-tools")
graph = b02.build_graph(get_llm())
print(graph.get_graph().draw_mermaid())'''),
("md", "## 3. Run the loop step by step\n`stream_mode='updates'` yields what each box added, in order."),
("code", '''q = "Is the VPN down right now? It keeps dropping."
total = 1
print("[0] Human ", q)
with trace_attributes(tags=["notebook-02"]):
    for chunk in graph.stream({"messages": [{"role": "user", "content": q}]},
                              config=langfuse_config(recursion_limit=12), stream_mode="updates"):
        for node, update in chunk.items():
            print(f"\\n--- after box: {node} ---")
            for m in update["messages"]:
                print(f"[{total}]", describe(m)); total += 1'''),
("md", "## 4. Prebuilt runs the same steps\nSame graph shape → same execution."),
("code", '''prebuilt = b02.build_prebuilt(get_llm())
steps = [node for chunk in prebuilt.stream({"messages": [{"role": "user", "content": q}]},
                                           config=langfuse_config(recursion_limit=12), stream_mode="updates")
         for node in chunk]
print("prebuilt steps:", steps)'''),
("md", "## 5. Where they really differ: a rule enforced in code\nThe custom graph replaces the `tools` box with `tools_with_policy`."),
("code", '''pvc = load_block("02-tools", "prebuilt_vs_custom.py")
print(pvc.QUESTION)
pvc.run("prebuilt", pvc.build_prebuilt())
pvc.run("custom", pvc.build_custom())'''),
("code", "flush()"),
],

"03-memory.ipynb": [
("md", """# Block 03 – Memory, one turn per cell

**You'll see:** the `messages` list grow turn by turn, a new thread starting blank, and the checkpoints behind it.

Run each turn cell **once**. Re-running a cell adds another turn to the same thread."""),
("code", SETUP),
("code", DESCRIBE),
("md", "## 1. Build the agent with a checkpointer"),
("code", '''from langgraph.checkpoint.memory import InMemorySaver
from common.graphs import build_tool_agent
from common.helpdesk import ALL_TOOLS, SYSTEM_PROMPT

saver = InMemorySaver()
graph = build_tool_agent(get_llm(), ALL_TOOLS, SYSTEM_PROMPT, checkpointer=saver, name="notebook-memory")
THREAD = "alice-notebook-1"
config = langfuse_config(thread_id=THREAD, recursion_limit=12)

def turn(text):
    with trace_attributes(session_id=THREAD, user_id="alice", tags=["notebook-03"]):
        result = graph.invoke({"messages": [{"role": "user", "content": text}]}, config=config)
    for i, m in enumerate(result["messages"]):
        print(f"[{i:>2}]", describe(m))
    print(f"\\n{len(result['messages'])} messages in thread '{THREAD}'")'''),
("md", "## 2. Turn 1"),
("code", 'turn("Hi, I\'m alice. My VPN keeps dropping.")'),
("md", "## 3. Turn 2: 'it' only makes sense with memory"),
("code", 'turn("Is there an outage for it?")'),
("md", "## 4. Turn 3: 'I' = alice, from message [0]"),
("code", 'turn("OK. And what laptop do I have on record?")'),
("md", "## 5. A different thread starts blank"),
("code", '''bob = graph.invoke({"messages": [{"role": "user", "content": "What laptop do I have?"}]},
                   config=langfuse_config(thread_id="bob-notebook-1"))
print(bob["messages"][-1].text)'''),
("md", "## 6. The checkpoints behind alice's thread\nOne snapshot per graph step; `next` is where a resume would continue."),
("code", '''history = list(graph.get_state_history({"configurable": {"thread_id": THREAD}}))
for cp in reversed(history):
    msgs = cp.values.get("messages", [])
    print(f"step {cp.metadata.get('step'):>3} | next: {', '.join(cp.next) or 'END':<10} | {len(msgs):>2} messages")
print("\\nthreads in the saver:", list(saver.storage.keys()))'''),
("code", "flush()"),
],

"04-multi-agent.ipynb": [
("md", """# Block 04 – The router, on its own and in the graph

**You'll see:** the form the router fills in, its decisions and reasons, and the whole graph step by step."""),
("code", SETUP),
("md", "## 1. The router's form, as Claude sees it"),
("code", '''import json
from common.loader import load_block
b04 = load_block("04-multi-agent")
print(json.dumps(b04.Route.model_json_schema(), indent=2))'''),
("md", "## 2. The router alone\n`build_router` returns a function; call it with a state."),
("code", '''router = b04.build_router(get_cheap_llm())
print(router)
print(router({"messages": [("user", "What is happening with INC-1001?")]}))'''),
("md", "## 3. Decisions and reasons for several questions\nWatch the two-part question and the ambiguous one."),
("code", '''router_llm = get_cheap_llm().with_structured_output(b04.Route)
questions = ["How do I set up email on my phone?",
             "What is happening with INC-1001?",
             "Is the VPN down and what is the status of INC-1001?",
             "My laptop is slow",
             "Thanks!"]
for q in questions:
    r = router_llm.invoke([("system", b04.ROUTER_PROMPT), ("user", q)])
    print(f"{r.agent:<13} | {q:<52} | {r.reason}")'''),
("md", "## 4. The whole graph, step by step\nThe router writes `route`; the conditional edge follows it; the specialist adds messages."),
("code", '''graph = b04.build_graph(llm=get_llm(), router_llm=get_cheap_llm())
with trace_attributes(tags=["notebook-04"]):
    for chunk in graph.stream({"messages": [("user", "What is happening with INC-1001?")]},
                              config=langfuse_config(recursion_limit=20), stream_mode="updates"):
        for node, update in chunk.items():
            shown = {k: (v if k == "route" else f"{len(v)} new message(s)") for k, v in update.items()}
            print(f"after {node}: {shown}")'''),
("code", "flush()"),
],

"05-human-in-the-loop.ipynb": [
("md", """# Block 05 – Pause, look, resume

**You'll see:** the run pause at `interrupt()`, the payload a human would review, resuming with approve or deny, and the node running twice.

The pause and the resume are in **separate cells** on purpose: in real life they may be hours apart."""),
("code", SETUP),
("md", "## 1. Build the account agent with a checkpointer"),
("code", '''from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from common.loader import load_block
b05 = load_block("05-human-in-the-loop")
graph = b05.build_graph(get_llm(), checkpointer=InMemorySaver())
config = langfuse_config(thread_id="bob-reset-notebook", recursion_limit=15)'''),
("md", "## 2. Ask for a reset → the run pauses"),
("code", '''with trace_attributes(session_id="bob-reset-notebook", tags=["notebook-05"]):
    result = graph.invoke({"messages": [("user", "Hi, this is bob. I'm locked out, please reset my password.")]},
                          config=config)
print("paused?", "__interrupt__" in result)
if "__interrupt__" in result:
    print("payload for the human:", result["__interrupt__"][0].value)
print("graph will continue at:", graph.get_state(config).next)'''),
("md", "## 3. The human approves → resume with the same thread_id\nChange `True` to `False` (and run cell 2 again first) to see a denial."),
("code", '''with trace_attributes(session_id="bob-reset-notebook", tags=["notebook-05"]):
    result = graph.invoke(Command(resume={"approved": True, "note": ""}), config=config)
print("paused?", "__interrupt__" in result)
print(result["messages"][-1].text)'''),
("md", "## 4. Proof that the node re-runs from the top on resume\nA counter in a test tool goes up twice: once before the pause, once on resume."),
("code", '''from langchain_core.tools import tool
from langgraph.types import interrupt
from common.graphs import build_tool_agent

runs = []

@tool
def risky_action(target: str) -> str:
    """A sensitive action that needs human approval. Use it when asked to run the risky action."""
    runs.append("code before interrupt ran")      # imagine an email or API call here
    answer = interrupt({"question": f"Run risky action on {target}?"})
    return "done" if answer else "denied"

g = build_tool_agent(get_llm(), [risky_action], "Use risky_action when the user asks.", checkpointer=InMemorySaver())
cfg = {"configurable": {"thread_id": "rerun-demo"}}
g.invoke({"messages": [("user", "Please run the risky action on server-1")]}, cfg)
print("after pause: ", len(runs), "run(s)")
g.invoke(Command(resume=True), cfg)
print("after resume:", len(runs), "run(s)  <- the node ran again from the top")'''),
("code", "flush()"),
],
}

if __name__ == "__main__":
    for name, cells in NOTEBOOKS.items():
        nbf.write(nb(cells), HERE / name)
        print("wrote", name)
