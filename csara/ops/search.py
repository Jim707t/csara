import os
import json
import math

CSARA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# BM25 parameters
BM25_K1 = 1.5
BM25_B = 0.75


def _load_json(rel_path: str) -> dict:
    full = os.path.join(CSARA_DIR, rel_path)
    if not os.path.exists(full):
        return {}
    with open(full, "r", encoding="utf-8") as f:
        return json.load(f)


def _compute_doc_stats(word_index: dict) -> tuple:
    """Compute document lengths and average from word_index.
    Returns (doc_lengths dict, avgdl float, N int)."""
    doc_lengths = {}
    for atom_ids in word_index.values():
        for aid in atom_ids:
            doc_lengths[aid] = doc_lengths.get(aid, 0) + 1
    n = len(doc_lengths)
    avgdl = sum(doc_lengths.values()) / n if n > 0 else 1
    return doc_lengths, avgdl, n


def keyword_search(keywords: list) -> dict:
    word_index = _load_json(os.path.join("memory", "index", "word_index.json"))
    doc_lengths, avgdl, n_docs = _compute_doc_stats(word_index)

    scores = {}

    for keyword in keywords:
        kw = keyword.lower()
        matching_atoms = set()

        # Exact match
        if kw in word_index:
            matching_atoms.update(word_index[kw])
            df = len(word_index[kw])
            idf = math.log((n_docs - df + 0.5) / (df + 0.5) + 1)
            for aid in word_index[kw]:
                dl = doc_lengths.get(aid, 1)
                # BM25 with binary tf (tf=1)
                tf_component = (BM25_K1 + 1) / (1 + BM25_K1 * (1 - BM25_B + BM25_B * dl / avgdl))
                scores[aid] = scores.get(aid, 0) + idf * tf_component

        # Substring matches (weaker signal, use half the BM25 score)
        if len(kw) < 5:
            continue
        for indexed_word, atom_ids in word_index.items():
            if indexed_word == kw:
                continue
            if len(indexed_word) < 5:
                continue
            matched = False
            if kw in indexed_word and len(kw) / len(indexed_word) > 0.5:
                matched = True
            elif indexed_word in kw and len(indexed_word) / len(kw) > 0.5:
                matched = True
            if matched:
                df = len(atom_ids)
                idf = math.log((n_docs - df + 0.5) / (df + 0.5) + 1)
                for aid in atom_ids:
                    if aid not in matching_atoms:
                        dl = doc_lengths.get(aid, 1)
                        tf_component = (BM25_K1 + 1) / (1 + BM25_K1 * (1 - BM25_B + BM25_B * dl / avgdl))
                        scores[aid] = scores.get(aid, 0) + idf * tf_component * 0.5

    if not scores:
        return {}

    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    if len(sorted_ids) > 30:
        sorted_ids = sorted_ids[:30]
    return {aid: scores[aid] for aid in sorted_ids}
