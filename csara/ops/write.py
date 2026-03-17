import os
import json
import re
from datetime import date

CSARA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _next_atom_id() -> str:
    atoms_dir = os.path.join(CSARA_DIR, "memory", "atoms")
    if not os.path.exists(atoms_dir):
        os.makedirs(atoms_dir, exist_ok=True)
        return "mem_001"

    existing = []
    for fname in os.listdir(atoms_dir):
        m = re.match(r"mem_(\d+)\.json", fname)
        if m:
            existing.append(int(m.group(1)))

    if not existing:
        return "mem_001"

    next_num = max(existing) + 1
    return f"mem_{next_num:03d}"


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


def write_atom(atom_dict: dict) -> str:
    today = date.today().isoformat()

    atom_id = _next_atom_id()
    atom_dict["id"] = atom_id
    atom_dict["created"] = today
    atom_dict["last_accessed"] = today

    # Default edges if not provided
    if "edges" not in atom_dict or not atom_dict["edges"]:
        atom_dict["edges"] = {
            "supports": [],
            "contradicts": [],
            "learned_from": "",
            "belongs_to": [],
            "occurred_in": [],
            "fixed_by": [],
            "generalizes": []
        }

    # 1. Write atom file
    atom_path = os.path.join("memory", "atoms", f"{atom_id}.json")
    _save_json(atom_path, atom_dict)

    # 2. Update index.json
    index = _load_json("index.json")
    if "atoms" not in index:
        index["atoms"] = {}
    if "meta" not in index:
        index["meta"] = {"created": today, "total_atoms": 0}

    index["atoms"][atom_id] = {
        "content": atom_dict.get("content", ""),
        "type": atom_dict.get("type", ""),
        "tags": atom_dict.get("tags", []),
        "strength": atom_dict.get("strength", 0.5)
    }
    index["meta"]["total_atoms"] = len(index["atoms"])
    _save_json("index.json", index)

    # 3. Update tag_index.json
    tag_index = _load_json(os.path.join("memory", "index", "tag_index.json"))
    for tag in atom_dict.get("tags", []):
        tag_lower = tag.lower()
        if tag_lower not in tag_index:
            tag_index[tag_lower] = []
        if atom_id not in tag_index[tag_lower]:
            tag_index[tag_lower].append(atom_id)
    _save_json(os.path.join("memory", "index", "tag_index.json"), tag_index)

    # 4. Update type_index.json
    type_index = _load_json(os.path.join("memory", "index", "type_index.json"))
    atom_type = atom_dict.get("type", "")
    if atom_type:
        if atom_type not in type_index:
            type_index[atom_type] = []
        if atom_id not in type_index[atom_type]:
            type_index[atom_type].append(atom_id)
    _save_json(os.path.join("memory", "index", "type_index.json"), type_index)

    # 5. Update graph.json
    graph = _load_json(os.path.join("memory", "index", "graph.json"))
    graph[atom_id] = atom_dict.get("edges", {})
    _save_json(os.path.join("memory", "index", "graph.json"), graph)

    return atom_id


def replace_atom(old_id: str, new_atom_dict: dict) -> str:
    """Replace an existing atom with new data, reusing the same ID."""
    # Load old atom to clean up its index entries
    old_path = os.path.join("memory", "atoms", f"{old_id}.json")
    old_full = os.path.join(CSARA_DIR, old_path)
    if os.path.exists(old_full):
        with open(old_full, "r", encoding="utf-8") as f:
            old_atom = json.load(f)

        # Remove old tags from tag_index
        tag_index = _load_json(os.path.join("memory", "index", "tag_index.json"))
        for tag in old_atom.get("tags", []):
            tl = tag.lower()
            if tl in tag_index and old_id in tag_index[tl]:
                tag_index[tl].remove(old_id)
                if not tag_index[tl]:
                    del tag_index[tl]
        _save_json(os.path.join("memory", "index", "tag_index.json"), tag_index)

        # Remove old type from type_index
        type_index = _load_json(os.path.join("memory", "index", "type_index.json"))
        old_type = old_atom.get("type", "")
        if old_type and old_type in type_index and old_id in type_index[old_type]:
            type_index[old_type].remove(old_id)
            if not type_index[old_type]:
                del type_index[old_type]
        _save_json(os.path.join("memory", "index", "type_index.json"), type_index)

    # Now write the new atom with the same ID
    today = date.today().isoformat()
    new_atom_dict["id"] = old_id
    new_atom_dict["created"] = today
    new_atom_dict["last_accessed"] = today

    if "edges" not in new_atom_dict or not new_atom_dict["edges"]:
        new_atom_dict["edges"] = {
            "supports": [], "contradicts": [], "learned_from": "",
            "belongs_to": [], "occurred_in": [], "fixed_by": [], "generalizes": []
        }

    # Overwrite atom file
    _save_json(os.path.join("memory", "atoms", f"{old_id}.json"), new_atom_dict)

    # Update index.json
    index = _load_json("index.json")
    if "atoms" not in index:
        index["atoms"] = {}
    index["atoms"][old_id] = {
        "content": new_atom_dict.get("content", ""),
        "type": new_atom_dict.get("type", ""),
        "tags": new_atom_dict.get("tags", []),
        "strength": new_atom_dict.get("strength", 0.5)
    }
    _save_json("index.json", index)

    # Add new tags to tag_index
    tag_index = _load_json(os.path.join("memory", "index", "tag_index.json"))
    for tag in new_atom_dict.get("tags", []):
        tl = tag.lower()
        if tl not in tag_index:
            tag_index[tl] = []
        if old_id not in tag_index[tl]:
            tag_index[tl].append(old_id)
    _save_json(os.path.join("memory", "index", "tag_index.json"), tag_index)

    # Add new type to type_index
    type_index = _load_json(os.path.join("memory", "index", "type_index.json"))
    new_type = new_atom_dict.get("type", "")
    if new_type:
        if new_type not in type_index:
            type_index[new_type] = []
        if old_id not in type_index[new_type]:
            type_index[new_type].append(old_id)
    _save_json(os.path.join("memory", "index", "type_index.json"), type_index)

    # Update graph
    graph = _load_json(os.path.join("memory", "index", "graph.json"))
    graph[old_id] = new_atom_dict.get("edges", {})
    _save_json(os.path.join("memory", "index", "graph.json"), graph)

    return old_id
