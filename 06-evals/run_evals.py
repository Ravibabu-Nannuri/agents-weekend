"""Block 06 - Evaluate the block-04 helpdesk on a fixed dataset.

Three evaluators:
  route_correct   - deterministic: did the router pick the expected specialist?
  tool_correct    - deterministic: was the expected tool called?
  mentions        - deterministic: does the answer contain the must-mention facts?
  helpfulness     - LLM-as-judge (cheap model) scores 1-5

Run:
  python 06-evals/run_evals.py                      # local data, results + traces in Langfuse
  python 06-evals/run_evals.py --upload             # also create a Langfuse Dataset, run on it
  python 06-evals/run_evals.py --run-name v2-prompt # name the run, compare runs in the UI
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import BaseModel, Field

from common.config import get_cheap_llm, get_llm
from common.loader import load_block
from common.tracing import langfuse_config, tracing_enabled

DATASET_NAME = "helpdesk-routing-v1"
DATA = json.loads((Path(__file__).parent / "dataset.json").read_text())

helpdesk = load_block("04-multi-agent")
GRAPH = None


def get_graph():
    global GRAPH
    if GRAPH is None:
        GRAPH = helpdesk.build_graph(llm=get_llm(), router_llm=get_cheap_llm())
    return GRAPH


# ------------------------------------------------------------------ task
def task(*, item, **kwargs):
    """Runs the agent on one dataset item. Returns what the evaluators need."""
    question = item["input"] if isinstance(item, dict) else item.input
    result = get_graph().invoke({"messages": [{"role": "user", "content": question}]},
                                config=langfuse_config(recursion_limit=20))
    tools = [tc["name"] for m in result["messages"] for tc in (getattr(m, "tool_calls", None) or [])]
    return {"route": result["route"], "tools": tools, "answer": result["messages"][-1].content}


# ------------------------------------------------------------ evaluators
def _ev(name, value, comment=""):
    from langfuse import Evaluation
    return Evaluation(name=name, value=value, comment=comment)


def route_correct(*, input, output, expected_output, **kwargs):
    ok = output["route"] == expected_output["route"]
    return _ev("route_correct", 1.0 if ok else 0.0, f"expected {expected_output['route']}, got {output['route']}")


def tool_correct(*, input, output, expected_output, **kwargs):
    want = expected_output.get("tool")
    if want is None:
        return _ev("tool_correct", 1.0, "no specific tool required")
    ok = want in output["tools"]
    return _ev("tool_correct", 1.0 if ok else 0.0, f"expected {want}, called {output['tools']}")


def mentions(*, input, output, expected_output, **kwargs):
    must = expected_output.get("must_mention", [])
    if not must:
        return _ev("mentions", 1.0, "nothing required")
    found = [m for m in must if m.lower() in output["answer"].lower()]
    return _ev("mentions", len(found) / len(must), f"found {found} of {must}")


class Judgement(BaseModel):
    score: int = Field(ge=1, le=5, description="1 = useless or wrong, 5 = correct, clear, actionable")
    reason: str


JUDGE_PROMPT = """You are grading an IT helpdesk agent.
User question: {q}
Agent answer: {a}
Score 1-5 for helpfulness and correctness. Off-topic questions should be politely declined - that deserves a 5."""


def helpfulness(*, input, output, expected_output, **kwargs):
    judge = get_cheap_llm().with_structured_output(Judgement)
    j: Judgement = judge.invoke(JUDGE_PROMPT.format(q=input, a=output["answer"]))
    return _ev("helpfulness", float(j.score), j.reason)


def average(name):
    def run_ev(*, item_results, **kwargs):
        vals = [e.value for r in item_results for e in r.evaluations if e.name == name]
        return _ev(f"avg_{name}", round(sum(vals) / len(vals), 3) if vals else 0.0)
    return run_ev


EVALUATORS = [route_correct, tool_correct, mentions, helpfulness]
RUN_EVALUATORS = [average(e.__name__) for e in EVALUATORS]


def upload_dataset(lf):
    lf.create_dataset(name=DATASET_NAME, description="IT helpdesk routing + answer quality")
    for i, row in enumerate(DATA):
        # fixed ids -> re-running --upload updates items instead of duplicating them
        lf.create_dataset_item(dataset_name=DATASET_NAME, id=f"{DATASET_NAME}-{i:03d}",
                               input=row["input"], expected_output=row["expected_output"])
    print(f"Uploaded {len(DATA)} items to Langfuse dataset '{DATASET_NAME}'")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--upload", action="store_true", help="create/update the Langfuse dataset and run on it")
    p.add_argument("--run-name", default="baseline")
    args = p.parse_args()

    if not tracing_enabled():
        sys.exit("Langfuse keys missing in .env - evals report their scores to Langfuse.")

    from langfuse import get_client
    lf = get_client()

    if args.upload:
        upload_dataset(lf)
        data = lf.get_dataset(DATASET_NAME).items
    else:
        data = DATA

    result = lf.run_experiment(
        name="helpdesk-eval", run_name=args.run_name,
        description="Block 06 evals for the block-04 supervisor",
        data=data, task=task, evaluators=EVALUATORS, run_evaluators=RUN_EVALUATORS,
        max_concurrency=4,  # be kind to rate limits
    )
    print(result.format())
    lf.flush()


if __name__ == "__main__":
    main()
