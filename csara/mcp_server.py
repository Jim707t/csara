"""CSara MCP Server — exposes search/store as tools for VS Code Copilot."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP
from search import run_search
from store import run_store, run_forget, run_forget_skill, run_list_skills

mcp = FastMCP("csara")


@mcp.tool()
def csara_search(query: str) -> str:
    """Search CSara memory for relevant memories and skills before starting any task.
    Call this BEFORE you begin working on something, with a brief description of
    what you are about to do. Returns relevant past memories and skill knowledge.

    Args:
        query: Brief description of what you are about to do
    """
    return run_search(query)


@mcp.tool()
def csara_store(task_input: str, task_output: str) -> str:
    """Store a memory after completing any task. Summarize what was asked and
    what was produced. Keep both arguments under 3 sentences. Be specific.

    Args:
        task_input: What you were asked to do (under 3 sentences, be specific)
        task_output: What you built, any decision made, fix applied, or pattern used (under 3 sentences)
    """
    return run_store(task_input, task_output)


@mcp.tool()
def csara_forget(atom_id: str) -> str:
    """Forget a specific memory atom by its ID.

    Args:
        atom_id: The memory atom ID to forget (e.g. mem_001)
    """
    return run_forget(atom_id)


@mcp.tool()
def csara_forget_skill(skill_name: str) -> str:
    """Delete a skill entirely from CSara.

    Args:
        skill_name: The name of the skill to delete (e.g. python, javascript)
    """
    return run_forget_skill(skill_name)


@mcp.tool()
def csara_list_skills() -> str:
    """List all registered skills in CSara."""
    return run_list_skills()


if __name__ == "__main__":
    mcp.run(transport="stdio")
