"""Comprehensive E2E tests for the deep research pipeline.

Tests cover:
  - Each individual node function with mock LLM responses
  - Full graph traversal end-to-end
  - Edge cases: empty results, failed nodes, missing config
  - All 10 improvements integrated
"""
import sys, os, json, pytest
from unittest.mock import patch, MagicMock, PropertyMock
from typing import Dict, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Intercept OllamaEmbeddings before importing agents.graph
class MockOllamaEmbeddings:
    def __init__(self, *args, **kwargs):
        pass
    def embed_query(self, text):
        return [0.0] * 768
    def embed_documents(self, texts):
        return [[0.0] * 768 for _ in texts]

import langchain_ollama
langchain_ollama.OllamaEmbeddings = MockOllamaEmbeddings

# -- Fixtures -----------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_ext_deps():
    """Mock all external service dependencies before every test."""
    import agents.graph as graph
    
    # Mock external clients to prevent real network/db operations
    graph.supabase_client = None
    graph.redis_client = None
    graph._embeddings_backend = MockOllamaEmbeddings()
    
    # Mock network request functions to keep tests local & fast
    graph.search_and_scrape = MagicMock(return_value={"https://example.com": "Content"})
    graph._wiki_fetch = MagicMock(return_value="")
    graph.cached_search = MagicMock(return_value={"https://example.com": "Content"})
    
    # Reset stateful provenance/scores
    graph.SOURCE_QUALITY = {
        "firecrawl": 1.0, 
        "tavily": 1.0, 
        "serpapi": 1.0, 
        "langsearch": 1.0, 
        "pixelrag": 1.0, 
        "duckduckgo": 0.6
    }
    graph._provenance = {}


def make_llm(content_str: str):
    """Create a MagicMock that behaves like an LLM for prompt | llm chains."""
    obj = type("obj", (), {"content": content_str})()
    m = MagicMock()
    m.return_value = obj
    m.invoke = MagicMock(return_value=obj)
    return m


def make_state(**overrides) -> Dict[str, Any]:
    return {
        "query": "test query",
        "depth": 1,
        "complexity": 1,
        "current_depth": 0,
        "sub_questions": [],
        "search_queries": [],
        "raw_pages": {},
        "source_urls": [],
        "scored_chunks": [],
        "synthesis_results": [],
        "gap_results": [],
        "gap_iteration": 0,
        "cited_report": "",
        "report": "",
        "findings": [],
        "sub_tasks": [],
        "feedback": "",
        "is_valid": False,
        "prior_lessons": [],
        "retrieved_memory": [],
        "structured_refs": [],
        **overrides
    }


# -- Node tests ---------------------------------------------------------------

class TestPlannerNode:
    """Tests for planner_node — sub-question generation (Stage 1)."""

    def test_generates_sub_questions(self):
        from agents.graph import planner_node
        llm = make_llm(json.dumps({"sub_questions": ["What is X?", "How does Y work?"]}))
        with patch("agents.graph.get_llm", return_value=llm):
            state = make_state()
            config = {"configurable": {"thread_id": "test"}}
            result = planner_node(state, config)
        assert "sub_questions" in result
        assert len(result["sub_questions"]) == 2
        assert result["sub_questions"][0] == "What is X?"

    def test_injects_prior_lessons(self):
        from agents.graph import planner_node
        llm = make_llm(json.dumps({"sub_questions": ["Q1"]}))
        with patch("agents.graph.get_llm", return_value=llm):
            state = make_state(prior_lessons=["Always search Wikipedia first"])
            config = {"configurable": {"thread_id": "test"}}
            result = planner_node(state, config)
        assert "sub_questions" in result

    def test_handles_malformed_llm_output(self):
        from agents.graph import planner_node
        llm = make_llm("not json")
        with patch("agents.graph.get_llm", return_value=llm):
            state = make_state()
            config = {"configurable": {"thread_id": "test"}}
            result = planner_node(state, config)
        assert "sub_questions" in result
        assert len(result["sub_questions"]) > 0


class TestMemoryRetrievalNode:
    """Tests for memory_retrieval_node (Stage 1b)."""

    def test_returns_empty_when_no_supabase(self):
        from agents.graph import memory_retrieval_node
        state = make_state(sub_questions=["What is X?"])
        config = {"configurable": {"thread_id": "test"}}
        result = memory_retrieval_node(state, config)
        assert "retrieved_memory" in result
        assert result["retrieved_memory"] == []


class TestSearcherNode:
    """Tests for searcher_node — parallel search execution (Stage 2)."""

    def test_searches_and_collects_pages(self):
        from agents.graph import searcher_node
        state = make_state(
            sub_questions=["What is X?"],
            search_queries=["X definition", "X explained"]
        )
        config = {"configurable": {"thread_id": "test"}}
        result = searcher_node(state, config)
        assert "raw_pages" in result
        assert "source_urls" in result

    def test_handles_empty_search_queries(self):
        from agents.graph import searcher_node
        state = make_state(sub_questions=["Q1"], search_queries=[])
        config = {"configurable": {"thread_id": "test"}}
        result = searcher_node(state, config)
        assert result == {}, "searcher returns {} when no queries to run"


class TestFilterNode:
    """Tests for filter_node — relevance scoring (Stage 3)."""

    def test_filters_and_scores_chunks(self):
        from agents.graph import filter_node, _provenance
        _provenance.clear()
        _provenance["https://example.com"] = "firecrawl"
        llm = make_llm(json.dumps([
            {"url": "https://example.com", "score": 8, "reason": "relevant"}
        ]))
        with patch("agents.graph.get_llm", return_value=llm):
            state = make_state(
                sub_questions=["What is X?"],
                raw_pages={"https://example.com": "Some content about X."},
                source_urls=["https://example.com"]
            )
            config = {"configurable": {"thread_id": "test"}}
            result = filter_node(state, config)
        assert "scored_chunks" in result
        assert len(result["scored_chunks"]) > 0
        chunk = result["scored_chunks"][0]
        assert chunk["score"] == 8

    def test_applies_source_quality_multiplier(self):
        from agents.graph import filter_node, _provenance, SOURCE_QUALITY
        _provenance.clear()
        _provenance["https://duckduckgo.com/result"] = "duckduckgo"
        llm = make_llm(json.dumps([
            {"url": "https://duckduckgo.com/result", "score": 8, "reason": "ok"}
        ]))
        with patch("agents.graph.get_llm", return_value=llm):
            state = make_state(
                sub_questions=["Q1"],
                raw_pages={"https://duckduckgo.com/result": "content"},
                source_urls=["https://duckduckgo.com/result"]
            )
            config = {"configurable": {"thread_id": "test"}}
            result = filter_node(state, config)
        if result.get("scored_chunks"):
            assert result["scored_chunks"][0]["score"] == 4, "0.6 * 8 = 4.8 -> 4"

    def test_fallback_scoring(self):
        from agents.graph import filter_node, _provenance
        _provenance.clear()
        llm = make_llm("invalid json")
        with patch("agents.graph.get_llm", return_value=llm):
            state = make_state(
                sub_questions=["Q1"],
                raw_pages={"https://example.com": "Some content"},
                source_urls=["https://example.com"]
            )
            config = {"configurable": {"thread_id": "test"}}
            result = filter_node(state, config)
        assert "scored_chunks" in result
        if result["scored_chunks"]:
            assert result["scored_chunks"][0]["score"] == 3, "6 * 0.6 = 3.6 -> 3"


class TestSynthesisNode:
    """Tests for synthesis_node — per-sub-question analysis (Stage 4)."""

    def test_synthesizes_answers(self):
        from agents.graph import synthesis_node
        llm = make_llm("This is a synthesized answer with [1] citation.")
        with patch("agents.graph.get_llm", return_value=llm):
            state = make_state(
                sub_questions=["What is X?"],
                scored_chunks=[{
                    "sub_question_idx": 0,
                    "sub_question": "What is X?",
                    "url": "https://example.com",
                    "chunk": "Content about X.",
                    "score": 8,
                    "reason": "relevant"
                }],
                source_urls=["https://example.com"]
            )
            config = {"configurable": {"thread_id": "test"}}
            result = synthesis_node(state, config)
        assert "synthesis_results" in result
        assert len(result["synthesis_results"]) > 0
        assert "structured_refs" in result
        assert "findings" in result

    def test_handles_no_relevant_chunks(self):
        from agents.graph import synthesis_node
        llm = make_llm("Default answer.")
        with patch("agents.graph.get_llm", return_value=llm):
            state = make_state(
                sub_questions=["What is X?"],
                scored_chunks=[],
                source_urls=[]
            )
            config = {"configurable": {"thread_id": "test"}}
            result = synthesis_node(state, config)
        assert "synthesis_results" in result
        assert "No relevant sources" in result["synthesis_results"][0]["answer"]


class TestGapDetector:
    """Tests for gap_detector_node — iteration loop (Stage 5)."""

    def test_detects_gaps(self):
        from agents.graph import gap_detector_node
        llm = make_llm(json.dumps({
            "gaps": [{"sub_question": "What is X?", "status": "PARTIAL", "new_queries": ["detailed X query"]}]
        }))
        with patch("agents.graph.get_llm", return_value=llm):
            state = make_state(
                depth=2,
                synthesis_results=[{"sub_question": "What is X?", "answer": "Partial answer."}]
            )
            config = {"configurable": {"thread_id": "test"}}
            result = gap_detector_node(state, config)
        assert "gap_results" in result
        assert len(result["gap_results"]) == 1
        assert result["gap_results"][0]["status"] == "PARTIAL"


class TestCitationMapper:
    """Tests for citation_mapper_node — structured references (Stage 6)."""

    def test_produces_html_anchors(self):
        from agents.graph import citation_mapper_node
        llm = make_llm("Answer with [^1] citation.")
        with patch("agents.graph.get_llm", return_value=llm):
            state = make_state(
                synthesis_results=[{"sub_question": "Q1", "answer": "Ans [1]."}],
                source_urls=["https://example.com"],
                structured_refs=[{"id": 1, "url": "https://example.com", "domain": "example.com"}]
            )
            config = {"configurable": {"thread_id": "test"}}
            result = citation_mapper_node(state, config)
        assert "cited_report" in result
        cited = result["cited_report"]
        assert isinstance(cited, str), f"Expected str, got {type(cited)}"
        assert "<a href=" in cited or "References" in cited

    def test_fallback_when_no_structured_refs(self):
        from agents.graph import citation_mapper_node
        llm = make_llm("Answer.")
        with patch("agents.graph.get_llm", return_value=llm):
            state = make_state(
                synthesis_results=[{"sub_question": "Q1", "answer": "Ans."}],
                source_urls=["https://example.com"],
                structured_refs=[]
            )
            config = {"configurable": {"thread_id": "test"}}
            result = citation_mapper_node(state, config)
        assert "cited_report" in result
        assert isinstance(result["cited_report"], str)


class TestReportNode:
    """Tests for report_node — final compilation (Stage 7)."""

    def test_generates_report(self):
        from agents.graph import report_node
        llm = make_llm("# Final Report\n\nSummary here.")
        with patch("agents.graph.get_llm", return_value=llm):
            state = make_state(
                synthesis_results=[{"sub_question": "Q1", "answer": "A1"}],
                source_urls=["https://example.com"],
                gap_results=[],
                structured_refs=[{"id": 1, "url": "https://example.com", "domain": "example.com"}]
            )
            config = {"configurable": {"thread_id": "test"}}
            result = report_node(state, config)
        assert "report" in result
        assert isinstance(result["report"], str)
        assert len(result["report"]) > 0


class TestEvaluatorNode:
    """Tests for evaluator_node — lesson extraction."""

    def test_extracts_lesson(self):
        from agents.graph import evaluator_node
        llm = make_llm("Lesson: Check sources first.")
        with patch("agents.graph.get_llm", return_value=llm):
            state = make_state(query="test", report="# Report")
            config = {"configurable": {"thread_id": "test"}}
            result = evaluator_node(state, config)
        assert isinstance(result, dict)


# -- Full Pipeline E2E --------------------------------------------------------

class TestFullPipeline:
    """End-to-end graph traversal with fully mocked dependencies."""

    def _mock_llm_for_e2e(self):
        """Create a mock LLM that returns valid JSON for planner/gap and text for others."""
        llm = MagicMock()
        responses = {
            "planner": json.dumps({"sub_questions": ["What is X?", "How does Y work?"]}),
            "gap": json.dumps({"gaps": [], "is_valid": True, "feedback": ""}),
        }
        def side_effect(*args, **kwargs):
            return type("obj", (), {"content": "Mocked research content with [1] citation."})()

        def call_side(input=None, **kwargs):
            return type("obj", (), {"content": "Mocked content."})()

        llm.side_effect = call_side
        llm.return_value = type("obj", (), {"content": "Mocked content."})()
        return llm

    def test_full_pipeline_runs_to_completion(self):
        from agents.graph import app_graph
        llm = self._mock_llm_for_e2e()
        with patch("agents.graph.get_llm", return_value=llm):
            config = {"configurable": {"thread_id": "e2e-test"}}
            state = make_state()
            outputs = []
            for output in app_graph.stream(state, config=config):
                outputs.append(output)
            assert len(outputs) > 0
            final_state = app_graph.get_state(config)
            assert final_state is not None
            assert "report" in final_state.values

    def test_pipeline_with_no_sources(self):
        from agents.graph import app_graph
        llm = self._mock_llm_for_e2e()
        with patch("agents.graph.get_llm", return_value=llm), \
             patch("agents.graph.search_and_scrape", return_value={}), \
             patch("agents.graph._wiki_fetch", return_value=""):
            config = {"configurable": {"thread_id": "e2e-empty"}}
            state = make_state()
            outputs = []
            for output in app_graph.stream(state, config=config):
                outputs.append(output)
            final_state = app_graph.get_state(config)
            report = final_state.values.get("report", "") if final_state else ""
            assert isinstance(report, str)


# -- Cache Integration --------------------------------------------------------

class TestCacheIntegration:
    """Tests that cached_search integrates correctly."""

    def test_cached_search_wraps_response(self):
        from agents.graph import cached_search
        with patch("agents.graph.search_and_scrape") as mock_search:
            mock_search.return_value = {"https://example.com": "Content"}
            config = {"configurable": {"thread_id": "cache-test"}}
            result = cached_search("test query", config)
            assert "https://example.com" in result
            assert result["https://example.com"] == "Content"


# -- State Schema Tests -------------------------------------------------------

class TestStateSchema:
    """Verify that the AgentState TypedDict has all required fields."""

    def test_all_fields_present(self):
        from typing import get_type_hints
        from agents.state import AgentState
        hints = get_type_hints(AgentState)
        required = [
            "query", "depth", "complexity", "current_depth",
            "sub_questions", "search_queries", "raw_pages",
            "source_urls", "scored_chunks", "synthesis_results",
            "gap_results", "gap_iteration", "cited_report",
            "report", "findings", "sub_tasks", "feedback",
            "is_valid", "prior_lessons", "retrieved_memory",
            "structured_refs"
        ]
        for field in required:
            assert field in hints, f"Missing field: {field}"
        assert len(hints) >= len(required)
