import sys
import os
import argparse
import json
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ops.search import keyword_search
from ops.read import read_atoms
from api.agents.retrieval import get_relevant_atoms, get_relevant_skills

CSARA_DIR = os.path.dirname(os.path.abspath(__file__))

STOP_WORDS = {
    "the", "a", "an", "is", "it", "to", "of", "in", "for", "and", "or",
    "how", "what", "why", "i", "my", "we", "this", "that",
    "do", "does", "did", "was", "were", "be", "been", "being",
    "have", "has", "had", "not", "no", "but", "so", "if", "when",
    "where", "which", "who", "whom", "there", "here", "then",
    "can", "could", "would", "should", "will", "shall", "may", "might",
    "with", "from", "by", "on", "at", "as", "into", "about",
    "than", "too", "very", "just", "only", "also", "any", "all",
    "are", "am", "our", "your", "its", "their", "some", "set",
    "get", "got", "put", "use", "used", "using", "make", "need",
    "properly", "correctly", "handle", "want", "like", "way"
}

DEBUG_WORDS = {
    "debug", "error", "fix", "bug", "traceback", "exception",
    "broken", "wrong", "issue", "fail"
}


def _extract_keywords(query: str) -> list:
    words = re.sub(r"[^\w\s]", "", query.lower()).split()
    return [w for w in words if w and w not in STOP_WORDS]


def _load_json(rel_path: str) -> dict:
    full = os.path.join(CSARA_DIR, rel_path)
    if not os.path.exists(full):
        return {}
    with open(full, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_skill_file(rel_path: str) -> str:
    full = os.path.join(CSARA_DIR, rel_path)
    if not os.path.exists(full):
        return ""
    with open(full, "r", encoding="utf-8") as f:
        return f.read().strip()


def _dbg(msg: str, debug: bool) -> None:
    if debug:
        print(f"  [DEBUG search] {msg}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="CSara memory search")
    parser.add_argument("--q", required=True, help="Search query")
    parser.add_argument("--debug", action="store_true", help="Print debug trace")
    args = parser.parse_args()

    debug = args.debug
    if debug:
        from api.claude import set_debug
        set_debug(True)
        print("\n  [DEBUG] === search.py debug trace ===", file=sys.stderr)

    query = args.q
    keywords = _extract_keywords(query)
    _dbg(f"query: {query!r}", debug)
    _dbg(f"keywords: {keywords}", debug)

    if not keywords:
        _dbg("no keywords after filtering — aborting", debug)
        print("=== CSara Memory ===")
        print("No relevant memory or skills found for this query.")
        print("===================")
        return

    # Keyword search
    keyword_hits = keyword_search(keywords)
    _dbg(f"keyword_hits: {keyword_hits}", debug)

    # Load index
    index_content = _load_json("index.json")
    _dbg(f"index atoms count: {len(index_content.get('atoms', {}))}", debug)
    _dbg(f"index skills: {list(index_content.get('skills', {}).keys())}", debug)

    # Get relevant skills (no LLM)
    relevant_skills = get_relevant_skills(query, index_content)
    _dbg(f"relevant_skills: {relevant_skills}", debug)

    # Get relevant atoms (LLM-powered if we have hits)
    atom_ids = []
    if keyword_hits:
        _dbg("calling retrieval agent for final atom ranking...", debug)
        atom_ids = get_relevant_atoms(query, index_content, keyword_hits)
    _dbg(f"final atom_ids: {atom_ids}", debug)

    # Load skill content BEFORE atoms (needed for dedup)
    skill_sections = []
    query_lower = query.lower()
    word_count = len(query.split())
    _dbg(f"word_count: {word_count}, debug_words_match: {any(w in query_lower for w in DEBUG_WORDS)}", debug)

    for skill_name in relevant_skills:
        skill_meta_path = os.path.join("skills", skill_name, "meta.json")
        meta = _load_json(skill_meta_path)
        layers = meta.get("layers", {})

        parts = []

        # Always load core
        if "core" in layers:
            core_content = _load_skill_file(layers["core"]["path"])
            if core_content:
                parts.append(core_content)

        # Load failures if debugging
        if "failures" in layers:
            if any(w in query_lower for w in DEBUG_WORDS):
                fail_content = _load_skill_file(layers["failures"]["path"])
                if fail_content and fail_content.strip().count("\n") > 0:
                    parts.append(fail_content)

        # Load edge_cases if complex query
        if "edge_cases" in layers:
            if word_count > 8:
                ec_content = _load_skill_file(layers["edge_cases"]["path"])
                if ec_content and ec_content.strip().count("\n") > 0:
                    parts.append(ec_content)

        if parts:
            skill_sections.append((skill_name, "\n\n".join(parts)))
            _dbg(f"skill '{skill_name}' loaded {len(parts)} layer(s)", debug)

    # Filter atoms whose content is already in skill text (skill dedup)
    if atom_ids and skill_sections:
        all_skill_text = "\n".join(content for _, content in skill_sections)
        filtered_ids = []
        for aid in atom_ids:
            atom_path = os.path.join(CSARA_DIR, "memory", "atoms", f"{aid}.json")
            if not os.path.exists(atom_path):
                filtered_ids.append(aid)
                continue
            with open(atom_path, "r", encoding="utf-8") as f:
                atom = json.load(f)
            content = atom.get("content", "").strip().rstrip(".,;:!?")
            if content and content in all_skill_text:
                _dbg(f"  skipping {aid} — content already in skill", debug)
            else:
                filtered_ids.append(aid)
        atom_ids = filtered_ids

    # Read atom content
    atom_text = read_atoms(atom_ids) if atom_ids else ""
    _dbg(f"atom_text length: {len(atom_text)} chars", debug)

    # Output
    if not atom_text and not skill_sections:
        print("=== CSara Memory ===")
        print("No relevant memory or skills found for this query.")
        print("===================")
        return

    print("=== CSara Memory ===")
    print()

    if atom_text:
        print("[MEMORY]")
        print(atom_text)
    else:
        print("[MEMORY]")
        print("No relevant memory found.")

    print()

    for skill_name, content in skill_sections:
        print(f"[SKILL: {skill_name}]")
        print(content)
        print()

    print("===================")


def run_search(query: str) -> str:
    """Callable entry point for use by MCP server (no subprocess needed)."""
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        _do_search(query, debug=False)
    return buf.getvalue().strip()


def _do_search(query: str, debug: bool) -> None:
    """Core search logic extracted from main()."""
    keywords = _extract_keywords(query)
    _dbg(f"query: {query!r}", debug)
    _dbg(f"keywords: {keywords}", debug)

    if not keywords:
        print("=== CSara Memory ===")
        print("No relevant memory or skills found for this query.")
        print("===================")
        return

    keyword_hits = keyword_search(keywords)
    _dbg(f"keyword_hits: {keyword_hits}", debug)

    index_content = _load_json("index.json")
    relevant_skills = get_relevant_skills(query, index_content)
    atom_ids = get_relevant_atoms(query, index_content, keyword_hits) if keyword_hits else []

    # Load skill content BEFORE atoms (needed for dedup)
    query_lower = query.lower()
    word_count = len(query.split())
    skill_sections = []
    for skill_name in relevant_skills:
        meta = _load_json(os.path.join("skills", skill_name, "meta.json"))
        layers = meta.get("layers", {})
        parts = []
        if "core" in layers:
            c = _load_skill_file(layers["core"]["path"])
            if c:
                parts.append(c)
        if "failures" in layers and any(w in query_lower for w in DEBUG_WORDS):
            f = _load_skill_file(layers["failures"]["path"])
            if f and f.strip().count("\n") > 0:
                parts.append(f)
        if "edge_cases" in layers and word_count > 8:
            e = _load_skill_file(layers["edge_cases"]["path"])
            if e and e.strip().count("\n") > 0:
                parts.append(e)
        if parts:
            skill_sections.append((skill_name, "\n\n".join(parts)))

    # Filter atoms whose content is already in skill text (skill dedup)
    if atom_ids and skill_sections:
        all_skill_text = "\n".join(content for _, content in skill_sections)
        filtered_ids = []
        for aid in atom_ids:
            atom_path = os.path.join(CSARA_DIR, "memory", "atoms", f"{aid}.json")
            if not os.path.exists(atom_path):
                filtered_ids.append(aid)
                continue
            with open(atom_path, "r", encoding="utf-8") as f:
                atom = json.load(f)
            content = atom.get("content", "").strip().rstrip(".,;:!?")
            if content and content in all_skill_text:
                _dbg(f"  skipping {aid} — content already in skill", debug)
            else:
                filtered_ids.append(aid)
        atom_ids = filtered_ids

    atom_text = read_atoms(atom_ids) if atom_ids else ""

    if not atom_text and not skill_sections:
        print("=== CSara Memory ===")
        print("No relevant memory or skills found for this query.")
        print("===================")
        return

    print("=== CSara Memory ===")
    print()
    print("[MEMORY]")
    print(atom_text if atom_text else "No relevant memory found.")
    print()
    for skill_name, content in skill_sections:
        print(f"[SKILL: {skill_name}]")
        print(content)
        print()
    print("===================")


if __name__ == "__main__":
    main()
