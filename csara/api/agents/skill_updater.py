import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.claude import call_claude
from api import claude as _claude_mod


def _dbg(msg: str) -> None:
    if _claude_mod._debug:
        print(f"  [DEBUG skill_updater] {msg}", file=sys.stderr)


SKILL_UPDATE_PROMPT = """You are a skill file updater for a personal AI assistant's memory system.
You will receive:
1. The CURRENT content of a skill file (markdown)
2. The FILE TYPE: "core" (rules/conventions), "failures" (past bugs and fixes), or "edge_cases" (gotchas/constraints)
3. NEW information to potentially merge in

Your job:
- If the new information is ALREADY covered by the existing content, return exactly: NO_CHANGE
- If the new information adds value, return the FULL updated file content with the new info merged in

Rules for merging:
- NEVER remove or lose existing content unless it directly contradicts the new info
- Deduplicate: if the new info overlaps with an existing bullet, merge them into one clearer bullet
- For "core" files: use markdown bullet list format (- Rule here)
- For "failures" files: use dated section format (## YYYY-MM-DD followed by description)
- For "edge_cases" files: use markdown bullet list format (- Edge case here)
- Keep the existing title header (# Title) at the top
- Be concise — each bullet or entry should be 1-2 sentences max
- Return ONLY the file content or NO_CHANGE. No explanation. No code fences."""


def update_skill_file(existing_content: str, file_type: str,
                      new_content: str, atom_type: str) -> str | None:
    """Ask Claude to intelligently merge new info into a skill file.

    Returns the updated file content, or None if no change needed.
    Returns empty string on API failure (caller should fall back to append).
    """
    user_message = f"""CURRENT FILE CONTENT:
{existing_content}

FILE TYPE: {file_type}
ATOM TYPE: {atom_type}

NEW INFORMATION TO MERGE:
{new_content}

Return the updated file or NO_CHANGE."""

    _dbg(f"file_type={file_type}, atom_type={atom_type}")
    _dbg(f"existing content length: {len(existing_content)} chars")
    _dbg(f"new content: {new_content!r}")
    _dbg("calling Claude for skill update decision...")

    response = call_claude(SKILL_UPDATE_PROMPT, user_message, max_tokens=1000)

    _dbg(f"raw response:\n{response[:300]}{'...' if len(response) > 300 else ''}")

    if not response:
        _dbg("API failure — empty response")
        return ""

    if response.strip() == "NO_CHANGE":
        _dbg("decision: NO_CHANGE")
        return None

    # Claude returned updated file content
    _dbg(f"decision: UPDATE ({len(response.strip())} chars)")
    return response.strip()
