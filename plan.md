# CSara — Build Plan
**Context Storage & Agent Retrieval Architecture**
Prototype for personal use. Copilot calls it through the CLI.
No external libraries. Python stdlib + Claude API only.

---

## What You Are Building

CSara is a memory system that sits next to your project on disk.
Copilot runs CLI commands to search memory and store memory.
CSara uses the Claude API internally to make retrieval and consolidation accurate.
CSara never executes tasks. It only returns relevant data to the caller.

The full interaction from Copilot's side looks like this:

```
# Before starting a task — get relevant memory and skills
python csara/search.py --q "async python debug"
# CSara prints relevant memory atoms as plain text
# Copilot reads that output and injects it into its own context

# After finishing a task — store what is worth remembering
python csara/store.py --input "fix the async function" --output "used asyncio.gather, it was blocking sequentially"
# CSara decides internally whether to store anything and does it silently
```

That is the entire interface Copilot needs to know.

---

## Environment Setup

CSara has zero external dependencies. No pip installs. No requirements.txt.
Every import used is Python stdlib: json, os, sys, pathlib, argparse, datetime, hashlib, re, urllib.request.

A virtual environment is still recommended so CSara runs in isolation from the project's own dependencies.

**Create and activate the venv once (the user does this manually after cloning):**

```bash
# From the project root (the directory that contains the csara/ folder)
python3 -m venv csara/.venv

# Activate on Mac/Linux:
source csara/.venv/bin/activate

# Activate on Windows:
csara\.venv\Scripts\activate
```

After activation, all `python csara/search.py` and `python csara/store.py` commands run inside that venv.

**init.py does NOT create or activate the venv.** The user creates it once manually. init.py only creates the folder structure and seed files.

**The only thing inside the venv is Python itself.** No packages are installed. The venv exists purely for process isolation.

If the user never activates the venv, CSara still works using the system Python as long as it is 3.10+. The venv is a recommendation, not a requirement.

---

## Constraints

- Python 3.10+ only
- No pip installs. Only Python stdlib: json, os, sys, pathlib, argparse, datetime, hashlib, re, urllib.request
- Claude API called directly with urllib.request — no anthropic SDK
- Claude API key stored in csara/.env as: ANTHROPIC_API_KEY=sk-ant-...
- CSara folder lives inside the project directory Copilot is working in
- All paths are relative to the csara/ folder
- No database. Everything is plain JSON files and .md files on disk

---

## Final Folder Structure

```
csara/
  .env                          # ANTHROPIC_API_KEY=sk-ant-... (user fills this in)
  boot.md                       # ~80 tokens, tells Copilot what commands exist
  index.json                    # master list of all atoms and skills

  memory/
    atoms/                      # one .json file per memory atom
      mem_001.json
      mem_002.json
    detail/                     # .md files for atoms with long content
      mem_002.md
    index/
      graph.json                # edges between atoms
      tag_index.json            # tag -> list of atom IDs
      type_index.json           # type -> list of atom IDs

  skills/
    python/
      meta.json
      core.md
      failures.md
      edge_cases.md

  ops/
    write.py                    # create or update an atom
    read.py                     # load atoms by ID list
    search.py                   # keyword search, returns atom text
    consolidate.py              # extract signal from task I/O

  api/
    claude.py                   # single function to call Claude API
    agents/
      retrieval.py              # decides which atom IDs to load for a query
      consolidator.py           # decides what new atom to create or returns null

  search.py                     # CLI entry point: python csara/search.py --q "..."
  store.py                      # CLI entry point: python csara/store.py --input "..." --output "..."
  init.py                       # CLI entry point: python csara/init.py (run once to create all folders and seed files)
```

---

## Phase 1 — Folder Structure and Seed Files

**Goal:** Running `python csara/init.py` creates the entire folder structure and all seed files so the system is ready to use.

### 1.1 — init.py

This file is run once. It creates every folder and every seed file listed below.
If a file already exists, it skips it without overwriting.

```
python csara/init.py
```

Expected output:
```
CSara initialized.
Folders created: memory/atoms, memory/detail, memory/index, skills/, ops/, api/agents/
Files created: boot.md, index.json, memory/index/graph.json, memory/index/tag_index.json, memory/index/type_index.json
Ready. Add your ANTHROPIC_API_KEY to csara/.env
```

### 1.2 — boot.md (created by init.py)

Exactly this content, nothing more:

```markdown
# CSara Memory System

Before any task: python csara/search.py --q "your query"
After any task:  python csara/store.py --input "what you were asked" --output "what you produced"
Forget a memory: python csara/store.py --forget mem_001

Output from search.py is plain text. Inject it into your context before working.
```

### 1.3 — index.json (created by init.py)

```json
{
  "atoms": {},
  "skills": {
    "python": {
      "summary": "Python coding patterns and personal conventions",
      "trigger_keywords": ["python", "code", "script", "debug", "function", "class", "import", "error", "traceback"],
      "path": "skills/python/meta.json"
    }
  },
  "meta": {
    "created": "YYYY-MM-DD",
    "total_atoms": 0
  }
}
```

The `atoms` object maps atom ID to a summary object:
```json
"mem_001": {
  "content": "short summary of the atom",
  "type": "preference",
  "tags": ["python", "async"],
  "strength": 0.9
}
```

This is what the retrieval agent reads. It never reads individual atom files during the search phase.

### 1.4 — memory/index/graph.json (created by init.py)

```json
{}
```

When atoms exist, it looks like:
```json
{
  "mem_001": {
    "supports": ["mem_047"],
    "belongs_to": ["skill:python"]
  },
  "mem_047": {
    "fixed_by": ["mem_001"],
    "occurred_in": ["project:csara"]
  }
}
```

### 1.5 — memory/index/tag_index.json (created by init.py)

```json
{}
```

When atoms exist:
```json
{
  "python": ["mem_001", "mem_047"],
  "async": ["mem_001", "mem_047"],
  "notion": ["mem_089"]
}
```

### 1.6 — memory/index/type_index.json (created by init.py)

```json
{}
```

When atoms exist:
```json
{
  "preference": ["mem_001"],
  "fix": ["mem_047"],
  "constraint": ["mem_089"]
}
```

### 1.7 — .env (created by init.py only if it does not exist)

```
ANTHROPIC_API_KEY=your_key_here
```

### 1.8 — Starter skill: skills/python/meta.json (created by init.py)

```json
{
  "skill": "python",
  "summary": "Python coding patterns and personal conventions",
  "trigger_keywords": ["python", "code", "script", "debug", "function", "class", "import", "error", "traceback"],
  "complexity_threshold": 0.7,
  "layers": {
    "core":       { "path": "skills/python/core.md",       "load": "always" },
    "failures":   { "path": "skills/python/failures.md",   "load": "if_debugging" },
    "edge_cases": { "path": "skills/python/edge_cases.md", "load": "if_complex" }
  }
}
```

### 1.9 — Starter skill: skills/python/core.md (created by init.py)

```markdown
# Python Core

- Type hint all function signatures
- Max 20 lines per function, split if longer
- Use asyncio.gather for concurrent async calls, never sequential awaits
- Never use bare except, always specify exception type
- Use context managers for file handles and connections
- Prefer list comprehensions over map/filter for readability
```

### 1.10 — skills/python/failures.md and skills/python/edge_cases.md

Created empty by init.py with just a `# Python Failures` and `# Python Edge Cases` heading.
These grow automatically as Copilot uses the system.

---

## Phase 2 — ops/ Files

These are pure execution files. No LLM calls. No decision making. Just read and write disk.

### 2.1 — ops/write.py

**Purpose:** Create a new atom JSON file. Update the three index files and graph.json atomically.

**Usage (called internally by store.py, not directly by Copilot):**
```python
from ops.write import write_atom
atom_id = write_atom(atom_dict)
```

**What write_atom(atom_dict) does step by step:**

1. Generate atom ID: `mem_` + zero-padded integer. Read all files in `memory/atoms/`, find the highest existing number, increment by 1. Example: if mem_047.json exists and is highest, next is mem_048.
2. Set `atom_dict["id"]` to the new ID.
3. Set `atom_dict["created"]` to today's date as YYYY-MM-DD string.
4. Set `atom_dict["last_accessed"]` to today's date.
5. Write `memory/atoms/{id}.json` with json.dumps(atom_dict, indent=2).
6. If `atom_dict["content_path"]` is not null, the detail .md file must already exist (passed by caller). write_atom does not create it.
7. Update `index.json`: add entry to `atoms` dict: `{ "content": atom_dict["content"], "type": atom_dict["type"], "tags": atom_dict["tags"], "strength": atom_dict["strength"] }`. Increment `meta.total_atoms`.
8. Update `memory/index/tag_index.json`: for each tag in atom_dict["tags"], append the atom ID to that tag's list. Create the list if the tag is new.
9. Update `memory/index/type_index.json`: append atom ID to the list for atom_dict["type"].
10. Update `memory/index/graph.json`: add entry for this atom ID using atom_dict["edges"].
11. Return the atom ID string.

**Full atom dict structure that write_atom expects:**

```python
{
  "type": "preference",          # preference | fix | pattern | constraint | fact | correction
  "content": "short summary",    # always 1-2 sentences max
  "content_path": None,          # or "memory/detail/mem_NNN.md" if detail file exists
  "tags": ["python", "async"],   # list of strings
  "strength": 0.9,               # float 0.0 to 1.0
  "source_task": "task input",   # the input that generated this memory, truncated to 100 chars
  "edges": {
    "supports": [],
    "contradicts": [],
    "learned_from": "",
    "belongs_to": [],
    "occurred_in": [],
    "fixed_by": [],
    "generalizes": []
  }
}
```

All fields required. If caller does not provide edges, default to empty lists and empty strings.

### 2.2 — ops/read.py

**Purpose:** Given a list of atom IDs, return their content as a single formatted plain text string ready to be injected into context.

**Usage:**
```python
from ops.read import read_atoms
text = read_atoms(["mem_001", "mem_047"])
```

**What read_atoms(id_list) does:**

1. For each ID in id_list:
   a. Load `memory/atoms/{id}.json`
   b. If `content_path` is not null, load that .md file and use its content as the body
   c. Otherwise use the `content` field as the body
   d. Update `last_accessed` field in the atom JSON to today's date and resave
2. Format all loaded atoms as:
```
[mem_001 | preference | python, async | strength: 0.9]
prefers asyncio.gather over sequential awaits

[mem_047 | fix | python, async | strength: 0.85]
sequential awaits caused blocking bug in the AI project.
Fix: replace sequential awaits with asyncio.gather.
```
3. Return that formatted string.

If an ID does not exist on disk, skip it silently.

### 2.3 — ops/search.py (internal module, not the CLI entry point)

**Purpose:** Given a list of query keywords, score every atom by how many keywords it matches. Return only atoms that match the most keywords. This is the precision filter that ensures even if 1 million atoms are tagged "python", only the 3 that also match "async" and "blocking" reach the LLM.

**Usage:**
```python
from ops.search import keyword_search
candidates = keyword_search(["async", "python", "blocking"])
# returns {"mem_001": 3, "mem_047": 3, "mem_089": 1}
# mem_001 and mem_047 matched all 3 keywords
# mem_089 only matched 1
```

**What keyword_search(keywords) does — step by step:**

1. Load `memory/index/tag_index.json`. Load `index.json`.

2. For each keyword in the keywords list:
   - Look up its atom ID list in tag_index.json (exact match, case insensitive)
   - For each atom ID found, increment its score by 1
   - Also scan the `content` field of every atom in index.json["atoms"] for this keyword (case insensitive substring match). If found and not already counted from the tag index, increment score by 1.

3. After processing all keywords, apply the **intersection filter**:
   - Find the maximum score achieved by any atom (max_score)
   - Keep only atoms whose score equals max_score
   - If max_score is 1 (no atom matched more than 1 keyword), keep all atoms that scored 1, but cap the list at 30 atoms sorted by score
   - If max_score is 2+, keep ONLY atoms that scored max_score. Discard everything lower.

   **Why this matters:** If the query is "async python blocking" and 50,000 atoms have tag "python" (score 1) but only 3 atoms have tags "python" + "async" + "blocking" (score 3), the filter discards all 50,000 score-1 atoms and returns only the 3 atoms that matched everything. The LLM never sees the noise.

4. Return the filtered dict of atom_id -> score, already sorted by score descending.

**The rule is: always pass the highest-intersection atoms to the LLM, never the full keyword pool.**

### 2.4 — ops/consolidate.py (internal module, not CLI)

**Purpose:** Given task input and task output, call the consolidator agent and return either a new atom dict or None.

**Usage:**
```python
from ops.consolidate import consolidate
atom_dict = consolidate(task_input, task_output)
# returns atom dict or None
```

This just calls `api/agents/consolidator.py` and returns its result. It is a thin wrapper.

---

## Phase 3 — api/ Files

These files contain all Claude API calls. No file reads or writes happen here. They take strings in and return strings or dicts out.

### 3.1 — api/claude.py

**Purpose:** Single function that calls the Claude API using urllib.request. No SDK.

```python
def call_claude(system_prompt: str, user_message: str, max_tokens: int = 500) -> str:
```

**What it does:**

1. Read ANTHROPIC_API_KEY from csara/.env file. Parse the file line by line, find the line starting with ANTHROPIC_API_KEY=, extract the value after =.
2. Build the request body:
```python
body = {
    "model": "claude-sonnet-4-20250514",
    "max_tokens": max_tokens,
    "system": system_prompt,
    "messages": [{"role": "user", "content": user_message}]
}
```
3. Make POST request to `https://api.anthropic.com/v1/messages` with headers:
   - `Content-Type: application/json`
   - `x-api-key: {key}`
   - `anthropic-version: 2023-06-01`
4. Parse response JSON. Return `response["content"][0]["text"]` as a string.
5. If any error (network, API, missing key), print the error to stderr and return empty string "".

### 3.2 — api/agents/retrieval.py

**Purpose:** Given a search query and the pre-filtered high-intersection candidates from keyword_search, make the final relevance decision using Claude. This is the precision layer on top of the intersection filter.

```python
def get_relevant_atoms(query: str, index_content: dict, keyword_hits: dict) -> list:
    # keyword_hits already contains ONLY the highest-intersection atoms
    # returns final list of atom IDs, max 8
```

**What it does:**

1. keyword_hits at this point contains only atoms that matched the maximum number of query keywords. If keyword_search did its job, this is already a small, high-precision list (often 3-10 atoms, rarely more than 20).

2. Build the candidate list from keyword_hits. For each atom ID, pull its summary from index_content["atoms"]: id, content, type, tags. Cap at 20 candidates maximum.

3. Call call_claude() with:

**System prompt:**
```
You are a memory retrieval agent for a personal AI assistant.
Your job is to select which memory atoms are actually relevant to the user's query.
These candidates have already been pre-filtered by keyword intersection — they are the closest keyword matches.
Your job is final relevance ranking, not broad filtering.
Return ONLY a JSON array of atom IDs. No explanation. No markdown. Just the array.
Example: ["mem_001", "mem_047"]
If nothing is truly relevant, return: []
Return at most 8 atoms. Fewer is better. Only return atoms that genuinely help with the query.
```

**User message:**
```
Query: {query}

Candidates (pre-filtered by keyword intersection):
{compact list: id | type | tags | content}

Which of these are genuinely relevant to this query?
```

4. Parse the returned JSON array. Return as Python list.
5. If Claude returns empty string or invalid JSON, fall back to returning all IDs from keyword_hits sorted by score, capped at 8.

**Also handle skills — no LLM needed:**

```python
def get_relevant_skills(query: str, index_content: dict) -> list:
    # returns list of skill names to load, e.g. ["python"]
```

For each skill in index_content["skills"], count how many trigger_keywords appear in the query string (case insensitive). Return skill names where at least 1 keyword matched, sorted by match count descending. No Claude call. Pure string matching.

### 3.3 — api/agents/consolidator.py

**Purpose:** Given task input and output, decide if anything is worth storing as a new atom.

```python
def consolidate(task_input: str, task_output: str) -> dict | None:
    # returns atom dict ready for write_atom(), or None
```

**What it does:**

Call call_claude() with:

**System prompt:**
```
You are a memory consolidation agent for a personal AI assistant.
Your job is to extract ONE piece of information worth storing permanently from a completed task.

Store ONLY if you find one of these:
1. A user preference or way of doing things
2. A bug/error and the fix that worked
3. A reusable pattern discovered
4. A hard constraint or limitation found (API limits, system rules, etc.)
5. An explicit user correction

If none of these are present, return: null

If you find something, return a JSON object with exactly these fields:
{
  "type": "preference" or "fix" or "pattern" or "constraint" or "correction",
  "content": "one or two sentence summary, plain language",
  "content_path": null,
  "tags": ["tag1", "tag2"],
  "strength": 0.9,
  "source_task": "first 100 chars of task input",
  "edges": {
    "supports": [],
    "contradicts": [],
    "learned_from": "",
    "belongs_to": [],
    "occurred_in": [],
    "fixed_by": [],
    "generalizes": []
  }
}

Return ONLY the JSON object or the word null. No explanation. No markdown code fences.
```

**User message:**
```
Task input: {task_input}

Task output: {task_output}

Extract memory or return null.
```

Parse the response:
- If response is "null" or empty string, return None
- Otherwise parse as JSON and return the dict
- If JSON parse fails, return None

---

## Phase 4 — CLI Entry Points

These are the only files Copilot ever calls directly.

### 4.1 — csara/search.py (CLI entry point)

**Usage:**
```
python csara/search.py --q "async python debug"
python csara/search.py --q "notion api pagination"
```

**What it does step by step:**

1. Parse --q argument with argparse.

2. Split the query into keywords: lowercase, split by spaces, strip punctuation. Filter out stop words: ["the", "a", "an", "is", "it", "to", "of", "in", "for", "and", "or", "how", "what", "why", "i", "my", "we", "this", "that"].

3. Call `keyword_search(keywords)` from ops/search.py. This returns ONLY the atoms with the highest keyword intersection score. If the query has 3 keywords and some atoms match all 3, only those atoms come back. Atoms matching fewer keywords are discarded at this stage.

4. Load index.json.

5. Call `get_relevant_skills(query, index_content)` from api/agents/retrieval.py. Get list of relevant skill names.

6. If keyword_hits is not empty, call `get_relevant_atoms(query, index_content, keyword_hits)` from api/agents/retrieval.py. Claude does final precision ranking on the already-filtered candidates. Get final atom ID list.

7. Call `read_atoms(atom_id_list)` from ops/read.py. Get formatted atom text.

8. For each relevant skill name, load the skill layers:
   - Always load core.md
   - Load failures.md if any of these words appear in the original query: "debug", "error", "fix", "bug", "traceback", "exception", "broken", "wrong", "issue", "fail"
   - Load edge_cases.md if the query contains more than 8 words (rough complexity signal)

9. Print to stdout:

```
=== CSara Memory ===

[MEMORY]
{atom text, or "No relevant memory found." if empty}

[SKILL: python]
{content of core.md}

{content of failures.md if loaded}
===================
```

If no atoms and no skills matched at all, print:
```
=== CSara Memory ===
No relevant memory or skills found for this query.
===================
```

### 4.2 — csara/store.py (CLI entry point)

**Usage:**
```
python csara/store.py --input "fix the async blocking issue" --output "replaced sequential awaits with asyncio.gather, fixed the blocking"
python csara/store.py --forget mem_001
```

**What it does for --input/--output:**

1. Parse --input and --output arguments.
2. Call `consolidate(task_input, task_output)` from ops/consolidate.py.
3. If result is None: print `CSara: nothing worth storing.` and exit.
4. If result is a dict: call `write_atom(result)` from ops/write.py.
5. Print `CSara: stored as {atom_id}.` and exit.

**What it does for --forget:**

1. Parse --forget with the atom ID.
2. Load `memory/atoms/{id}.json`. If it does not exist, print `CSara: {id} not found.` and exit.
3. Delete `memory/atoms/{id}.json`.
4. If the atom had a content_path, delete that file too if it exists.
5. Remove the atom ID from index.json atoms dict.
6. Remove the atom ID from all lists in tag_index.json.
7. Remove the atom ID from all lists in type_index.json.
8. Remove the atom ID entry from graph.json. Also scan all other atom entries in graph.json and remove this ID from any lists it appears in.
9. Decrement index.json meta.total_atoms by 1.
10. Print `CSara: forgot {id}.` and exit.

---

## Phase 5 — Skill Self-Update

Skills grow automatically when store.py stores a new memory.

In store.py, after write_atom() succeeds, run this additional step:

1. Check if the new atom's tags include any skill trigger keywords (compare atom tags against each skill's trigger_keywords in index.json).
2. If a skill matches and the atom type is "fix" or "correction":
   - Append to `skills/{skill_name}/failures.md`:
   ```
   ## {today's date}
   {atom content}
   {content of content_path .md file if exists, otherwise empty}
   ```
3. If a skill matches and the atom type is "pattern":
   - Append to `skills/{skill_name}/core.md`:
   ```
   - {atom content}
   ```

This means failures.md and core.md grow automatically from real usage without any extra work.

---

## Phase 6 — Wiring Everything Together

### 6.1 — How all the modules import each other

All imports use paths relative to the csara/ directory.
When Copilot runs `python csara/search.py`, Python's working directory is the project root.
All files in csara/ add `csara/` prefix to their internal imports using sys.path.

At the top of every file inside csara/:
```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
```

This means `from ops.write import write_atom` works correctly regardless of where the user runs the command from.

### 6.2 — All file paths inside the code

Every file path used inside CSara must be built relative to the csara/ directory, not the working directory.

Define this constant in every file that touches disk:
```python
CSARA_DIR = os.path.dirname(os.path.abspath(__file__))
```

Then build all paths like:
```python
index_path = os.path.join(CSARA_DIR, "index.json")
atoms_dir = os.path.join(CSARA_DIR, "memory", "atoms")
```

This ensures it works whether Copilot runs `python csara/search.py` from the project root or from anywhere else.

---

## Phase 7 — Testing Checklist

Run these commands in order after building. Each must work before moving to the next.

```bash
# Step 1 — Initialize
python csara/init.py
# Expected: folders created, seed files written, .env created

# Step 2 — Verify folder structure
ls csara/memory/atoms csara/memory/index csara/skills/python csara/ops csara/api/agents
# Expected: all folders exist

# Step 3 — Store a first memory manually
python csara/store.py --input "how to handle concurrent api calls in python" --output "used asyncio.gather instead of sequential awaits, resolved the blocking issue completely"
# Expected: CSara: stored as mem_001.

# Step 4 — Verify the atom was written
cat csara/memory/atoms/mem_001.json
# Expected: valid JSON with type, content, tags, edges, strength

# Step 5 — Verify indexes were updated
cat csara/memory/index/tag_index.json
# Expected: tags from mem_001 appear as keys with ["mem_001"] as value

# Step 6 — Search for the memory
python csara/search.py --q "async python concurrent"
# Expected: CSara Memory section prints, mem_001 content appears, python skill core.md appears

# Step 7 — Store a second memory
python csara/store.py --input "ran into notion api pagination issue" --output "notion api returns max 100 items per page, need to use the next_cursor field to paginate through all results"
# Expected: CSara: stored as mem_002.

# Step 8 — Search with unrelated query that should not match
python csara/search.py --q "weather in paris"
# Expected: No relevant memory or skills found.

# Step 9 — Forget a memory
python csara/store.py --forget mem_001
# Expected: CSara: forgot mem_001.

# Step 10 — Verify it is gone
python csara/search.py --q "async python"
# Expected: mem_001 no longer appears in output
```

---

## Environment Setup

The user will add the Claude API key to csara/.env after init.py runs.
Format is exactly: `ANTHROPIC_API_KEY=sk-ant-api03-...`

The model used for all API calls: `claude-sonnet-4-20250514`

api/claude.py reads the .env file by opening it and parsing lines. No dotenv library.

---

## What NOT to Build in This Phase

Do not build:
- ops/decay.py — not needed for prototype
- api/agents/classifier.py — consolidator handles classification for now
- api/agents/arbiter.py — no conflict resolution in prototype
- clarification scripts (mm45.py through mm49.py) — not needed for prototype
- interfaces/mcp_server.py — CLI only for now
- interfaces/rest_api.py — CLI only for now
- install.sh — not needed, just git clone and run init.py

These are Phase 3+ work. Build only what is listed in this plan.

---

## Summary of Files to Create

```
csara/init.py                        create everything
csara/search.py                      CLI: search memory
csara/store.py                       CLI: store or forget memory
csara/boot.md                        created by init.py
csara/index.json                     created by init.py
csara/.env                           created by init.py (empty key)
csara/memory/atoms/                  folder, created by init.py
csara/memory/detail/                 folder, created by init.py
csara/memory/index/graph.json        created by init.py
csara/memory/index/tag_index.json    created by init.py
csara/memory/index/type_index.json   created by init.py
csara/memory/working/                folder, created by init.py
csara/skills/python/meta.json        created by init.py
csara/skills/python/core.md          created by init.py
csara/skills/python/failures.md      created by init.py (empty)
csara/skills/python/edge_cases.md    created by init.py (empty)
csara/ops/__init__.py                empty
csara/ops/write.py                   write and index atoms
csara/ops/read.py                    load atoms by ID list
csara/ops/search.py                  keyword search, no LLM
csara/ops/consolidate.py             thin wrapper to consolidator agent
csara/api/__init__.py                empty
csara/api/claude.py                  raw urllib.request API call
csara/api/agents/__init__.py         empty
csara/api/agents/retrieval.py        LLM-powered relevance ranking
csara/api/agents/consolidator.py     LLM-powered signal extraction
```

Total: 22 files. Build them in this order:
1. init.py (creates structure)
2. api/claude.py (everything else depends on this)
3. ops/write.py
4. ops/read.py
5. ops/search.py
6. ops/consolidate.py + api/agents/consolidator.py
7. api/agents/retrieval.py
8. search.py (CLI)
9. store.py (CLI)
10. Run Phase 7 testing checklist