import os
import json

CSARA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_json(rel_path: str) -> dict:
    full = os.path.join(CSARA_DIR, rel_path)
    if not os.path.exists(full):
        return {}
    with open(full, "r", encoding="utf-8") as f:
        return json.load(f)


def keyword_search(keywords: list) -> dict:
    tag_index = _load_json(os.path.join("memory", "index", "tag_index.json"))
    index = _load_json("index.json")
    atoms = index.get("atoms", {})

    scores = {}

    for keyword in keywords:
        kw = keyword.lower()
        already_counted = set()

        # Check tag_index (exact match, case insensitive)
        for tag_key, atom_ids in tag_index.items():
            if tag_key.lower() == kw:
                for aid in atom_ids:
                    scores[aid] = scores.get(aid, 0) + 1
                    already_counted.add(aid)

        # Scan content field in index.json atoms (substring match)
        for aid, atom_info in atoms.items():
            if aid in already_counted:
                continue
            content = atom_info.get("content", "").lower()
            if kw in content:
                scores[aid] = scores.get(aid, 0) + 1

    if not scores:
        return {}

    # Threshold filter: keep atoms matching at least half the keywords, capped at 4
    import math
    min_score = max(1, min(math.ceil(len(keywords) / 2), 4))
    filtered = {aid: s for aid, s in scores.items() if s >= min_score}

    if not filtered:
        return {}

    # Sort by score descending, cap at 30
    sorted_ids = sorted(filtered.keys(), key=lambda x: filtered[x], reverse=True)
    if len(sorted_ids) > 30:
        sorted_ids = sorted_ids[:30]
    return {aid: filtered[aid] for aid in sorted_ids}
