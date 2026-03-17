import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.agents.consolidator import consolidate as _consolidate


def consolidate(task_input: str, task_output: str) -> dict | None:
    return _consolidate(task_input, task_output)
