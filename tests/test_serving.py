"""Offline tests for block 10's API: fake model, temporary SQLite checkpointer."""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
for k in ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "DATABASE_URL"]:
    os.environ[k] = ""

from fastapi.testclient import TestClient  # noqa: E402
from langchain_core.messages import AIMessage  # noqa: E402

from common.loader import load_block  # noqa: E402
from fake_llm import ScriptedLLM, tool_call  # noqa: E402

serving = load_block("10-serving", "app.py")


def client_with(llm, db_path):
    os.environ["SQLITE_PATH"] = str(db_path)
    return TestClient(serving.create_app(llm=llm))


def test_health_reports_sqlite(tmp_path):
    with client_with(ScriptedLLM(), tmp_path / "a.db") as c:
        body = c.get("/health").json()
        assert body["status"] == "ok" and body["checkpointer"].startswith("sqlite:")


def test_chat_uses_tools_and_remembers(tmp_path):
    llm = ScriptedLLM(replies=[tool_call("check_system_status", {"system": "vpn"}),
                               AIMessage(content="VPN is degraded."),
                               AIMessage(content="Yes, as I said, it's degraded.")])
    with client_with(llm, tmp_path / "b.db") as c:
        r1 = c.post("/chat", json={"thread_id": "t1", "message": "is vpn down?"}).json()
        assert r1["tools_used"] == ["check_system_status"] and r1["messages_in_thread"] == 4
        r2 = c.post("/chat", json={"thread_id": "t1", "message": "really?"}).json()
        assert r2["tools_used"] == [] and r2["messages_in_thread"] == 6
        thread = c.get("/threads/t1").json()
        assert [m["type"] for m in thread["messages"]] == ["human", "ai", "tool", "ai", "human", "ai"]


def test_memory_survives_restart(tmp_path):
    db = tmp_path / "c.db"
    with client_with(ScriptedLLM(replies=[AIMessage(content="Hi alice")]), db) as c:
        c.post("/chat", json={"thread_id": "alice", "message": "I'm alice"})
    # brand-new app instance, same database file = a server restart
    with client_with(ScriptedLLM(replies=[AIMessage(content="You're alice")]), db) as c:
        r = c.post("/chat", json={"thread_id": "alice", "message": "who am I?"}).json()
        assert r["messages_in_thread"] == 4


def test_stream_emits_events(tmp_path):
    llm = ScriptedLLM(replies=[tool_call("check_system_status", {"system": "vpn"}),
                               AIMessage(content="Degraded.")])
    with client_with(llm, tmp_path / "d.db") as c:
        with c.stream("POST", "/chat/stream", json={"thread_id": "s1", "message": "vpn?"}) as resp:
            events = [line[7:] for line in resp.iter_lines() if line.startswith("event: ")]
    assert "tool_result" in events and events[-1] == "done"


def test_unknown_thread_404_and_delete(tmp_path):
    with client_with(ScriptedLLM(replies=[AIMessage(content="hi")]), tmp_path / "e.db") as c:
        assert c.get("/threads/nope").status_code == 404
        c.post("/chat", json={"thread_id": "gone", "message": "hello"})
        assert c.get("/threads/gone").status_code == 200
        assert c.delete("/threads/gone").json()["deleted"] is True
        assert c.get("/threads/gone").status_code == 404


def test_validation_rejects_empty_message(tmp_path):
    with client_with(ScriptedLLM(), tmp_path / "f.db") as c:
        assert c.post("/chat", json={"thread_id": "x", "message": ""}).status_code == 422


def test_runaway_agent_returns_clean_error(tmp_path):
    looping = ScriptedLLM(replies=[tool_call("check_system_status", {"system": "vpn"}, f"c{i}") for i in range(40)])
    os.environ["MAX_STEPS"] = "4"
    try:
        mod = load_block("10-serving", "app.py")
        os.environ["SQLITE_PATH"] = str(tmp_path / "g.db")
        with TestClient(mod.create_app(llm=looping)) as c:
            r = c.post("/chat", json={"thread_id": "loop", "message": "vpn?"})
            assert r.status_code == 500 and "stopped after 4 steps" in r.json()["detail"]
    finally:
        os.environ.pop("MAX_STEPS")


def test_feedback_without_tracing_is_503_and_no_trace_id(tmp_path):
    with client_with(ScriptedLLM(replies=[AIMessage(content="hi")]), tmp_path / "h.db") as c:
        r = c.post("/chat", json={"thread_id": "f1", "message": "hello"}).json()
        assert r["trace_id"] is None
        assert c.post("/feedback", json={"trace_id": "abc", "thumbs_up": True}).status_code == 503
