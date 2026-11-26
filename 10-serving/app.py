"""Block 10 - Serve the helpdesk agent over HTTP, with durable memory.

  POST   /chat               one turn, full answer as JSON
  POST   /chat/stream        one turn, answer streamed as Server-Sent Events (tokens + tool events)
  GET    /threads/{id}       the stored conversation for a thread
  DELETE /threads/{id}       forget a conversation
  GET    /health             liveness + which checkpointer is in use

Checkpointer:
  DATABASE_URL=postgresql://...   -> Postgres (docker compose, production)
  otherwise                       -> SQLite file (SQLITE_PATH, default checkpoints.db)
Either way, conversations survive a restart.

Run locally:   make serve        (or: .venv/bin/uvicorn app:app --app-dir 10-serving --reload)
Run in Docker: cd 10-serving && docker compose up --build
"""

import json
import os
import sys
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import ToolMessage
from langgraph.errors import GraphRecursionError
from pydantic import BaseModel, Field

from common.config import DEFAULT_MODEL, get_llm
from common.graphs import build_tool_agent
from common.helpdesk import ALL_TOOLS, SYSTEM_PROMPT
from common.tracing import flush, langfuse_config, trace_attributes

MAX_STEPS = int(os.getenv("MAX_STEPS", "15"))  # recursion_limit: hard cap on loop steps per request


# ----------------------------------------------------------- request/response
class ChatRequest(BaseModel):
    thread_id: str = Field(min_length=1, max_length=128, description="Conversation id; same id = same memory")
    message: str = Field(min_length=1, max_length=4000)
    user_id: str = Field(default="anonymous", max_length=128)


class ChatResponse(BaseModel):
    thread_id: str
    answer: str
    tools_used: list[str]
    messages_in_thread: int


# ---------------------------------------------------------------- checkpointer
async def open_checkpointer(stack: AsyncExitStack):
    """Postgres if DATABASE_URL is set, else a SQLite file. Both are durable."""
    url = os.getenv("DATABASE_URL", "")
    if url.startswith("postgres"):
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        saver = await stack.enter_async_context(AsyncPostgresSaver.from_conn_string(url))
        await saver.setup()  # creates the checkpoint tables on first run
        return saver, "postgres"

    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    path = os.getenv("SQLITE_PATH", "checkpoints.db")
    saver = await stack.enter_async_context(AsyncSqliteSaver.from_conn_string(path))
    return saver, f"sqlite:{path}"


def describe(m) -> dict:
    return {
        "type": type(m).__name__.replace("Message", "").lower(),
        "text": m.text,
        "tool_calls": [tc["name"] for tc in getattr(m, "tool_calls", None) or []],
    }


# --------------------------------------------------------------------- the app
def create_app(llm=None) -> FastAPI:
    """Factory so tests can pass a fake model. Production uses the module-level `app`."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Runs once at startup: open the DB connection and build the graph ONCE,
        # not per request. Closed cleanly at shutdown.
        async with AsyncExitStack() as stack:
            saver, kind = await open_checkpointer(stack)
            app.state.graph = build_tool_agent(llm or get_llm(), ALL_TOOLS, SYSTEM_PROMPT,
                                               checkpointer=saver, name="helpdesk-api")
            app.state.checkpointer = saver
            app.state.checkpointer_kind = kind
            yield
        flush()  # send any pending traces before the process exits

    app = FastAPI(title="IT Helpdesk Agent", version="1.0", lifespan=lifespan)

    def config_for(req: ChatRequest) -> dict:
        return langfuse_config(thread_id=req.thread_id, recursion_limit=MAX_STEPS)

    @app.get("/health")
    async def health():
        return {"status": "ok", "checkpointer": app.state.checkpointer_kind, "model": DEFAULT_MODEL}

    @app.post("/chat", response_model=ChatResponse)
    async def chat(req: ChatRequest):
        graph = app.state.graph
        state = await graph.aget_state({"configurable": {"thread_id": req.thread_id}})
        before = len(state.values.get("messages", []))
        try:
            with trace_attributes(session_id=req.thread_id, user_id=req.user_id, tags=["block-10", "api"]):
                result = await graph.ainvoke({"messages": [{"role": "user", "content": req.message}]},
                                             config=config_for(req))
        except GraphRecursionError:
            raise HTTPException(status_code=500, detail=f"Agent stopped after {MAX_STEPS} steps without answering.")
        new = result["messages"][before:]
        tools = [tc["name"] for m in new for tc in (getattr(m, "tool_calls", None) or [])]
        return ChatResponse(thread_id=req.thread_id, answer=result["messages"][-1].text,
                            tools_used=tools, messages_in_thread=len(result["messages"]))

    @app.post("/chat/stream")
    async def chat_stream(req: ChatRequest):
        graph = app.state.graph

        def sse(event: str, data) -> str:
            return f"event: {event}\ndata: {json.dumps(data)}\n\n"

        async def events():
            try:
                with trace_attributes(session_id=req.thread_id, user_id=req.user_id, tags=["block-10", "stream"]):
                    # stream_mode="messages" yields (message chunk, metadata) as the model generates
                    async for chunk, meta in graph.astream({"messages": [{"role": "user", "content": req.message}]},
                                                           config=config_for(req), stream_mode="messages"):
                        node = meta.get("langgraph_node")
                        if isinstance(chunk, ToolMessage):
                            yield sse("tool_result", {"tool": chunk.name, "text": chunk.text[:300]})
                        elif node == "model":
                            for tc in getattr(chunk, "tool_call_chunks", None) or []:
                                if tc.get("name"):
                                    yield sse("tool_call", {"tool": tc["name"]})
                            if chunk.text:
                                yield sse("token", {"text": chunk.text})
                yield sse("done", {"thread_id": req.thread_id})
            except GraphRecursionError:
                yield sse("error", {"detail": f"Agent stopped after {MAX_STEPS} steps without answering."})

        return StreamingResponse(events(), media_type="text/event-stream")

    @app.get("/threads/{thread_id}")
    async def get_thread(thread_id: str):
        state = await app.state.graph.aget_state({"configurable": {"thread_id": thread_id}})
        messages = state.values.get("messages", [])
        if not messages:
            raise HTTPException(status_code=404, detail="No conversation with that thread_id.")
        return {"thread_id": thread_id, "messages": [describe(m) for m in messages]}

    @app.delete("/threads/{thread_id}")
    async def delete_thread(thread_id: str):
        await app.state.checkpointer.adelete_thread(thread_id)
        return {"thread_id": thread_id, "deleted": True}

    return app


app = create_app()
