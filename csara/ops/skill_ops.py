import os
import json
from datetime import date

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


def update_skills(atom_dict: dict) -> None:
    """Update skill files when a new atom is stored."""
    from api.agents.skill_updater import update_skill_file

    index = _load_json("index.json")
    skills = index.get("skills", {})
    atom_tags = [t.lower() for t in atom_dict.get("tags", [])]
    atom_type = atom_dict.get("type", "")
    today = date.today().isoformat()

    type_to_file = {
        "pattern": ("core.md", "core"),
        "preference": ("core.md", "core"),
        "fix": ("failures.md", "failures"),
        "correction": ("failures.md", "failures"),
        "constraint": ("edge_cases.md", "edge_cases"),
    }

    if atom_type not in type_to_file:
        return

    target_filename, file_type = type_to_file[atom_type]

    new_text = atom_dict.get("content", "")
    if atom_dict.get("content_path"):
        detail_full = os.path.join(CSARA_DIR, atom_dict["content_path"])
        if os.path.exists(detail_full):
            with open(detail_full, "r", encoding="utf-8") as f:
                detail_text = f.read().strip()
            if detail_text:
                new_text += f"\n{detail_text}"

    for skill_name, skill_info in skills.items():
        trigger_kws = [kw.lower() for kw in skill_info.get("trigger_keywords", [])]
        if not any(tag in trigger_kws for tag in atom_tags):
            continue

        target_path = os.path.join(CSARA_DIR, "skills", skill_name, target_filename)
        if not os.path.exists(target_path):
            continue

        with open(target_path, "r", encoding="utf-8") as f:
            existing_content = f.read()

        result = update_skill_file(existing_content, file_type, new_text, atom_type)

        if result is None:
            continue
        elif result == "":
            if file_type == "failures":
                entry = f"\n\n## {today}\n{new_text}"
                with open(target_path, "a", encoding="utf-8") as f:
                    f.write(entry)
            else:
                with open(target_path, "a", encoding="utf-8") as f:
                    f.write(f"\n- {new_text}")
        else:
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(result)
                if not result.endswith("\n"):
                    f.write("\n")


def list_skills() -> None:
    index = _load_json("index.json")
    skills = index.get("skills", {})
    if not skills:
        print("CSara: no skills registered.")
        return
    for name, info in skills.items():
        keywords = ", ".join(info.get("trigger_keywords", []))
        print(f"  {name}: {info.get('summary', '')}")
        print(f"    keywords: {keywords}")


def create_skill(name: str, summary: str, keywords: list[str], core_rules: str) -> None:
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
