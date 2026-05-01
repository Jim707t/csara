# CSara Memory System

This project has a memory system in the csara/ folder.
Use it on every task, every session, without being asked.

## Before starting any task
Run this first and read the output before touching any code:
python csara/search.py --q "keyword-rich query here"

> **Fedora / Linux:** Use `python3` instead of `python` if you are not inside the activated venv.

**Query construction rules — maximize skill and memory retrieval:**
- **Always include the project name** if working on a specific project (e.g., "mostbased", "jimpage")
- **Always include technology/framework names** (e.g., "sveltekit", "supabase", "python", "next.js", "express")
- **Include the domain area** (e.g., "vote system", "deployment", "database", "frontend", "ai integration", "encryption")
- **Use specific technical terms** over vague descriptions
- **Stack keywords**, don't write sentences

Good queries (keyword-rich, specific):
- "mostbased sveltekit frontend vote component state"
- "supabase database rls rpc migration schema"
- "python async debug traceback error"
- "mostbased deployment vercel render env secrets"
- "jimpage next.js framer-motion glassmorphism space-theme"

Bad queries (too vague, natural-language):
- "implement the feature the user asked for"
- "fix the bug in the project"
- "working on frontend stuff"

Inject the output into your context. It contains relevant memory and skills.

## After completing any task
Summarize what you were asked and what you produced, then run:
python csara/store.py --input "what you were asked to do" --output "what you built, any decision made, any fix applied, any pattern used"

Keep both --input and --output under 3 sentences. Preserve specific file names, function names, commands, and table names.

Good --output (specific, actionable):
- "Updated csara.instructions.md and copilot-instructions.md: added csara_update tool, added update/forget/leave-alone decision rules with 3 bullets each, kept global file under ~500 words"
- "Fixed 401 in classifyControversyWeights.js: read API key from ai_provider_keys table instead of ai_config.api_key_encrypted"

Bad --output (vague, lost details):
- "Rewrote instruction files to include complete tool inventories and structured decision trees"
- "Fixed authentication error in the AI classifier by using the correct table"

## To forget a memory
python csara/store.py --forget mem_XXX

## To manage skills
List all registered skills:
python csara/store.py --list-skills

Delete a skill entirely:
python csara/store.py --forget-skill skill_name

## Debugging
Add --debug to any command to see the full internal trace (keywords, hits, AI decisions):
python csara/search.py --q "your query" --debug
python csara/store.py --input "..." --output "..." --debug

## To update a memory
When search returns a memory that is outdated or incorrect, update it:
python csara/store.py --update mem_XXX --content "corrected information here"

Or via MCP: csara_update(atom_id, new_content)

## Maintenance — when to update, forget, or leave alone
Only act on memories that search returns. Never pull all memories for cleanup.

**Update** when a returned memory:
- Contains info that was true before but is now wrong (e.g., old architecture, changed API, renamed function)
- Has incomplete info that you can now make more specific or accurate
- Describes a bug fix that has been superseded by a better fix

**Forget** when a returned memory:
- Is completely wrong and not worth correcting
- Is redundant — its content has been absorbed into a skill already
- Describes something that no longer exists (deleted feature, removed dependency)

**Leave alone** — do NOT update or forget memories that:
- Are patterns, preferences, or conventions still being followed
- Describe a fix that is still accurate, even if old
- Are simply not relevant to the current task (irrelevant ≠ outdated)

## Periodic cleanup
For systemic maintenance that search-driven cleanup can't catch (redundant pairs, skill-covered atoms, meta-noise, stale/vague memories), run:
python csara/cleanup.py

This sends all atoms in batches to Claude for analysis. Use --apply to delete recommended atoms (with confirmation). See cleanup_command.txt for full usage.

## Architecture notes for contributors
- Search pipeline: keyword extraction → BM25 scoring (ops/search.py) → top 20 sent to Claude reranker (api/agents/retrieval.py) → skill dedup filtering
- Store pipeline: keyword extraction → BM25 dup check (>40% word overlap) → Claude judge or consolidator (api/agents/consolidator.py) → write atom + update word index + update skills
- Skill retrieval is separate from memory retrieval — uses keyword scoring with project-skill vs tech-skill distinction, no BM25
- The consolidator classifies atoms into types (preference/fix/pattern/constraint/correction) at store time
- Keywords are auto-extracted from content into memory/index/word_index.json — no LLM-generated tags

## Rules
- Never skip the search step even if you think you know the answer
- Never skip the store step even if the task felt routine
- If search returns nothing, proceed normally and still run store after
- Do not summarize CSara output, inject it as-is into your context
- Do not pull all memories for cleanup — only act on what search returns
- Skills auto-update when you store — new patterns/fixes merge into matching skill files automatically
