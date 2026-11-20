# Block 06 – Evals: measuring agent quality (50 min)

**Goal:** stop judging the agent by "it looked fine when I tried it". Score it on a fixed dataset, every change.

## Steps
1. Look at `dataset.json` – 16 questions with the **expected route, expected tool, and facts the answer must mention**.
2. Run a baseline: `python 06-evals/run_evals.py --run-name baseline`
3. Make one change in `04-multi-agent/solution.py` (e.g. vague `Route` descriptions, or a different model).
4. Run again: `python 06-evals/run_evals.py --run-name vague-router`
5. With `--upload`, the dataset lives in Langfuse and runs appear side by side under **Datasets**.

## The four evaluators
| Evaluator | Type | Catches |
|---|---|---|
| `route_correct` | deterministic | router sends the question to the wrong specialist |
| `tool_correct` | deterministic | specialist uses the wrong tool (or none) |
| `mentions` | deterministic | answer misses key facts (ticket status, outage) |
| `helpfulness` | **LLM-as-judge** | vague, unhelpful or wrong answers |

Rule of thumb: **use deterministic checks wherever you can**, and LLM judges only for what code can't check.
They're cheaper, faster and don't drift.

## What to look at in Langfuse
- **Datasets → helpdesk-routing-v1 → Runs**: compare `baseline` vs your change, item by item.
- Click a failing item → jump straight to **its trace** and see *why* it failed.
- Each trace has **scores** attached. Filter traces by `route_correct = 0`.

## Exercise: the improvement loop
1. Find a failing item. 2. Read the trace. 3. Fix the prompt/tool description.
4. Re-run. Did it fix that item **without breaking others**? That's regression testing for prompts.

## Interview Q&A
**Q: How do you evaluate an agent?**
A: At three levels: (1) final answer quality – deterministic checks plus LLM-as-judge;
(2) trajectory – right route, right tools, right order, number of steps; (3) operational – cost,
latency, error rate. Offline on a curated dataset before release, online by scoring sampled production traces.

**Q: Where does the eval dataset come from?**
A: Start with 20–50 hand-written cases covering main intents and edge cases, then keep adding
real production failures (from traces and user feedback). Every bug becomes a test case.

**Q: What are the risks of LLM-as-judge?**
A: Bias (prefers long answers, its own style), inconsistency, and cost. Mitigate with clear
rubrics, structured scores, a different/stronger model than the one judged, and spot-checking the
judge against human labels.

**Q: How do you ship a prompt change safely?**
A: Run the eval suite, compare with the baseline, block the change if key metrics regress
(like CI tests), then roll out gradually and watch online scores and traces.
