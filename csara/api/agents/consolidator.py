import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.claude import call_claude
from api import claude as _claude_mod


def _dbg(msg: str) -> None:
    if _claude_mod._debug:
        print(f"  [DEBUG consolidator] {msg}", file=sys.stderr)


SYSTEM_PROMPT = """You are a memory consolidation agent for a personal AI assistant.
Your job is to extract ONE piece of information worth storing permanently from a completed task.

Store ONLY if you find one of these:
1. A user preference or way of doing things (type: preference)
2. A bug/error and the fix that worked (type: fix)
3. A reusable pattern discovered (type: pattern)
4. A hard constraint or limitation found (type: constraint)
5. An explicit user correction (type: correction)

If none of these are present, return: null

If you find something, return a JSON object with exactly these 2 fields:
{
  "type": "preference",
  "content": "summary preserving specific details"
}

Rules:
- type must be one of: preference, fix, pattern, constraint, correction
- content must be 1-3 sentences max
- CRITICAL: preserve specific commands, tool names, code snippets, file paths, and function names in content. Do NOT abstract them into vague guidelines. For example, write "Use `wc -l` in bash or `Get-Content file | Measure-Object -Line` in PowerShell to count lines" NOT "User follows coding guidelines about file sizes."
- Return ONLY the JSON object or the word null. No explanation. No markdown."""


def consolidate(task_input: str, task_output: str) -> dict | None:
    user_message = f"""Task input: {task_input}

Task output: {task_output}

Extract memory or return null."""

    _dbg(f"task_input: {task_input!r}")
    _dbg(f"task_output: {task_output!r}")
    _dbg("calling Claude for consolidation decision...")

    response = call_claude(SYSTEM_PROMPT, user_message, max_tokens=200)

    _dbg(f"raw AI response:\n{response}")

    if not response or response.strip().lower() == "null":
        _dbg("AI decision: nothing worth storing")
        return None

    try:
        result = json.loads(response.strip())
        if isinstance(result, dict) and "type" in result and "content" in result:
            # Claude only decides type + content — keywords auto-extracted by code
            atom_dict = {
                "type": result["type"],
                "content": result["content"],
                "content_path": None,
                "tags": [],
                "strength": 0.9,
                "source_task": task_input[:100],
                "edges": {
                    "supports": [],
                    "contradicts": [],
                    "learned_from": "",
                    "belongs_to": [],
                    "occurred_in": [],
                    "fixed_by": [],
                    "generalizes": []
                }
            }
            _dbg(f"AI decision: STORE as type={atom_dict['type']!r}")
            _dbg(f"  content: {atom_dict['content']!r}")
            return atom_dict
    except json.JSONDecodeError as e:
        _dbg(f"JSON parse failed: {e}")
        _dbg(f"raw text was: {response!r}")

    _dbg("AI decision: response unusable, returning None")
    return None


JUDGE_PROMPT = """You are a memory deduplication judge.
You will see an EXISTING stored memory and NEW information about the same topic.
Decide which version is more useful to keep.

Rules:
- If the new info adds nothing over the existing memory, return: "keep"
- If the new info is richer, more specific, or corrects the old, return a JSON object with exactly these 2 fields:
{
  "type": "preference",
  "content": "one or two sentence summary combining the best of both"
}
- type must be one of: preference, fix, pattern, constraint, correction
- content must be 1-3 sentences max
- CRITICAL: preserve specific commands, tool names, code snippets, and function names
- Return ONLY the JSON object or the word "keep". No explanation. No markdown."""


def judge_duplicate(task_input: str, task_output: str,
                    old_content: str, old_tags: list) -> dict | None:
    """Ask Claude whether new info should replace an existing atom.
    Returns atom dict if replace, None if keep old."""
    user_message = f"""EXISTING memory:
Content: {old_content}

NEW information:
Input: {task_input}
Output: {task_output}

Should we keep the existing memory or replace with the new info?"""

    _dbg(f"judging duplicate...")
    _dbg(f"  old content: {old_content!r}")
    _dbg(f"  new input: {task_input!r}")
    _dbg(f"  new output: {task_output!r}")

    response = call_claude(JUDGE_PROMPT, user_message, max_tokens=200)
    _dbg(f"judge raw response:\n{response}")

    if not response or response.strip().lower() == "keep":
        _dbg("judge decision: KEEP old")
        return None

    try:
        result = json.loads(response.strip())
        if isinstance(result, dict) and "type" in result and "content" in result:
            atom_dict = {
                "type": result["type"],
                "content": result["content"],
                "content_path": None,
                "tags": [],
                "strength": 0.9,
                "source_task": task_input[:100],
                "edges": {
                    "supports": [],
                    "contradicts": [],
                    "learned_from": "",
                    "belongs_to": [],
                    "occurred_in": [],
                    "fixed_by": [],
                    "generalizes": []
                }
            }
            _dbg(f"judge decision: REPLACE with type={atom_dict['type']!r}")
            _dbg(f"  content: {atom_dict['content']!r}")
            return atom_dict
    except json.JSONDecodeError as e:
        _dbg(f"judge JSON parse failed: {e}")

    _dbg("judge decision: response unusable, keeping old")
    return None
