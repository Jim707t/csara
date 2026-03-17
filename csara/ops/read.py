import os
import json
from datetime import date

CSARA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_atoms(id_list: list) -> str:
    results = []
    today = date.today().isoformat()

    for atom_id in id_list:
        atom_path = os.path.join(CSARA_DIR, "memory", "atoms", f"{atom_id}.json")
        if not os.path.exists(atom_path):
            continue

        with open(atom_path, "r", encoding="utf-8") as f:
            atom = json.load(f)

        # Determine body text
        content_path = atom.get("content_path")
        if content_path:
            detail_full = os.path.join(CSARA_DIR, content_path)
            if os.path.exists(detail_full):
                with open(detail_full, "r", encoding="utf-8") as f:
                    body = f.read().strip()
            else:
                body = atom.get("content", "")
        else:
            body = atom.get("content", "")

        # Update last_accessed
        atom["last_accessed"] = today
        with open(atom_path, "w", encoding="utf-8") as f:
            json.dump(atom, f, indent=2)
            f.write("\n")

        # Format output
        atom_type = atom.get("type", "unknown")
        tags = ", ".join(atom.get("tags", []))
        strength = atom.get("strength", 0.5)
        header = f"[{atom_id} | {atom_type} | {tags} | strength: {strength}]"
        results.append(f"{header}\n{body}")

    return "\n\n".join(results)
