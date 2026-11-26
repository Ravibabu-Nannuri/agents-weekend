"""Block 10 - Talk to the running API like a real client would.

Start the server first (make serve), then in another terminal:
  .venv/bin/python 10-serving/client_demo.py
"""

import json
import sys

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
THREAD = "alice-api-1"


def main():
    with httpx.Client(base_url=BASE, timeout=120) as c:
        print("GET /health ->", c.get("/health").json())

        for text in ["Hi, I'm alice. My VPN keeps dropping.", "Is there an outage for it?"]:
            r = c.post("/chat", json={"thread_id": THREAD, "user_id": "alice", "message": text}).json()
            print(f"\nPOST /chat  alice: {text}")
            print(f"  tools used: {r['tools_used']}  | messages in thread: {r['messages_in_thread']}")
            print(f"  agent: {r['answer'][:200]}")

        print("\nPOST /chat/stream  alice: OK. And what laptop do I have on record?\n  agent: ", end="")
        body = {"thread_id": THREAD, "user_id": "alice", "message": "OK. And what laptop do I have on record?"}
        with c.stream("POST", "/chat/stream", json=body) as resp:
            event = None
            for line in resp.iter_lines():
                if line.startswith("event: "):
                    event = line[7:]
                elif line.startswith("data: "):
                    data = json.loads(line[6:])
                    if event == "token":
                        print(data["text"], end="", flush=True)      # words appear as they're generated
                    elif event == "tool_call":
                        print(f"\n  [calling {data['tool']}...]\n  agent: ", end="", flush=True)
        print()

        thread = c.get(f"/threads/{THREAD}").json()
        print(f"\nGET /threads/{THREAD} -> {len(thread['messages'])} stored messages")
        print("\nNow stop the server (Ctrl+C), start it again, and run:")
        print(f"  curl {BASE}/threads/{THREAD}")
        print("The conversation is still there: the checkpointer is durable.")


if __name__ == "__main__":
    main()
