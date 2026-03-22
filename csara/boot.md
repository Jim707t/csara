# CSara Memory System

Before any task: python csara/search.py --q "keyword-rich query here"
After any task:  python csara/store.py --input "what you were asked" --output "what you produced"
Forget a memory: python csara/store.py --forget mem_001
Update a memory: python csara/store.py --update mem_001 --content "corrected info"

Query tips: always include project name + technology names. Stack keywords, don't write sentences.
Good: "mostbased sveltekit frontend vote component"  Bad: "fix the bug in the project"

Output from search.py is plain text. Inject it into your context before working.
