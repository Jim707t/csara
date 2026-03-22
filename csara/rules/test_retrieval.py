"""
CSara Search Retrieval Test Suite
Tests that search returns the RIGHT memories and skills for diverse scenarios.
Each test case defines: query, expected_memories (must ALL appear), expected_skills (must ALL appear),
and forbidden_memories/forbidden_skills (must NOT appear).

Run: python -m pytest csara/rules/test_retrieval.py -v
"""

import sys
import os
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from search import _extract_keywords, _do_search
from ops.search import keyword_search
from api.agents.retrieval import get_relevant_skills

CSARA_DIR = os.path.join(os.path.dirname(__file__), "..")


def _load_index():
    path = os.path.join(CSARA_DIR, "index.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _get_search_results(query: str) -> dict:
    """Run search pipeline and return structured results."""
    keywords = _extract_keywords(query)
    if not keywords:
        return {"memories": [], "skills": []}

    index = _load_index()

    # Get skills
    skills = get_relevant_skills(query, index)

    # Get memory hits
    from ops.search import keyword_search
    hits = keyword_search(keywords)

    # For baseline: return raw keyword hits (top 15) without Claude rerank
    sorted_ids = sorted(hits.keys(), key=lambda x: hits[x], reverse=True)[:15]

    return {
        "memories": sorted_ids,
        "skills": skills,
        "keyword_hits": hits,
    }


# ============================================================
# TEST SCENARIOS — 30 diverse agent task scenarios
# ============================================================

SCENARIOS = [
    {
        "id": 1,
        "name": "mostbased_vote_system_bug",
        "query": "mostbased vote system insert_vote_v2 bug fix",
        "expected_skills": ["mostbased-vote-system", "mostbased-core"],
        "expected_memories": [],  # vote-specific memories
        "forbidden_skills": ["jimpage", "python"],
    },
    {
        "id": 2,
        "name": "jimpage_add_new_section",
        "query": "jimpage add new section glassmorphism framer-motion animation",
        "expected_skills": ["jimpage"],
        "expected_memories": ["mem_008", "mem_009", "mem_010", "mem_011"],
        "forbidden_skills": ["mostbased-core", "mostbased-database"],
    },
    {
        "id": 3,
        "name": "python_async_error",
        "query": "python asyncio event loop error debug",
        "expected_skills": ["python"],
        "expected_memories": ["mem_018"],
        "forbidden_skills": ["jimpage", "mostbased-vote-system"],
    },
    {
        "id": 4,
        "name": "supabase_rls_migration",
        "query": "supabase database rls rpc migration schema",
        "expected_skills": ["mostbased-database"],
        "expected_memories": ["mem_004"],  # SQLite WAL is DB-related but different
        "forbidden_skills": ["jimpage", "python"],
    },
    {
        "id": 5,
        "name": "mostbased_deployment_env",
        "query": "mostbased deployment vercel render env secrets production",
        "expected_skills": ["mostbased-deployment", "mostbased-core"],
        "expected_memories": [],
        "forbidden_skills": ["jimpage"],
    },
    {
        "id": 6,
        "name": "javascript_node_express_api",
        "query": "javascript node express api endpoint async",
        "expected_skills": ["javascript"],
        "expected_memories": [],
        "forbidden_skills": ["jimpage"],
    },
    {
        "id": 7,
        "name": "svelte_frontend_component",
        "query": "sveltekit svelte component state store feedCache",
        "expected_skills": ["mostbased-frontend"],
        "expected_memories": [],
        "forbidden_skills": ["jimpage", "python"],
    },
    {
        "id": 8,
        "name": "gtk4_windows_portable",
        "query": "gtk4 windows portable msys2 deployment dll",
        "expected_skills": [],
        "expected_memories": ["mem_014", "mem_015", "mem_016"],
        "forbidden_skills": ["mostbased-core", "jimpage"],
    },
    {
        "id": 9,
        "name": "ai_article_generation",
        "query": "mostbased ai openai gemini anthropic article generation provider",
        "expected_skills": ["mostbased-ai-integration"],
        "expected_memories": ["mem_058"],
        "forbidden_skills": ["jimpage"],
    },
    {
        "id": 10,
        "name": "python_naming_conventions",
        "query": "python naming conventions snake_case coding style",
        "expected_skills": ["python"],
        "expected_memories": ["mem_003"],
        "forbidden_skills": ["jimpage"],
    },
    {
        "id": 11,
        "name": "powershell_line_counting",
        "query": "powershell count lines file measure",
        "expected_skills": [],
        "expected_memories": ["mem_022", "mem_023"],
        "forbidden_skills": ["jimpage", "mostbased-core"],
    },
    {
        "id": 12,
        "name": "mostbased_metrics_controversy",
        "query": "mostbased controversy score metrics weighted formula",
        "expected_skills": ["mostbased-core"],
        "expected_memories": ["mem_052"],
        "forbidden_skills": ["jimpage", "python"],
    },
    {
        "id": 13,
        "name": "mobile_responsive_css",
        "query": "mobile responsive overflow tailwind css fix hidden",
        "expected_skills": [],
        "expected_memories": ["mem_072", "mem_074", "mem_075"],
        "forbidden_skills": ["jimpage"],
    },
    {
        "id": 14,
        "name": "mcp_server_development",
        "query": "mcp fastmcp server tool python stringio import",
        "expected_skills": ["python"],
        "expected_memories": ["mem_007"],
        "forbidden_skills": ["jimpage"],
    },
    {
        "id": 15,
        "name": "svelte_scroll_restoration",
        "query": "svelte scroll position restoration cache bug fix",
        "expected_skills": ["mostbased-frontend"],
        "expected_memories": ["mem_045", "mem_067"],
        "forbidden_skills": ["jimpage", "python"],
    },
    {
        "id": 16,
        "name": "supabase_cookie_credentials",
        "query": "supabase cookie credentials fix __cf_bm console warning",
        "expected_skills": ["mostbased-database"],
        "expected_memories": ["mem_081"],
        "forbidden_skills": ["jimpage"],
    },
    {
        "id": 17,
        "name": "admin_dashboard_design",
        "query": "admin dashboard metrics accordion super_admin role",
        "expected_skills": ["mostbased-core"],
        "expected_memories": ["mem_042", "mem_056"],
        "forbidden_skills": ["jimpage", "python"],
    },
    {
        "id": 18,
        "name": "tiktok_scraping_social",
        "query": "tiktok scraping social media data trending hashtags",
        "expected_skills": [],
        "expected_memories": ["mem_032"],
        "forbidden_skills": ["jimpage", "python"],
    },
    {
        "id": 19,
        "name": "seo_audit_og_tags",
        "query": "seo audit og tags robots sitemap svelte",
        "expected_skills": [],
        "expected_memories": ["mem_079", "mem_080"],
        "forbidden_skills": ["jimpage"],
    },
    {
        "id": 20,
        "name": "file_size_refactoring",
        "query": "file size lines refactoring best practices coding guidelines",
        "expected_skills": [],
        "expected_memories": ["mem_021"],
        "forbidden_skills": ["jimpage"],
    },
    {
        "id": 21,
        "name": "graceful_shutdown_worker",
        "query": "graceful shutdown worker signal handling background process",
        "expected_skills": [],
        "expected_memories": ["mem_005"],
        "forbidden_skills": ["jimpage", "mostbased-core"],
    },
    {
        "id": 22,
        "name": "config_env_validation",
        "query": "configuration environment variables fail fast startup validation",
        "expected_skills": [],
        "expected_memories": ["mem_006"],
        "forbidden_skills": ["jimpage"],
    },
    {
        "id": 23,
        "name": "innovation_scoring_system",
        "query": "mostbased innovation scoring milestones creative output field influence wikidata openalex",
        "expected_skills": ["mostbased-core"],
        "expected_memories": ["mem_037"],
        "forbidden_skills": ["jimpage", "python"],
    },
    {
        "id": 24,
        "name": "nextjs_pages_router_typescript",
        "query": "next.js pages router typescript tailwind project",
        "expected_skills": ["jimpage"],
        "expected_memories": ["mem_008"],
        "forbidden_skills": ["mostbased-core"],
    },
    {
        "id": 25,
        "name": "sqlite_concurrent_locking",
        "query": "sqlite database locking concurrent reads wal journal",
        "expected_skills": [],
        "expected_memories": ["mem_004"],
        "forbidden_skills": ["jimpage"],
    },
    {
        "id": 26,
        "name": "csara_memory_system_itself",
        "query": "csara memory search keyword index retrieval atom",
        "expected_skills": [],
        "expected_memories": ["mem_027", "mem_041", "mem_060"],
        "forbidden_skills": ["jimpage"],
    },
    {
        "id": 27,
        "name": "mostbased_cron_auth",
        "query": "mostbased cron authentication secret header middleware",
        "expected_skills": ["mostbased-deployment", "mostbased-core"],
        "expected_memories": ["mem_038", "mem_053"],
        "forbidden_skills": ["jimpage", "python"],
    },
    {
        "id": 28,
        "name": "svelte5_reactivity_bug",
        "query": "svelte 5 legacy mode deep object mutation bind reactivity bug",
        "expected_skills": ["mostbased-frontend"],
        "expected_memories": ["mem_085"],
        "forbidden_skills": ["jimpage", "python"],
    },
    {
        "id": 29,
        "name": "portable_offline_html_tool",
        "query": "self-contained html offline portable tool no dependencies",
        "expected_skills": [],
        "expected_memories": ["mem_013"],
        "forbidden_skills": ["mostbased-core", "jimpage"],
    },
    {
        "id": 30,
        "name": "ga4_analytics_sveltekit",
        "query": "google analytics ga4 sveltekit tracking route navigation",
        "expected_skills": ["mostbased-frontend"],
        "expected_memories": ["mem_039"],
        "forbidden_skills": ["jimpage", "python"],
    },
]


class TestSearchRetrieval:
    """Test that search retrieves correct memories and skills for each scenario."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.index = _load_index()

    @pytest.mark.parametrize("scenario", SCENARIOS, ids=[s["name"] for s in SCENARIOS])
    def test_expected_skills_retrieved(self, scenario):
        """Every expected skill must be in the results."""
        results = _get_search_results(scenario["query"])
        for skill in scenario.get("expected_skills", []):
            assert skill in results["skills"], (
                f"Scenario '{scenario['name']}': expected skill '{skill}' not found. "
                f"Got skills: {results['skills']}"
            )

    @pytest.mark.parametrize("scenario", SCENARIOS, ids=[s["name"] for s in SCENARIOS])
    def test_forbidden_skills_not_retrieved(self, scenario):
        """Forbidden skills must NOT be in the results."""
        results = _get_search_results(scenario["query"])
        for skill in scenario.get("forbidden_skills", []):
            assert skill not in results["skills"], (
                f"Scenario '{scenario['name']}': forbidden skill '{skill}' was retrieved. "
                f"Got skills: {results['skills']}"
            )

    @pytest.mark.parametrize("scenario", SCENARIOS, ids=[s["name"] for s in SCENARIOS])
    def test_expected_memories_retrieved(self, scenario):
        """Every expected memory must be in the results."""
        results = _get_search_results(scenario["query"])
        for mem in scenario.get("expected_memories", []):
            assert mem in results["memories"], (
                f"Scenario '{scenario['name']}': expected memory '{mem}' not found. "
                f"Got memories: {results['memories']}"
            )


class TestKeywordExtraction:
    """Test keyword extraction produces meaningful keywords."""

    def test_stop_words_removed(self):
        kw = _extract_keywords("the quick brown fox is very fast")
        assert "the" not in kw
        assert "is" not in kw
        assert "very" not in kw
        assert "quick" in kw
        assert "brown" in kw

    def test_empty_query(self):
        kw = _extract_keywords("")
        assert kw == []

    def test_all_stop_words(self):
        kw = _extract_keywords("the is a an to of")
        assert kw == []

    def test_dedup(self):
        kw = _extract_keywords("python python python code code")
        assert kw.count("python") == 1
        assert kw.count("code") == 1

    def test_preserves_hyphens_as_words(self):
        kw = _extract_keywords("server-side rendering")
        # Should handle hyphenated words
        assert len(kw) > 0


class TestKeywordSearch:
    """Test the keyword_search function from ops/search.py."""

    def test_exact_match(self):
        hits = keyword_search(["python"])
        assert "mem_003" in hits  # snake_case preference mentions python
        assert len(hits) > 0

    def test_no_match(self):
        hits = keyword_search(["xyznonexistent123"])
        assert len(hits) == 0

    def test_multiple_keywords_boost(self):
        hits = keyword_search(["gtk4", "windows", "portable"])
        # mem_015 and mem_016 mention all three
        assert "mem_015" in hits or "mem_016" in hits

    def test_substring_matching(self):
        hits = keyword_search(["sveltekit"])
        assert len(hits) > 0

    def test_max_results_cap(self):
        # Even with broad keywords, should cap at 30
        hits = keyword_search(["file", "code", "error", "function"])
        assert len(hits) <= 30


class TestSkillRetrieval:
    """Test skill matching logic."""

    def _index(self):
        path = os.path.join(CSARA_DIR, "index.json")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_exact_keyword_match(self):
        skills = get_relevant_skills("python script debug", self._index())
        assert "python" in skills

    def test_project_name_match(self):
        skills = get_relevant_skills("mostbased frontend component", self._index())
        assert "mostbased-frontend" in skills or "mostbased-core" in skills

    def test_no_false_positive_jimpage(self):
        skills = get_relevant_skills("python async error fix", self._index())
        assert "jimpage" not in skills

    def test_multiword_keyword(self):
        skills = get_relevant_skills("jim nemorin personal website", self._index())
        assert "jimpage" in skills

    def test_empty_query(self):
        skills = get_relevant_skills("", self._index())
        assert skills == []


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
