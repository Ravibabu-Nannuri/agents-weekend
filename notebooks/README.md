# Walkthrough notebooks (blocks 01–05)

Run the blocks **one step per cell** and inspect the state between steps. The notebooks import the
repo's real code (`common/` and each block's `solution.py`); they don't duplicate it.

| Notebook | What you see |
|---|---|
| `01-first-agent.ipynb` | What `create_agent` builds, raw content blocks vs `.text`, token usage |
| `02-tools.ipynb` | A tool card, the loop streamed step by step, prebuilt vs custom with the outage rule |
| `03-memory.ipynb` | `messages` growing one turn per cell, a blank new thread, the checkpoints |
| `04-multi-agent.ipynb` | The `Route` schema, router decisions and reasons, the whole graph step by step |
| `05-human-in-the-loop.ipynb` | Pause in one cell, resume in the next, proof the node re-runs |

## How to open
1. In VS Code, open a notebook and pick the kernel **`.venv`** (top right).
2. Run cells top to bottom. Cell 1 (setup) must run first.
3. Traces appear in Langfuse with tags `notebook-01` … `notebook-05`.

## Tips
- Cells share memory. Re-running a turn cell adds another turn; use **Restart** to start clean.
- These call the real Claude API, so each run costs a little (well under a dollar for all five).
- To change a notebook, edit `build_notebooks.py` and re-run it, or just edit the notebook directly.
