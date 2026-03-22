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

SKILL_RERANK_SYSTEM_PROMPT = """You are a strict skill relevance filter. Given a search query and candidate skills with summaries, return ONLY the names of skills that DIRECTLY apply to the query.

Rules:
- Only keep skills whose domain clearly matches the query intent
- A skill that shares a generic word (e.g. "deployment") but covers a different project must be removed
- Return ONLY a JSON array of skill names, nothing else
- Example: ["python", "mostbased-core"]
- If nothing is relevant, return: []
- Aim for 1-3 results."""


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

# Words too generic to contribute to skill/summary matching
SKILL_SUMMARY_STOP_WORDS = SKILL_STOP_WORDS | {
    "error", "errors", "codes", "code", "rules", "covers", "operating",
    "patterns", "conventions", "system", "uses", "using", "based",
    "project", "personal", "specific", "knowledge", "domain",
}

# Keywords too generic to justify matching a project-specific skill on their own
GENERIC_PROJECT_KEYWORDS = {
    "project", "frontend", "backend", "architecture",
    "deployment", "deploy", "tailwind", "css", "design", "build",
    "production", "environment", "config", "setup",
    "component", "components", "state", "store", "styling", "layout",
    "routing", "api", "server", "client", "database", "migration",
}


def _normalize_kw(text: str) -> str:
    """Normalize a keyword for comparison: lowercase, remove non-alphanum except hyphens."""
    return re.sub(r"[^\w\-]", "", text.lower())


def _is_project_skill(skill_name: str) -> bool:
    """Detect project-specific skills (vs generic technology skills)."""
    tech_skills = {"python", "javascript", "typescript", "rust", "go", "java", "frontend", "backend"}
    return skill_name not in tech_skills


def _extract_project_name(skill_name: str) -> str:
    """Extract project base name from skill name (e.g., 'mostbased-core' -> 'mostbased')."""
    return skill_name.split("-")[0]


def get_relevant_skills(query: str, index_content: dict) -> list:
    skills = index_content.get("skills", {})
    if not skills:
        return []

    query_lower = query.lower()
    query_clean = re.sub(r"[^\w\s]", "", query_lower)
    query_words = set(query_clean.split())
    # Also keep hyphenated forms for matching
    query_hyphenated = set(re.sub(r"[^\w\s\-]", "", query_lower).split())

    skill_scores = {}
    for skill_name, skill_info in skills.items():
        keywords = skill_info.get("trigger_keywords", [])
        score = 0
        exact_matches = 0
        has_specific_match = False  # non-generic keyword matched

        for kw in keywords:
            kw_lower = kw.lower()
            kw_normalized = _normalize_kw(kw)

            # Multi-word keyword: check if it appears in the full query string
            if " " in kw_lower:
                if kw_lower in query_lower:
                    score += 2
                    exact_matches += 1
                    if kw_lower not in GENERIC_PROJECT_KEYWORDS:
                        has_specific_match = True
                continue

            # Exact match (try both normalized and original)
            if kw_lower in query_words or kw_normalized in query_words or kw_lower in query_hyphenated:
                score += 2
                exact_matches += 1
                if kw_lower not in GENERIC_PROJECT_KEYWORDS:
                    has_specific_match = True
                continue

            # Also try normalized query words against normalized keyword
            for qw in query_words:
                if kw_normalized == qw or _normalize_kw(kw) == _normalize_kw(qw):
                    score += 2
                    exact_matches += 1
                    if kw_lower not in GENERIC_PROJECT_KEYWORDS:
                        has_specific_match = True
                    break
            else:
                # Substring match (min 5 chars): query word contains keyword or vice versa
                # Only match if the substring is a significant portion of the host word
                for qw in query_words:
                    if len(kw_normalized) >= 5 and kw_normalized in qw and len(kw_normalized) / len(qw) > 0.5:
                        score += 1
                        break
                    if len(qw) >= 5 and qw in kw_normalized and len(qw) / len(kw_normalized) > 0.5:
                        score += 1
                        break

        # Summary word matching (+0.5 per overlapping word, using stricter stop words)
        summary = skill_info.get("summary", "").lower()
        summary_words = set(re.sub(r"[^\w\s]", "", summary).split()) - SKILL_SUMMARY_STOP_WORDS
        overlap = query_words & summary_words
        score += len(overlap) * 0.5

        # Project-specific skills need stronger signals to match
        if _is_project_skill(skill_name):
            project_name = _extract_project_name(skill_name)
            has_project_name = project_name in query_words or project_name in query_lower
            if has_project_name:
                # Project name in query: any keyword match is enough
                if score >= 2:
                    skill_scores[skill_name] = score
            elif has_specific_match:
                # Non-generic keyword matched: likely relevant even without project name
                if score >= 2:
                    skill_scores[skill_name] = score
            elif exact_matches >= 3 and score >= 6:
                # Only generic keywords matched: need strong evidence from many matches
                skill_scores[skill_name] = score
        else:
            # Technology skills: single keyword match is meaningful
            if score >= 2:
                skill_scores[skill_name] = score

    _dbg(f"skill_scores: {skill_scores}")

    if skill_scores:
        sorted_skills = sorted(skill_scores.keys(), key=lambda x: skill_scores[x], reverse=True)

        # Rerank with Claude when too many skills matched (>3)
        if len(sorted_skills) > 3:
            _dbg(f"too many skill matches ({len(sorted_skills)}), calling Claude reranker")
            skill_summaries = "\n".join(
                f"- {name}: {skills[name].get('summary', '')}"
                for name in sorted_skills
            )
            try:
                response = call_claude(
                    SKILL_RERANK_SYSTEM_PROMPT,
                    f"Query: {query}\n\nCandidate skills:\n{skill_summaries}",
                    max_tokens=150
                )
                reranked = json.loads(response.strip())
                if isinstance(reranked, list):
                    valid = [s for s in reranked if s in skill_scores]
                    _dbg(f"skill rerank result: {valid}")
                    if valid:
                        return valid
            except Exception as e:
                _dbg(f"skill rerank failed: {e}, using score sort")

        return sorted_skills

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
