# CSara Development Rules

## R1: File Size Limits
- Max 300 lines per Python file. Refactor at 250+.
- Max 50 files per folder. Split into subfolders at 40+.
- memory/atoms/ and skills/ are exempt (auto-managed).

## R2: Claude API Usage
- Claude is ONLY for tasks requiring intelligence: consolidation, deduplication judging, skill file merging.
- Search/retrieval MUST use pure code (BM25, keyword matching, scoring). No Claude calls during search except final rerank on >5 candidates.
- Never call Claude for keyword extraction, tag generation, or index operations.

## R3: Testing
- Every public function must have a unit test.
- Search retrieval must pass 100% on the test scenario suite (25+ scenarios).
- Tests run without Claude API (mock API calls in tests).

## R4: Retrieval Quality
- Zero false negatives: every relevant memory/skill MUST be retrieved.
- Minimal noise: irrelevant items must NOT be retrieved.
- Skills matching uses keyword + summary overlap. Claude reranks when >3 skills match.
- Memory retrieval uses BM25 scoring with IDF weighting. Claude reranks when >5 atoms match.

## R5: Token Efficiency
- MCP tool descriptions must be concise (<100 words each).
- Search output must not exceed 4000 chars to avoid overwhelming agent context.
- Dedup atoms against skills before returning — never return content already in a skill.

## R6: Code Organization
- ops/ — pure data operations (no API calls)
- api/ — all Claude API interactions
- rules/ — project rules and test suites
- memory/ — data storage only
- skills/ — skill files only
- Root csara/ — entry points only (search.py, store.py, mcp_server.py, init.py)

## R7: Index Integrity
- word_index.json must index ALL text fields (content, source_task, detail).
- Tags from atoms must be indexed as keywords.
- Index updates must be atomic (write temp, rename).

## Compliance Checklist
Before any PR/commit, verify:
- [ ] No file exceeds 300 lines
- [ ] No folder exceeds 50 files (except memory/atoms and skills/)
- [ ] No Claude calls in search path (except rerank >5 atoms or >3 skills)
- [ ] All test scenarios pass at 100%
- [ ] All public functions have unit tests
