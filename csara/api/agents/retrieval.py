import sys
import os
import re
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api import claude as _claude_mod
from api.claude import call_claude

CSARA_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _dbg(msg: str) -> None:
    if _claude_mod._debug:
        print(f"  [DEBUG retrieval] {msg}", file=sys.stderr)


RERANK_SYSTEM_PROMPT = """You are a strict memory relevance filter. Given a search query and memory candidates, return ONLY the IDs of memories that DIRECTLY help answer the query.

Rules:
- Be aggressive: a memory mentioning "lines" or "files" incidentally is NOT relevant to a query about "counting lines"
- Only keep memories whose PRIMARY topic matches the query intent
- A memory about a completely different subject that happens to share a keyword must be removed
- Return ONLY a JSON array of atom IDs, nothing else
- Example: ["mem_003", "mem_024"]
- If nothing is relevant, return: []
- Aim for 2-4 results. More than 5 means you aren't filtering enough."""


def get_relevant_atoms(query: str, index_content: dict, keyword_hits: dict) -> list:
    sorted_ids = sorted(keyword_hits.keys(), key=lambda x: keyword_hits[x], reverse=True)

    # For small result sets, skip Claude — just return top 8 by score
    if len(sorted_ids) <= 5:
        result = sorted_ids[:8]
        _dbg(f"candidates: {len(sorted_ids)} (<=5, skipping rerank), returning: {result}")
        return result

    # For larger sets, use Claude to filter noise
    _dbg(f"candidates: {len(sorted_ids)} (>5, calling Claude reranker)")
    top_candidates = sorted_ids[:15]  # send at most 15 to Claude

    # Load atom content for each candidate
    candidate_summaries = []
    for aid in top_candidates:
        atom_path = os.path.join(CSARA_DIR, "memory", "atoms", f"{aid}.json")
        if not os.path.exists(atom_path):
            continue
        with open(atom_path, "r", encoding="utf-8") as f:
            atom = json.load(f)
        content = atom.get("content", "")
        source = atom.get("source_task", "")
        summary = f"{source} | {content}" if source else content
        candidate_summaries.append(f"[{aid}] {summary[:300]}")

    if not candidate_summaries:
        return sorted_ids[:8]

    user_msg = f"Query: {query}\n\nCandidates:\n" + "\n".join(candidate_summaries)
    _dbg(f"rerank user_msg length: {len(user_msg)} chars")

    try:
        response = call_claude(RERANK_SYSTEM_PROMPT, user_msg, max_tokens=200)
        _dbg(f"rerank response: {response}")
        reranked = json.loads(response.strip())
        if isinstance(reranked, list) and all(isinstance(x, str) for x in reranked):
            # Validate all returned IDs were in our candidates
            valid = [aid for aid in reranked if aid in keyword_hits]
            _dbg(f"reranked result: {valid}")
            return valid  # trust Claude's judgment, even if empty
    except Exception as e:
        _dbg(f"rerank failed: {e}, falling back to score sort")

    return sorted_ids[:8]


SKILL_STOP_WORDS = {
    "and", "the", "a", "an", "for", "of", "in", "to", "is", "with", "or",
    "on", "by", "at", "as", "from", "it", "be", "was", "are", "that", "this",
    "its", "not", "but", "so", "if", "no", "all", "any", "has", "have", "had",
}


def get_relevant_skills(query: str, index_content: dict) -> list:
    skills = index_content.get("skills", {})
    if not skills:
        return []

    query_lower = query.lower()
    query_clean = re.sub(r"[^\w\s]", "", query_lower)
    query_words = set(query_clean.split())

    skill_scores = {}
    for skill_name, skill_info in skills.items():
        keywords = skill_info.get("trigger_keywords", [])
        score = 0

        for kw in keywords:
            kw_lower = kw.lower()

            # Multi-word keyword: check if it appears in the full query string
            if " " in kw_lower:
                if kw_lower in query_lower:
                    score += 2
                continue

            # Exact match
            if kw_lower in query_words:
                score += 2
                continue

            # Substring match (min 4 chars): query word contains keyword or vice versa
            for qw in query_words:
                if len(kw_lower) >= 4 and kw_lower in qw:
                    score += 1
                    break
                if len(qw) >= 4 and qw in kw_lower:
                    score += 1
                    break

        # Summary word matching (+0.5 per overlapping word)
        summary = skill_info.get("summary", "").lower()
        summary_words = set(re.sub(r"[^\w\s]", "", summary).split()) - SKILL_STOP_WORDS
        overlap = query_words & summary_words
        score += len(overlap) * 0.5

        if score > 0:
            skill_scores[skill_name] = score

    _dbg(f"skill_scores: {skill_scores}")

    if skill_scores:
        return sorted(skill_scores.keys(), key=lambda x: skill_scores[x], reverse=True)

    # Claude fallback: only when keyword matching found nothing
    substantive_words = [w for w in query_words if len(w) > 2]
    if len(substantive_words) < 2:
        return []

    _dbg("no skills matched via keywords, trying Claude fallback")
    skill_list = "\n".join(
        f"- {name}: {info.get('summary', '')}"
        for name, info in skills.items()
    )

    try:
        response = call_claude(
            "You select relevant skills for a task. Return ONLY a JSON array of skill names. Return [] if none apply. Be selective.",
            f"Skills:\n{skill_list}\n\nQuery: {query}",
            max_tokens=100
        )
        result = json.loads(response.strip())
        if isinstance(result, list):
            valid = [s for s in result if s in skills]
            _dbg(f"Claude fallback returned: {valid}")
            return valid
    except Exception as e:
        _dbg(f"Claude skill fallback failed: {e}")

    return []
