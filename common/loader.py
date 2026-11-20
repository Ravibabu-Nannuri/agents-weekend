"""Block folders start with digits (01-first-agent), so they can't be imported normally.
This loads a block's solution.py as a module, e.g. load_block("04-multi-agent")."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_block(folder: str, file: str = "solution.py"):
    path = ROOT / folder / file
    spec = importlib.util.spec_from_file_location(f"block_{folder.replace('-', '_')}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
