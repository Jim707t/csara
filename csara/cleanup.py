"""CSara cleanup — periodic maintenance that Copilot can't do.

Loads ALL atoms, sends batches to Claude for systemic analysis:
- Redundant pairs (atoms that cover the same info)
- Atoms whose content is fully covered by a skill
- Meta-noise (atoms about CSara itself that pollute search)
- Stale atoms (never accessed, very old)

Run: python csara/cleanup.py
Dry run (default): prints recommendations only
Apply:  python csara/cleanup.py --apply
Debug:  python csara/cleanup.py --debug
"""

import sys
import os
import json
import argparse
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.claude import call_claude, set_debug
from ops.forget import forget_atom

CSARA_DIR = os.path.dirname(os.path.abspath(__file__))

CLEANUP_PROMPT = """You are a memory corpus cleanup agent. You will see a batch of stored memories from a personal AI assistant's memory system.

Identify problems. For each problem found, return a JSON object in an array.

Problem types:
1. "redundant" — two atoms cover the same information. Keep the richer one.
2. "skill_covered" — atom content is fully captured by a loaded skill (you'll see skill summaries).
3. "meta_noise" — atom is about the memory system itself rather than actual user work. These pollute search results by matching many queries.
4. "stale" — atom describes something likely obsolete (old dates, references to removed features).
5. "vague" — atom is too abstract to be actionable. It lost specific details during consolidation.

Return format — a JSON array:
[
  {"action": "forget", "atom_id": "mem_XXX", "reason": "redundant with mem_YYY which has more detail"},
  {"action": "forget", "atom_id": "mem_XXX", "reason": "fully covered by python skill"},
  {"action": "flag", "atom_id": "mem_XXX", "reason": "meta-noise: describes CSara internals, not user work"}
]

Rules:
- "forget" = safe to delete. "flag" = needs human review.
- Be conservative. Only recommend forget for clear redundancy or skill coverage.
- Use "flag" for meta-noise and vague atoms — let the human decide.
- If nothing is wrong with a batch, return: []
- Return ONLY the JSON array. No explanation."""


def _load_all_atoms() -> list:
    atoms_dir = os.path.join(CSARA_DIR, "memory", "atoms")
    atoms = []
    for fname in sorted(os.listdir(atoms_dir)):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(atoms_dir, fname), "r", encoding="utf-8") as f:
            atom = json.load(f)
        atoms.append(atom)
    return atoms


def _load_skill_summaries() -> str:
    index_path = os.path.join(CSARA_DIR, "index.json")
    if not os.path.exists(index_path):
        return ""
    with open(index_path, "r", encoding="utf-8") as f:
        index = json.load(f)
    skills = index.get("skills", {})
    if not skills:
        return ""
    lines = []
    for name, info in skills.items():
        summary = info.get("summary", "")
        lines.append(f"- {name}: {summary}")
    return "\n".join(lines)


def _format_atom(atom: dict) -> str:
    aid = atom.get("id", "?")
    atype = atom.get("type", "?")
    content = atom.get("content", "")
    source = atom.get("source_task", "")
    created = atom.get("created", "?")
    accessed = atom.get("last_accessed", "?")
    return f"[{aid} | {atype} | created:{created} | accessed:{accessed}]\n  source: {source}\n  content: {content}"


def _run_batch(batch: list, skill_summaries: str) -> list:
    atoms_text = "\n\n".join(_format_atom(a) for a in batch)
    user_msg = f"Skills:\n{skill_summaries}\n\nMemories:\n{atoms_text}" if skill_summaries else f"Memories:\n{atoms_text}"

    response = call_claude(CLEANUP_PROMPT, user_msg, max_tokens=1000)
    if not response or response.strip() == "[]":
        return []

    try:
        results = json.loads(response.strip())
        if isinstance(results, list):
            return [r for r in results if isinstance(r, dict) and "atom_id" in r]
    except json.JSONDecodeError:
        print(f"  Warning: failed to parse Claude response: {response[:200]}", file=sys.stderr)

    return []


def main():
    parser = argparse.ArgumentParser(description="CSara periodic cleanup")
    parser.add_argument("--apply", action="store_true", help="Actually forget recommended atoms (default: dry run)")
    parser.add_argument("--debug", action="store_true", help="Print debug trace")
    parser.add_argument("--batch-size", type=int, default=25, help="Atoms per Claude call (default: 25)")
    args = parser.parse_args()

    if args.debug:
        set_debug(True)

    atoms = _load_all_atoms()
    skill_summaries = _load_skill_summaries()

    print(f"CSara cleanup: {len(atoms)} atoms, {len(skill_summaries.splitlines())} skills")
    print(f"Mode: {'APPLY' if args.apply else 'DRY RUN'}")
    print()

    all_recommendations = []
    batch_size = args.batch_size

    for i in range(0, len(atoms), batch_size):
        batch = atoms[i:i + batch_size]
        batch_ids = [a.get("id", "?") for a in batch]
        print(f"Batch {i // batch_size + 1}: {batch_ids[0]}..{batch_ids[-1]} ({len(batch)} atoms)")

        recs = _run_batch(batch, skill_summaries)
        if recs:
            all_recommendations.extend(recs)
            for r in recs:
                action = r.get("action", "?")
                aid = r.get("atom_id", "?")
                reason = r.get("reason", "")
                marker = "DELETE" if action == "forget" else "REVIEW"
                print(f"  [{marker}] {aid}: {reason}")
        else:
            print(f"  (clean)")

    print()
    print(f"=== Summary ===")

    forgets = [r for r in all_recommendations if r.get("action") == "forget"]
    flags = [r for r in all_recommendations if r.get("action") == "flag"]

    print(f"Forget: {len(forgets)} atoms")
    for r in forgets:
        print(f"  {r['atom_id']}: {r.get('reason', '')}")

    print(f"Flag for review: {len(flags)} atoms")
    for r in flags:
        print(f"  {r['atom_id']}: {r.get('reason', '')}")

    if args.apply and forgets:
        print()
        confirm = input(f"Delete {len(forgets)} atoms? (yes/no): ").strip().lower()
        if confirm == "yes":
            for r in forgets:
                forget_atom(r["atom_id"])
            print(f"Done. Deleted {len(forgets)} atoms.")
        else:
            print("Cancelled.")
    elif forgets and not args.apply:
        print()
        print("Run with --apply to delete recommended atoms.")


if __name__ == "__main__":
    main()
