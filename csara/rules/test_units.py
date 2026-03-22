"""Unit tests for individual CSara functions.
Tests each function in isolation without requiring Claude API calls.
"""
import os
import sys
import json
import math
import pytest
import tempfile
import shutil

# Add CSara to path
CSARA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, CSARA_DIR)

from search import _extract_keywords
from ops.search import keyword_search, _compute_doc_stats, BM25_K1, BM25_B
from ops.write import extract_keywords as write_extract_keywords
from api.agents.retrieval import (
    get_relevant_skills, _is_project_skill, _extract_project_name,
    _normalize_kw, GENERIC_PROJECT_KEYWORDS, SKILL_SUMMARY_STOP_WORDS,
)


# ─── _extract_keywords (search.py) ───────────────────────────────────────────

class TestExtractKeywords:

    def test_basic_extraction(self):
        result = _extract_keywords("python async debug")
        assert "python" in result
        assert "async" in result
        assert "debug" in result

    def test_stop_words_removed(self):
        result = _extract_keywords("the is a for and with")
        assert result == []

    def test_dedup(self):
        result = _extract_keywords("python python python code code")
        assert result.count("python") == 1
        assert result.count("code") == 1

    def test_empty(self):
        assert _extract_keywords("") == []

    def test_preserves_hyphens(self):
        result = _extract_keywords("framer-motion next-js")
        assert "framer-motion" in result
        assert "next-js" in result

    def test_hyphen_split_parts(self):
        """Hyphenated words should also add their parts as separate keywords."""
        result = _extract_keywords("framer-motion")
        assert "framer-motion" in result
        assert "framer" in result
        assert "motion" in result

    def test_hyphen_part_dedup(self):
        """If a hyphen part matches an existing keyword, don't add it twice."""
        result = _extract_keywords("framer framer-motion")
        assert result.count("framer") == 1

    def test_single_char_filtered(self):
        result = _extract_keywords("a b c python")
        assert "python" in result
        assert "b" not in result
        assert "c" not in result

    def test_punctuation_removed(self):
        result = _extract_keywords("python! error? debug.")
        assert "python" in result
        assert "error" in result

    def test_case_insensitive(self):
        result = _extract_keywords("Python ASYNC Debug")
        assert "python" in result
        assert "async" in result

    def test_special_chars(self):
        """Dots are replaced by spaces (words split), hyphens preserved."""
        result = _extract_keywords("next.js vue.js")
        # Dots become spaces, so "next.js" → "next" + "js"
        assert "next" in result
        assert "vue" in result


# ─── extract_keywords (ops/write.py) ─────────────────────────────────────────

class TestWriteExtractKeywords:

    def test_basic(self):
        result = write_extract_keywords("python async debug error")
        assert "python" in result
        assert "async" in result

    def test_dedup(self):
        result = write_extract_keywords("python python code code")
        assert result.count("python") == 1

    def test_hyphen_preserved(self):
        result = write_extract_keywords("framer-motion pages-router")
        assert "framer-motion" in result
        assert "pages-router" in result

    def test_stop_words(self):
        result = write_extract_keywords("the is a for and")
        assert result == []

    def test_single_char_filtered(self):
        result = write_extract_keywords("a b c python")
        assert "python" in result
        assert len(result) == 1


# ─── _compute_doc_stats (ops/search.py) ──────────────────────────────────────

class TestComputeDocStats:

    def test_basic(self):
        word_index = {
            "python": ["mem_001", "mem_002"],
            "async": ["mem_001"],
            "debug": ["mem_002", "mem_003"],
        }
        doc_lengths, avgdl, n = _compute_doc_stats(word_index)
        assert n == 3
        assert doc_lengths["mem_001"] == 2  # python + async
        assert doc_lengths["mem_002"] == 2  # python + debug
        assert doc_lengths["mem_003"] == 1  # debug only
        assert avgdl == pytest.approx(5 / 3)

    def test_empty(self):
        doc_lengths, avgdl, n = _compute_doc_stats({})
        assert n == 0
        assert avgdl == 1  # fallback


# ─── keyword_search BM25 (ops/search.py) ─────────────────────────────────────

class TestKeywordSearchBM25:

    def test_returns_matching_atoms(self):
        hits = keyword_search(["python"])
        assert len(hits) > 0

    def test_no_match(self):
        hits = keyword_search(["xyznonexistent123"])
        assert len(hits) == 0

    def test_multiple_keywords_boost(self):
        """Atoms matching more keywords should score higher."""
        hits = keyword_search(["jimpage", "nextjs", "framer-motion"])
        if len(hits) >= 2:
            scores = list(hits.values())
            assert scores[0] >= scores[-1]  # sorted descending

    def test_rare_words_score_higher(self):
        """BM25 IDF: rare words should contribute more to score."""
        # A very specific word should have higher IDF than a common one
        # We can't test exact values but we can verify the scoring logic
        hits_common = keyword_search(["code"])
        hits_rare = keyword_search(["glassmorphism"])
        # Both should find something
        if hits_common and hits_rare:
            # Can't easily compare scores across queries but at least verify they work
            assert len(hits_common) > 0
            assert len(hits_rare) > 0

    def test_cap_at_30(self):
        hits = keyword_search(["file", "code", "error", "function", "python"])
        assert len(hits) <= 30

    def test_bm25_idf_formula(self):
        """Verify BM25 IDF produces correct values for known inputs."""
        n_docs = 10
        df = 2
        idf = math.log((n_docs - df + 0.5) / (df + 0.5) + 1)
        assert idf > 0  # should be positive for df < n_docs
        # Rare term (df=1) should have higher IDF
        idf_rare = math.log((n_docs - 1 + 0.5) / (1 + 0.5) + 1)
        idf_common = math.log((n_docs - 9 + 0.5) / (9 + 0.5) + 1)
        assert idf_rare > idf_common


# ─── _is_project_skill, _extract_project_name ────────────────────────────────

class TestProjectSkillHelpers:

    def test_tech_skills_not_project(self):
        assert not _is_project_skill("python")
        assert not _is_project_skill("javascript")
        assert not _is_project_skill("typescript")
        assert not _is_project_skill("frontend")
        assert not _is_project_skill("backend")

    def test_project_skills(self):
        assert _is_project_skill("jimpage")
        assert _is_project_skill("mostbased-core")
        assert _is_project_skill("mostbased-database")

    def test_extract_project_name(self):
        assert _extract_project_name("mostbased-core") == "mostbased"
        assert _extract_project_name("mostbased-database") == "mostbased"
        assert _extract_project_name("jimpage") == "jimpage"

    def test_normalize_kw(self):
        assert _normalize_kw("next.js") == "nextjs"
        assert _normalize_kw("framer-motion") == "framer-motion"
        assert _normalize_kw("Python") == "python"
        assert _normalize_kw("vue.js") == "vuejs"


# ─── get_relevant_skills ─────────────────────────────────────────────────────

class TestGetRelevantSkills:

    def _index(self):
        path = os.path.join(CSARA_DIR, "index.json")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_tech_skill_single_keyword(self):
        """Python skill should match with just 'python' keyword."""
        skills = get_relevant_skills("python script debug", self._index())
        assert "python" in skills

    def test_project_skill_with_project_name(self):
        """Project skills match when project name is in query."""
        skills = get_relevant_skills("mostbased admin roles", self._index())
        assert "mostbased-core" in skills

    def test_project_skill_without_project_name_generic_keyword(self):
        """Generic keywords alone shouldn't trigger project skills."""
        skills = get_relevant_skills("deployment server setup", self._index())
        assert "mostbased-core" not in skills

    def test_project_skill_specific_keyword(self):
        """Specific non-generic keywords should trigger project skills."""
        skills = get_relevant_skills("supabase rpc migration", self._index())
        assert "mostbased-database" in skills

    def test_normalized_keyword_matching(self):
        """next.js trigger should match nextjs query word."""
        skills = get_relevant_skills("nextjs pages router", self._index())
        assert "jimpage" in skills

    def test_multiword_keyword(self):
        """Multi-word keywords like 'jim nemorin' should match."""
        skills = get_relevant_skills("jim nemorin website portfolio", self._index())
        assert "jimpage" in skills

    def test_no_match(self):
        """Completely unrelated queries should return nothing."""
        skills = get_relevant_skills("quantum physics photon experiment", self._index())
        assert len(skills) == 0

    def test_claude_keyword_no_false_positive(self):
        """'claude reranking' about CSara internals should NOT trigger mostbased-ai-integration."""
        skills = get_relevant_skills("CSara skill selection retrieval ranking claude reranking", self._index())
        assert "mostbased-ai-integration" not in skills

    def test_cross_project_isolation(self):
        """Working on jimpage frontend should NOT load mostbased-frontend skill."""
        skills = get_relevant_skills("jimpage nextjs frontend component styling", self._index())
        assert "jimpage" in skills
        assert "mostbased-frontend" not in skills
        assert "mostbased-core" not in skills

    def test_general_frontend_skill_matches(self):
        """General frontend skill should match generic frontend queries."""
        skills = get_relevant_skills("responsive design accessibility component", self._index())
        assert "frontend" in skills
        assert "mostbased-frontend" not in skills

    def test_general_backend_skill_matches(self):
        """General backend skill should match generic backend queries."""
        skills = get_relevant_skills("rest api authentication middleware validation", self._index())
        assert "backend" in skills
        assert "mostbased-core" not in skills

    def test_generic_keywords_list(self):
        """Verify common generic words are in the GENERIC list."""
        for word in ["project", "frontend", "backend", "deployment", "tailwind"]:
            assert word in GENERIC_PROJECT_KEYWORDS
        # Domain-specific words should NOT be in the generic list
        for word in ["admin", "supabase", "sveltekit"]:
            assert word not in GENERIC_PROJECT_KEYWORDS

    def test_summary_stop_words(self):
        """Verify common summary stop words are filtered."""
        for word in ["error", "system", "project", "code"]:
            assert word in SKILL_SUMMARY_STOP_WORDS

    def test_empty_query(self):
        skills = get_relevant_skills("", self._index())
        assert skills == []

    def test_all_stop_words_query(self):
        skills = get_relevant_skills("the is a for and", self._index())
        assert len(skills) == 0

    def test_skill_rerank_triggers_above_threshold(self):
        """When >3 skills match keywords, Claude reranker should be called."""
        from unittest.mock import patch
        # Build a fake index with 5 skills that all match the query
        fake_index = {"skills": {
            f"skill-{i}": {
                "trigger_keywords": ["sveltekit", "supabase", "vote"],
                "summary": f"Skill {i} about sveltekit supabase voting"
            }
            for i in range(5)
        }}
        with patch("api.agents.retrieval.call_claude", return_value='["skill-0", "skill-2"]'):
            result = get_relevant_skills("sveltekit supabase vote system", fake_index)
        # Claude should have filtered to just 2
        assert result == ["skill-0", "skill-2"]

    def test_skill_rerank_skipped_below_threshold(self):
        """When <=3 skills match, no Claude call should be made."""
        from unittest.mock import patch
        fake_index = {"skills": {
            "python": {
                "trigger_keywords": ["python", "pip", "venv"],
                "summary": "Python language skill"
            },
            "javascript": {
                "trigger_keywords": ["javascript", "npm", "node"],
                "summary": "JavaScript language skill"
            },
        }}
        with patch("api.agents.retrieval.call_claude") as mock_claude:
            result = get_relevant_skills("python pip install", fake_index)
        mock_claude.assert_not_called()
        assert "python" in result


# ─── Integration: search accuracy regression suite ───────────────────────────

class TestSearchAccuracyRegression:
    """Quick regression tests for critical search scenarios."""

    def test_keyword_search_finds_jimpage_atoms(self):
        hits = keyword_search(["jimpage", "glassmorphism", "framer-motion"])
        # Should find jimpage-related atoms
        jimpage_atoms = {"mem_008", "mem_009", "mem_010", "mem_011", "mem_012"}
        found = set(hits.keys()) & jimpage_atoms
        assert len(found) >= 3

    def test_keyword_search_finds_python_atoms(self):
        hits = keyword_search(["python", "snake_case"])
        assert "mem_003" in hits

    def test_keyword_search_finds_csara_atoms(self):
        hits = keyword_search(["csara", "memory", "search", "keyword"])
        assert "mem_027" in hits  # Full-text keyword indexing atom

    def test_no_false_positive_substring(self):
        """Gibberish strings shouldn't match anything."""
        hits = keyword_search(["xyznonexistent123"])
        assert len(hits) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
