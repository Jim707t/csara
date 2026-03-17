# CSara — Context Storage & Agent Retrieval Architecture

A persistent memory system for GitHub Copilot. Stores what you build, what you fix, and how you work. Retrieves relevant context automatically before every task so Copilot never starts from zero.

---

## How it works

CSara exposes two MCP tools that Copilot calls automatically:

- **csara_search** — called before a task. Returns relevant past memories and skill knowledge.
- **csara_store** — called after a task. Consolidates what was done into a memory atom.

Memory is stored as plain JSON files on disk. Skills are Markdown files. Nothing leaves your machine except Claude API calls for consolidation.

---

## Requirements

- Python 3.10 or higher
- A Claude API key (Anthropic) — [get one here](https://console.anthropic.com/)
- VS Code with GitHub Copilot

---

## Setup

### 1. Clone the repo

```
git clone https://github.com/Jim707t/csara.git
cd csara
```

### 2. Create the virtual environment and install the MCP SDK

```
python -m venv csara/.venv
csara\.venv\Scripts\activate       # Windows
# source csara/.venv/bin/activate  # macOS/Linux

pip install "mcp[cli]"
```

The MCP SDK is the only dependency. All CSara core logic uses Python stdlib only.

### 3. Add your API key

```
copy csara\.env.example csara\.env
```

Open `csara/.env` and fill in your key:

```
ANTHROPIC_API_KEY=sk-ant-...
```

### 4. Initialize the folder structure

```
python csara/init.py
```

This creates the empty `memory/` and `skills/` folders that git does not track.

### 5. Configure VS Code to load the MCP server globally

Open the VS Code user-level MCP config. Run from the Command Palette:

```
MCP: Open User Configuration
```

This opens `%APPDATA%\Code\User\mcp.json` (Windows) or `~/.config/Code/User/mcp.json` (Linux/macOS). Add the CSara server using the **absolute path** to your cloned folder:

```json
{
  "servers": {
    "csara": {
      "command": "/absolute/path/to/csara/.venv/bin/python",
      "args": ["/absolute/path/to/csara/mcp_server.py"]
    }
  }
}
```

On Windows use double backslashes or forward slashes:

```json
{
  "servers": {
    "csara": {
      "command": "C:/path/to/csara/csara/.venv/Scripts/python.exe",
      "args": ["C:/path/to/csara/csara/mcp_server.py"]
    }
  }
}
```

### 6. Reload VS Code

After saving `mcp.json`, reload the window (`Ctrl+Shift+P` → Reload Window). VS Code will prompt you to trust the CSara server — accept it.

### 7. Tell Copilot to use CSara in every workspace

The MCP server is global — the tools are available in every workspace. But Copilot won't call them automatically unless it has instructions to do so.

Create this file once and it covers every workspace on your machine:

**Windows:** `C:\Users\<you>\.copilot\instructions\csara.instructions.md`
**macOS/Linux:** `~/.copilot/instructions/csara.instructions.md`

Contents:

```markdown
---
name: 'CSara Memory System'
description: 'Persistent memory system — search before tasks, store after tasks'
applyTo: '**'
---

You have access to CSara memory tools (csara_search, csara_store, csara_forget, csara_list_skills). Use them on every task without being asked. Before starting any task, call csara_search with a brief description of what you are about to do. After completing any task, call csara_store with what was asked (task_input) and what you produced (task_output). Keep both under 3 sentences, be specific. Never skip either step. If csara_search returns nothing, proceed normally and still call csara_store after. Do not summarize CSara output, inject it as-is into your context.
```

You do not need to copy anything into individual projects. This one file is enough.

---

## CLI usage (alternative / debugging)

You can also call CSara directly from the terminal without the MCP setup:

```bash
# Search before a task
python csara/search.py --q "async python pattern"

# Store after a task
python csara/store.py --input "what you were asked" --output "what you built or fixed"

# Forget a memory
python csara/store.py --forget mem_001

# List skills
python csara/store.py --list-skills

# Delete a skill
python csara/store.py --forget-skill python

# Add --debug to any command for a full internal trace
python csara/search.py --q "your query" --debug
```

---

Your memories and skills are personal and stay on your machine — they are gitignored. The repo contains only the engine.
