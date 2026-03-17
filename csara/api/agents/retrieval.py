import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api import claude as _claude_mod


def _dbg(msg: str) -> None:
    if _claude_mod._debug:
        print(f"  [DEBUG retrieval] {msg}", file=sys.stderr)


RETRIEVAL_SYSTEM_PROMPT = """You are a memory retrieval agent for a personal AI assistant.
Your job is to select which memory atoms are actually relevant to the user's query.
These candidates have already been pre-filtered by keyword intersection — they are the closest keyword matches.
Your job is final relevance ranking, not broad filtering.
Return ONLY a JSON array of atom IDs. No explanation. No markdown. Just the array.
Example: ["mem_001", "mem_047"]
If nothing is truly relevant, return: []
Return at most 8 atoms. Fewer is better. Only return atoms that genuinely help with the query."""


def get_relevant_atoms(query: str, index_content: dict, keyword_hits: dict) -> list:
    # Pure code retrieval — sort by keyword score descending, cap at 8
    sorted_ids = sorted(keyword_hits.keys(), key=lambda x: keyword_hits[x], reverse=True)
    result = sorted_ids[:8]
    _dbg(f"candidates: {len(sorted_ids)}, returning top {len(result)} by score")
    _dbg(f"  returning: {result}")
    return result


def get_relevant_skills(query: str, index_content: dict) -> list:
    skills = index_content.get("skills", {})
    query_lower = query.lower()
    query_words = set(re.sub(r"[^\w\s]", "", query_lower).split())

    skill_scores = {}
    for skill_name, skill_info in skills.items():
        keywords = skill_info.get("trigger_keywords", [])
        count = sum(1 for kw in keywords if kw.lower() in query_words)
        if count > 0:
            skill_scores[skill_name] = count

    return sorted(skill_scores.keys(), key=lambda x: skill_scores[x], reverse=True)
