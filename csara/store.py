import sys
import os
import argparse
import json
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ops.consolidate import consolidate
from ops.write import write_atom, replace_atom, extract_keywords
from ops.search import keyword_search
from ops.forget import forget_atom, forget_skill
from ops.skill_ops import update_skills, list_skills, create_skill
from api.agents.consolidator import judge_duplicate

CSARA_DIR = os.path.dirname(os.path.abspath(__file__))

DETAIL_THRESHOLD = 200


def _load_json(rel_path: str) -> dict:
    full = os.path.join(CSARA_DIR, rel_path)
    if not os.path.exists(full):
        return {}
    with open(full, "r", encoding="utf-8") as f:
        return json.load(f)


def _dbg(msg: str, debug: bool) -> None:
    if debug:
        print(f"  [DEBUG store] {msg}", file=sys.stderr)


def _save_detail(atom_id: str, raw_text: str, debug: bool) -> None:
    if len(raw_text) <= DETAIL_THRESHOLD:
        return
    detail_rel = os.path.join("memory", "detail", f"{atom_id}.md")
    detail_full = os.path.join(CSARA_DIR, detail_rel)
    os.makedirs(os.path.dirname(detail_full), exist_ok=True)
    with open(detail_full, "w", encoding="utf-8") as f:
        f.write(raw_text)
    atom_path = os.path.join(CSARA_DIR, "memory", "atoms", f"{atom_id}.json")
    if os.path.exists(atom_path):
        with open(atom_path, "r", encoding="utf-8") as f:
            atom = json.load(f)
        atom["content_path"] = detail_rel
        with open(atom_path, "w", encoding="utf-8") as f:
            json.dump(atom, f, indent=2)
            f.write("\n")
    _dbg(f"saved detail to {detail_rel} ({len(raw_text)} chars)", debug)


def _do_store(task_input: str, task_output: str, debug: bool) -> None:
    raw_text = f"{task_input} {task_output}"
    keywords = extract_keywords(raw_text)
    _dbg(f"extracted keywords: {keywords}", debug)

    hits = keyword_search(keywords) if keywords else {}
    _dbg(f"keyword hits: {hits}", debug)

    dup_id = None
    dup_content = ""
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
                _dbg(f"potential dup: {aid} (overlap: {len(shared_words)}/{min_len})", debug)
                break

    if dup_id:
        _dbg(f"dup found: {dup_id}, calling Claude judge...", debug)
        replacement = judge_duplicate(task_input, task_output, dup_content, [])
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
        update_skills(replacement)
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
        update_skills(result)
        print(f"CSara: stored as {atom_id}.")


def _update_memory(atom_id: str, new_content: str) -> None:
    atom_path = os.path.join(CSARA_DIR, "memory", "atoms", f"{atom_id}.json")
    if not os.path.exists(atom_path):
        print(f"CSara: {atom_id} not found.")
        return

    with open(atom_path, "r", encoding="utf-8") as f:
        old_atom = json.load(f)

    result = consolidate(f"Update {atom_id}", new_content)
    if result is None:
        result = dict(old_atom)
        result["content"] = new_content
        result["tags"] = old_atom.get("tags", [])
        result["type"] = old_atom.get("type", "pattern")

    old_detail = os.path.join(CSARA_DIR, "memory", "detail", f"{atom_id}.md")
    if os.path.exists(old_detail):
        os.remove(old_detail)

    replace_atom(atom_id, result)

    if len(new_content) > DETAIL_THRESHOLD:
        detail_rel = os.path.join("memory", "detail", f"{atom_id}.md")
        detail_full = os.path.join(CSARA_DIR, detail_rel)
        os.makedirs(os.path.dirname(detail_full), exist_ok=True)
        with open(detail_full, "w", encoding="utf-8") as f:
            f.write(new_content)
        with open(atom_path, "r", encoding="utf-8") as f:
            atom = json.load(f)
        atom["content_path"] = detail_rel
        with open(atom_path, "w", encoding="utf-8") as f:
            json.dump(atom, f, indent=2)
            f.write("\n")

    update_skills(result)
    print(f"CSara: updated {atom_id}.")


# --- MCP entry points ---

def run_store(task_input: str, task_output: str) -> str:
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        _do_store(task_input, task_output, debug=False)
    return buf.getvalue().strip() or "CSara: done."


def run_forget(atom_id: str) -> str:
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        forget_atom(atom_id)
    return buf.getvalue().strip() or "CSara: done."


def run_forget_skill(skill_name: str) -> str:
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        forget_skill(skill_name)
    return buf.getvalue().strip() or "CSara: done."


def run_list_skills() -> str:
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        list_skills()
    return buf.getvalue().strip() or "CSara: no skills registered."


def run_create_skill(name: str, summary: str, keywords: list[str], core_rules: str) -> str:
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        create_skill(name, summary, keywords, core_rules)
    return buf.getvalue().strip() or "CSara: done."


def run_update(atom_id: str, new_content: str) -> str:
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        _update_memory(atom_id, new_content)
    return buf.getvalue().strip() or "CSara: done."


def main():
    parser = argparse.ArgumentParser(description="CSara memory store")
    parser.add_argument("--input", help="Task input description")
    parser.add_argument("--output", help="Task output description")
    parser.add_argument("--forget", help="Atom ID to forget")
    parser.add_argument("--update", help="Atom ID to update")
    parser.add_argument("--content", help="New content for --update")
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
        list_skills()
        return

    if args.forget_skill:
        forget_skill(args.forget_skill)
        return

    if args.forget:
        _dbg(f"forget: {args.forget}", debug)
        forget_atom(args.forget)
        return

    if args.update:
        if not args.content:
            print("Error: --content is required with --update.", file=sys.stderr)
            sys.exit(1)
        _update_memory(args.update, args.content)
        return

    if not args.input or not args.output:
        print("Error: --input and --output are required (or use --forget).", file=sys.stderr)
        sys.exit(1)

    _dbg(f"input: {args.input!r}", debug)
    _dbg(f"output: {args.output!r}", debug)
    _do_store(args.input, args.output, debug)


if __name__ == "__main__":
    main()
