import os
import json
from datetime import date

CSARA_DIR = os.path.dirname(os.path.abspath(__file__))


def create_dir(rel_path: str) -> bool:
    full = os.path.join(CSARA_DIR, rel_path)
    if not os.path.exists(full):
        os.makedirs(full, exist_ok=True)
        return True
    return False


def create_file(rel_path: str, content: str) -> bool:
    full = os.path.join(CSARA_DIR, rel_path)
    if os.path.exists(full):
        return False
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)
    return True


def main():
    folders = [
        os.path.join("memory", "atoms"),
        os.path.join("memory", "detail"),
        os.path.join("memory", "index"),

        "skills",
        os.path.join("skills", "python"),
        "ops",
        "api",
        os.path.join("api", "agents"),
    ]

    folders_created = []
    for f in folders:
        if create_dir(f):
            folders_created.append(f)

    today = date.today().isoformat()

    boot_md = """# CSara Memory System

Before any task: python csara/search.py --q "your query"
After any task:  python csara/store.py --input "what you were asked" --output "what you produced"
Forget a memory: python csara/store.py --forget mem_001

Output from search.py is plain text. Inject it into your context before working.
"""

    index_json = {
        "atoms": {},
        "skills": {
            "python": {
                "summary": "Python coding patterns and personal conventions",
                "trigger_keywords": [
                    "python", "code", "script", "debug", "function",
                    "class", "import", "error", "traceback"
                ],
                "path": "skills/python/meta.json"
            }
        },
        "meta": {
            "created": today,
            "total_atoms": 0
        }
    }

    graph_json = {}
    tag_index_json = {}
    type_index_json = {}

    env_content = "ANTHROPIC_API_KEY=your_key_here\n"

    python_meta = {
        "skill": "python",
        "summary": "Python coding patterns and personal conventions",
        "trigger_keywords": [
            "python", "code", "script", "debug", "function",
            "class", "import", "error", "traceback"
        ],
        "complexity_threshold": 0.7,
        "layers": {
            "core": {"path": "skills/python/core.md", "load": "always"},
            "failures": {"path": "skills/python/failures.md", "load": "if_debugging"},
            "edge_cases": {"path": "skills/python/edge_cases.md", "load": "if_complex"}
        }
    }

    core_md = """# Python Core

- Type hint all function signatures
- Max 20 lines per function, split if longer
- Use asyncio.gather for concurrent async calls, never sequential awaits
- Never use bare except, always specify exception type
- Use context managers for file handles and connections
- Prefer list comprehensions over map/filter for readability
"""

    failures_md = "# Python Failures\n"
    edge_cases_md = "# Python Edge Cases\n"

    files_info = [
        ("boot.md", boot_md),
        ("index.json", json.dumps(index_json, indent=2) + "\n"),
        (os.path.join("memory", "index", "graph.json"), json.dumps(graph_json, indent=2) + "\n"),
        (os.path.join("memory", "index", "tag_index.json"), json.dumps(tag_index_json, indent=2) + "\n"),
        (os.path.join("memory", "index", "type_index.json"), json.dumps(type_index_json, indent=2) + "\n"),
        (".env", env_content),
        (os.path.join("skills", "python", "meta.json"), json.dumps(python_meta, indent=2) + "\n"),
        (os.path.join("skills", "python", "core.md"), core_md),
        (os.path.join("skills", "python", "failures.md"), failures_md),
        (os.path.join("skills", "python", "edge_cases.md"), edge_cases_md),
    ]

    files_created = []
    for rel_path, content in files_info:
        if create_file(rel_path, content):
            files_created.append(rel_path)

    print("CSara initialized.")
    if folders_created:
        print(f"Folders created: {', '.join(folders_created)}")
    if files_created:
        print(f"Files created: {', '.join(files_created)}")
    print("Ready. Add your ANTHROPIC_API_KEY to csara/.env")


if __name__ == "__main__":
    main()
