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
    word_index = _load_json(os.path.join("memory", "index", "word_index.json"))

    scores = {}

    for keyword in keywords:
        kw = keyword.lower()

        # Check word_index for exact match
        if kw in word_index:
            for aid in word_index[kw]:
                scores[aid] = scores.get(aid, 0) + 1

        # Also check substring matches in word_index keys
        # e.g. searching "sqrt" matches "math-sqrt" or "sqrt144"
        # Min 4 chars to avoid noisy short-word matches ("is" in "list")
        if len(kw) < 4:
            continue
        for indexed_word, atom_ids in word_index.items():
            if indexed_word == kw:
                continue  # already counted
            if len(indexed_word) < 4:
                continue
            if kw in indexed_word or indexed_word in kw:
                for aid in atom_ids:
                    scores[aid] = scores.get(aid, 0) + 0.5

    if not scores:
        return {}

    # With full-text word_index, even 1 keyword match is meaningful.
    # Sort by score descending, cap at 30.
    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    if len(sorted_ids) > 30:
        sorted_ids = sorted_ids[:30]
    return {aid: scores[aid] for aid in sorted_ids}
