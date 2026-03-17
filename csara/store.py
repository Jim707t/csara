import sys
import os
import argparse
import json
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ops.consolidate import consolidate
from ops.write import write_atom, replace_atom
from ops.search import keyword_search
from api.agents.consolidator import judge_duplicate
import re

CSARA_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_json(rel_path: str) -> dict:
    full = os.path.join(CSARA_DIR, rel_path)
    if not os.path.exists(full):
        return {}
    with open(full, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(rel_path: str, data: dict) -> None:
    full = os.path.join(CSARA_DIR, rel_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def _forget(atom_id: str) -> None:
    atom_path = os.path.join(CSARA_DIR, "memory", "atoms", f"{atom_id}.json")
    if not os.path.exists(atom_path):
        print(f"CSara: {atom_id} not found.")
        return

    # Load atom to get its data
    with open(atom_path, "r", encoding="utf-8") as f:
        atom = json.load(f)

    # Delete atom file
    os.remove(atom_path)

    # Delete detail file if exists
    content_path = atom.get("content_path")
    if content_path:
        detail_full = os.path.join(CSARA_DIR, content_path)
        if os.path.exists(detail_full):
            os.remove(detail_full)

    # Remove from index.json
    index = _load_json("index.json")
    if atom_id in index.get("atoms", {}):
        del index["atoms"][atom_id]
        index["meta"]["total_atoms"] = len(index["atoms"])
    _save_json("index.json", index)

    # Remove from tag_index.json
    tag_index = _load_json(os.path.join("memory", "index", "tag_index.json"))
    tags_to_remove = []
    for tag, ids in tag_index.items():
        if atom_id in ids:
            ids.remove(atom_id)
        if not ids:
            tags_to_remove.append(tag)
    for tag in tags_to_remove:
        del tag_index[tag]
    _save_json(os.path.join("memory", "index", "tag_index.json"), tag_index)

    # Remove from type_index.json
    type_index = _load_json(os.path.join("memory", "index", "type_index.json"))
    types_to_remove = []
    for t, ids in type_index.items():
        if atom_id in ids:
            ids.remove(atom_id)
        if not ids:
            types_to_remove.append(t)
    for t in types_to_remove:
        del type_index[t]
    _save_json(os.path.join("memory", "index", "type_index.json"), type_index)

    # Remove from graph.json
    graph = _load_json(os.path.join("memory", "index", "graph.json"))
    if atom_id in graph:
        del graph[atom_id]
    # Also remove from other atoms' edge lists
    for aid, edges in graph.items():
        if isinstance(edges, dict):
            for edge_type, edge_val in edges.items():
                if isinstance(edge_val, list) and atom_id in edge_val:
                    edge_val.remove(atom_id)
                elif isinstance(edge_val, str) and edge_val == atom_id:
                    edges[edge_type] = ""
    _save_json(os.path.join("memory", "index", "graph.json"), graph)

    print(f"CSara: forgot {atom_id}.")


def _update_skills(atom_dict: dict) -> None:
    """Update skill files when a new atom is stored (Phase 5)."""
    index = _load_json("index.json")
    skills = index.get("skills", {})
    atom_tags = [t.lower() for t in atom_dict.get("tags", [])]
    atom_type = atom_dict.get("type", "")
    today = date.today().isoformat()

    for skill_name, skill_info in skills.items():
        trigger_kws = [kw.lower() for kw in skill_info.get("trigger_keywords", [])]
        if not any(tag in trigger_kws for tag in atom_tags):
            continue

        if atom_type in ("fix", "correction"):
            failures_path = os.path.join(CSARA_DIR, "skills", skill_name, "failures.md")
            if os.path.exists(failures_path):
                content = atom_dict.get("content", "")
                detail_text = ""
                if atom_dict.get("content_path"):
                    detail_full = os.path.join(CSARA_DIR, atom_dict["content_path"])
                    if os.path.exists(detail_full):
                        with open(detail_full, "r", encoding="utf-8") as f:
                            detail_text = f.read().strip()

                entry = f"\n\n## {today}\n{content}"
                if detail_text:
                    entry += f"\n{detail_text}"

                with open(failures_path, "a", encoding="utf-8") as f:
                    f.write(entry)

        elif atom_type == "pattern":
            core_path = os.path.join(CSARA_DIR, "skills", skill_name, "core.md")
            if os.path.exists(core_path):
                content = atom_dict.get("content", "")
                with open(core_path, "a", encoding="utf-8") as f:
                    f.write(f"\n- {content}")


def _forget_skill(skill_name: str) -> None:
    skill_dir = os.path.join(CSARA_DIR, "skills", skill_name)
    if not os.path.exists(skill_dir):
        print(f"CSara: skill '{skill_name}' not found.")
        return

    # Remove skill files
    for fname in os.listdir(skill_dir):
        os.remove(os.path.join(skill_dir, fname))
    os.rmdir(skill_dir)

    # Remove from index.json
    index = _load_json("index.json")
    if skill_name in index.get("skills", {}):
        del index["skills"][skill_name]
    _save_json("index.json", index)

    print(f"CSara: deleted skill '{skill_name}'.")


def _list_skills() -> None:
    index = _load_json("index.json")
    skills = index.get("skills", {})
    if not skills:
        print("CSara: no skills registered.")
        return
    for name, info in skills.items():
        keywords = ", ".join(info.get("trigger_keywords", []))
        print(f"  {name}: {info.get('summary', '')}")
        print(f"    keywords: {keywords}")


def _create_skill(name: str, summary: str, keywords: list[str], core_rules: str) -> None:
    skill_dir = os.path.join(CSARA_DIR, "skills", name)
    if os.path.exists(skill_dir):
        print(f"CSara: skill '{name}' already exists. Use csara_store to add to it.")
        return
    os.makedirs(skill_dir)

    meta = {
        "skill": name,
        "summary": summary,
        "trigger_keywords": keywords,
        "complexity_threshold": 0.7,
        "layers": {
            "core": {"path": f"skills/{name}/core.md", "load": "always"},
            "failures": {"path": f"skills/{name}/failures.md", "load": "if_debugging"},
            "edge_cases": {"path": f"skills/{name}/edge_cases.md", "load": "if_complex"}
        }
    }
    skill_meta_path = os.path.join(skill_dir, "meta.json")
    with open(skill_meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
        f.write("\n")

    with open(os.path.join(skill_dir, "core.md"), "w", encoding="utf-8") as f:
        f.write(f"# {name.title()} Core\n\n{core_rules}\n")
    open(os.path.join(skill_dir, "failures.md"), "w").close()
    open(os.path.join(skill_dir, "edge_cases.md"), "w").close()

    index = _load_json("index.json")
    index.setdefault("skills", {})[name] = {
        "summary": summary,
        "trigger_keywords": keywords
    }
    _save_json("index.json", index)

    print(f"CSara: skill '{name}' created.")


def run_create_skill(name: str, summary: str, keywords: list[str], core_rules: str) -> str:
    """Callable entry point for MCP server."""
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        _create_skill(name, summary, keywords, core_rules)
    return buf.getvalue().strip() or "CSara: done."


DETAIL_THRESHOLD = 200  # raw text longer than this gets saved to detail/


def _save_detail(atom_id: str, raw_text: str, debug: bool) -> None:
    """Save long raw text to detail/ and update the atom's content_path."""
    if len(raw_text) <= DETAIL_THRESHOLD:
        return
    detail_rel = os.path.join("memory", "detail", f"{atom_id}.md")
    detail_full = os.path.join(CSARA_DIR, detail_rel)
    os.makedirs(os.path.dirname(detail_full), exist_ok=True)
    with open(detail_full, "w", encoding="utf-8") as f:
        f.write(raw_text)
    # Update atom file to point to detail
    atom_path = os.path.join(CSARA_DIR, "memory", "atoms", f"{atom_id}.json")
    if os.path.exists(atom_path):
        with open(atom_path, "r", encoding="utf-8") as f:
            atom = json.load(f)
        atom["content_path"] = detail_rel
        with open(atom_path, "w", encoding="utf-8") as f:
            json.dump(atom, f, indent=2)
            f.write("\n")
    _dbg(f"saved detail to {detail_rel} ({len(raw_text)} chars)", debug)


def _dbg(msg: str, debug: bool) -> None:
    if debug:
        print(f"  [DEBUG store] {msg}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="CSara memory store")
    parser.add_argument("--input", help="Task input description")
    parser.add_argument("--output", help="Task output description")
    parser.add_argument("--forget", help="Atom ID to forget")
    parser.add_argument("--forget-skill", help="Skill name to delete")
    parser.add_argument("--list-skills", action="store_true", help="List all skills")
    parser.add_argument("--debug", action="store_true", help="Print debug trace")
    args = parser.parse_args()

    debug = args.debug
    if debug:
        from api.claude import set_debug
        set_debug(True)
        print("\n  [DEBUG] === store.py debug trace ===", file=sys.stderr)

    if args.list_skills:
        _list_skills()
        return

    if args.forget_skill:
        _forget_skill(args.forget_skill)
        return

    if args.forget:
        _dbg(f"forget: {args.forget}", debug)
        _forget(args.forget)
        return

    if not args.input or not args.output:
        print("Error: --input and --output are required (or use --forget).", file=sys.stderr)
        sys.exit(1)

    _dbg(f"input: {args.input!r}", debug)
    _dbg(f"output: {args.output!r}", debug)

    # --- Step 1: Pure-code similarity check BEFORE any Claude call ---
    stop_words = {
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
    raw_text = f"{args.input} {args.output}"
    keywords = [w for w in re.sub(r"[^\w\s]", "", raw_text.lower()).split()
                if w and w not in stop_words]
    _dbg(f"extracted keywords: {keywords}", debug)

    hits = keyword_search(keywords) if keywords else {}
    _dbg(f"keyword hits: {hits}", debug)

    dup_id = None
    dup_content = ""
    dup_tags = []
    if hits:
        index = _load_json("index.json")
        existing_atoms = index.get("atoms", {})
        raw_words = set(raw_text.lower().split())

        for aid, score in hits.items():
            info = existing_atoms.get(aid, {})
            old_content = info.get("content", "").lower()
            old_words = set(old_content.split())
            shared_words = raw_words & old_words
            min_len = min(len(raw_words), len(old_words))
            if min_len > 0 and len(shared_words) / min_len > 0.4:
                dup_id = aid
                dup_content = info.get("content", "")
                dup_tags = info.get("tags", [])
                _dbg(f"potential dup: {aid} (word overlap: {len(shared_words)}/{min_len})", debug)
                break

    # --- Step 2: Branch based on dup detection ---
    if dup_id:
        _dbg(f"dup found: {dup_id}, calling Claude judge...", debug)
        replacement = judge_duplicate(args.input, args.output, dup_content, dup_tags)
        if replacement is None:
            _dbg(f"judge says KEEP old {dup_id}", debug)
            print(f"CSara: {dup_id} already covers this, skipped.")
            return
        # Replace the old atom with richer new one
        # Remove old detail file if exists
        old_detail = os.path.join(CSARA_DIR, "memory", "detail", f"{dup_id}.md")
        if os.path.exists(old_detail):
            os.remove(old_detail)
        replace_atom(dup_id, replacement)
        _save_detail(dup_id, raw_text, debug)
        _dbg(f"replaced {dup_id} with new content", debug)
        _update_skills(replacement)
        _dbg(f"skill update check done", debug)
        print(f"CSara: replaced {dup_id} with richer info.")
    else:
        _dbg("no dup found, calling consolidator agent...", debug)
        result = consolidate(args.input, args.output)
        _dbg(f"consolidator result: {json.dumps(result, indent=2) if result else 'None'}", debug)
        if result is None:
            print("CSara: nothing worth storing.")
            return
        atom_id = write_atom(result)
        _save_detail(atom_id, raw_text, debug)
        _dbg(f"wrote atom: {atom_id}", debug)
        _update_skills(result)
        _dbg(f"skill update check done", debug)
        print(f"CSara: stored as {atom_id}.")


def run_store(task_input: str, task_output: str) -> str:
    """Callable entry point for MCP server."""
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        _do_store(task_input, task_output, debug=False)
    return buf.getvalue().strip() or "CSara: done."


def run_forget(atom_id: str) -> str:
    """Callable entry point for MCP server."""
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        _forget(atom_id)
    return buf.getvalue().strip() or "CSara: done."


def run_forget_skill(skill_name: str) -> str:
    """Callable entry point for MCP server."""
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        _forget_skill(skill_name)
    return buf.getvalue().strip() or "CSara: done."


def run_list_skills() -> str:
    """Callable entry point for MCP server."""
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        _list_skills()
    return buf.getvalue().strip() or "CSara: no skills registered."


def _do_store(task_input: str, task_output: str, debug: bool) -> None:
    """Core store logic extracted from main()."""
    stop_words = {
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
    raw_text = f"{task_input} {task_output}"
    keywords = [w for w in re.sub(r"[^\w\s]", "", raw_text.lower()).split()
                if w and w not in stop_words]
    _dbg(f"extracted keywords: {keywords}", debug)

    hits = keyword_search(keywords) if keywords else {}
    _dbg(f"keyword hits: {hits}", debug)

    dup_id = None
    dup_content = ""
    dup_tags = []
    if hits:
        index = _load_json("index.json")
        existing_atoms = index.get("atoms", {})
        raw_words = set(raw_text.lower().split())
        for aid, score in hits.items():
            info = existing_atoms.get(aid, {})
            old_content = info.get("content", "").lower()
            old_words = set(old_content.split())
            shared_words = raw_words & old_words
            min_len = min(len(raw_words), len(old_words))
            if min_len > 0 and len(shared_words) / min_len > 0.4:
                dup_id = aid
                dup_content = info.get("content", "")
                dup_tags = info.get("tags", [])
                _dbg(f"potential dup: {aid} (word overlap: {len(shared_words)}/{min_len})", debug)
                break

    if dup_id:
        _dbg(f"dup found: {dup_id}, calling Claude judge...", debug)
        replacement = judge_duplicate(task_input, task_output, dup_content, dup_tags)
        if replacement is None:
            _dbg(f"judge says KEEP old {dup_id}", debug)
            print(f"CSara: {dup_id} already covers this, skipped.")
            return
        old_detail = os.path.join(CSARA_DIR, "memory", "detail", f"{dup_id}.md")
        if os.path.exists(old_detail):
            os.remove(old_detail)
        replace_atom(dup_id, replacement)
        _save_detail(dup_id, raw_text, debug)
        _dbg(f"replaced {dup_id} with new content", debug)
        _update_skills(replacement)
        print(f"CSara: replaced {dup_id} with richer info.")
    else:
        _dbg("no dup found, calling consolidator agent...", debug)
        result = consolidate(task_input, task_output)
        _dbg(f"consolidator result: {result}", debug)
        if result is None:
            print("CSara: nothing worth storing.")
            return
        atom_id = write_atom(result)
        _save_detail(atom_id, raw_text, debug)
        _dbg(f"wrote atom: {atom_id}", debug)
        _update_skills(result)
        print(f"CSara: stored as {atom_id}.")


if __name__ == "__main__":
    main()
