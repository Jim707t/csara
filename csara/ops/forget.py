import os
import json

CSARA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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


def forget_atom(atom_id: str) -> None:
    atom_path = os.path.join(CSARA_DIR, "memory", "atoms", f"{atom_id}.json")
    if not os.path.exists(atom_path):
        print(f"CSara: {atom_id} not found.")
        return

    with open(atom_path, "r", encoding="utf-8") as f:
        atom = json.load(f)

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

    # Remove from word_index.json
    word_index = _load_json(os.path.join("memory", "index", "word_index.json"))
    word_index = {k: [a for a in v if a != atom_id] for k, v in word_index.items()}
    word_index = {k: v for k, v in word_index.items() if v}
    _save_json(os.path.join("memory", "index", "word_index.json"), word_index)

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
    for aid, edges in graph.items():
        if isinstance(edges, dict):
            for edge_type, edge_val in edges.items():
                if isinstance(edge_val, list) and atom_id in edge_val:
                    edge_val.remove(atom_id)
                elif isinstance(edge_val, str) and edge_val == atom_id:
                    edges[edge_type] = ""
    _save_json(os.path.join("memory", "index", "graph.json"), graph)

    print(f"CSara: forgot {atom_id}.")


def forget_skill(skill_name: str) -> None:
    skill_dir = os.path.join(CSARA_DIR, "skills", skill_name)
    if not os.path.exists(skill_dir):
        print(f"CSara: skill '{skill_name}' not found.")
        return

    for fname in os.listdir(skill_dir):
        os.remove(os.path.join(skill_dir, fname))
    os.rmdir(skill_dir)

    index = _load_json("index.json")
    if skill_name in index.get("skills", {}):
        del index["skills"][skill_name]
    _save_json("index.json", index)

    print(f"CSara: deleted skill '{skill_name}'.")
