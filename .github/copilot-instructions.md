# CSara Memory System

This project has a memory system in the csara/ folder.
Use it on every task, every session, without being asked.

## Before starting any task
Run this first and read the output before touching any code:
python csara/search.py --q "brief description of what you are about to do"

Inject the output into your context. It contains relevant memory and skills.

## After completing any task
Summarize what you were asked and what you produced, then run:
python csara/store.py --input "what you were asked to do" --output "what you built, any decision made, any fix applied, any pattern used"

Keep both --input and --output under 3 sentences. Be specific, not generic.

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

## Rules
- Never skip the search step even if you think you know the answer
- Never skip the store step even if the task felt routine
- If search returns nothing, proceed normally and still run store after
- Do not summarize CSara output, inject it as-is into your context
