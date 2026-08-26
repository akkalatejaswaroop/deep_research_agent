import pytest
from unittest.mock import patch, MagicMock
from main import build_report_autonomously, call_llm, generate_sub_questions, generate_section, generate_executive_summary, generate_report_introduction, generate_future_outlook, generate_gap_analysis


class TestLLMResilience:
    """Test that the application survives all LLM failure modes."""

    @patch("main.call_llm", return_value="")
    @patch("main.search_all_sources", return_value=[])
    def test_empty_llm_produces_report_from_fallbacks(self, mock_search, mock_llm):
        """When LLM always returns empty, every section should still produce fallback content."""
        result = build_report_autonomously("What is quantum computing?", depth=1, target_sub_questions=3)
        report = result.get("report", "")
        assert report, "Report should not be empty"
        assert "What is quantum computing" in report or "quantum computing" in report.lower(), "Query should appear"
        assert len(report) > 200, f"Report too short ({len(report)} chars) to be useful fallback content"

    @patch("main.call_llm", side_effect=Exception("LLM crashed"))
    @patch("main.search_all_sources", return_value=[])
    def test_llm_exception_produces_report_from_fallbacks(self, mock_search, mock_llm):
        """When LLM raises exceptions, pipeline should still complete with fallback content."""
        result = build_report_autonomously("What is quantum computing?", depth=1, target_sub_questions=3)
        report = result.get("report", "")
        assert report, "Report should not be empty"
        assert len(report) > 200, f"Report too short ({len(report)} chars)"

    @patch("main.call_llm", side_effect=[""] * 10 + ["some valid text"])
    @patch("main.search_all_sources", return_value=[])
    def test_llm_intermittent_failures(self, mock_search, mock_llm):
        """Pipeline tolerates intermittent LLM failures (some calls fail, some succeed)."""
        result = build_report_autonomously("What is quantum computing?", depth=1, target_sub_questions=3)
        report = result.get("report", "")
        assert report, "Report should not be empty"

    @patch("main.call_llm", side_effect=Exception("Connection refused"))
    @patch("main.search_all_sources", side_effect=Exception("Network error"))
    def test_everything_crashes_gracefully(self, mock_search, mock_llm):
        """When both LLM and search fail, pipeline returns a panic-safe result, never throws."""
        result = build_report_autonomously("What is quantum computing?", depth=1, target_sub_questions=3)
        assert isinstance(result, dict), "Result must be a dict"
        report = result.get("report", "")
        assert "GENERATION FAILED" in report or len(report) > 0

    @patch("main.call_llm", return_value="")
    def test_sub_questions_generated_without_llm(self, mock_llm):
        """generate_sub_questions produces template questions when LLM returns empty."""
        sqs = generate_sub_questions("What is quantum computing?", target_count=4)
        assert len(sqs) == 4, f"Expected 4 sub-questions, got {len(sqs)}"
        for q in sqs:
            assert len(q) > 10, f"Sub-question too short: {q}"

    @patch("main.call_llm", return_value="")
    @patch("main._extract_evidence", return_value=[
        {"sentence": "Quantum computers use qubits.", "citation": "[1]", "source": {"url": "http://example.com", "domain": "example.com", "title": "Example"}, "relevance": 0.9}
    ])
    def test_section_fallback_uses_evidence(self, mock_evidence, mock_llm):
        """generate_section should fall back to evidence-based content when LLM returns empty."""
        section = generate_section(
            query="What is quantum computing?",
            sub_question="How do qubits work?",
            sources=[{"url": "http://example.com", "domain": "example.com", "title": "Example", "content": "Quantum computers use qubits."}],
            para_count=2,
        )
        assert len(section) > 50, f"Section too short: {section[:100]}"
        assert "qubit" in section.lower(), "Section should contain content about qubits"

    @patch("main.call_llm", return_value="")
    def test_executive_summary_string_fallback(self, mock_llm):
        """generate_executive_summary falls back when LLM is unavailable."""
        summary = generate_executive_summary(
            query="What is RISC-V?",
            sources=[],
            sections_summaries=["Architecture overview", "Ecosystem adoption", "Performance characteristics"],
        )
        assert len(summary) > 30, f"Summary too short: {summary[:100]}"

    @patch("main.call_llm", return_value="")
    def test_future_outlook_string_fallback(self, mock_llm):
        """generate_future_outlook should return insufficiency marker when no sources."""
        outlook = generate_future_outlook(
            query="What is RISC-V?",
            sources=[],
        )
        assert "INSUFFICIENT EVIDENCE" in outlook or len(outlook) > 30

    @patch("main.call_llm", return_value="")
    def test_gap_analysis_string_fallback(self, mock_llm):
        """generate_gap_analysis should return default gap text when LLM fails."""
        gap = generate_gap_analysis(
            query="What is RISC-V?",
            section_texts=["Some analysis text"],
        )
        assert len(gap) > 30, f"Gap analysis too short: {gap[:100]}"


class TestCallLLMHardening:
    """Test that call_llm internal hardening works correctly."""

    def setup_method(self):
        from main import _llm_retry_counts
        _llm_retry_counts.clear()

    @patch("main._call_llm_once", return_value="")
    def test_call_llm_retries_on_empty(self, mock_once):
        """call_llm should retry up to 3 times when _call_llm_once returns empty."""
        result = call_llm("test prompt")
        assert result == ""
        assert mock_once.call_count == 3

    @patch("main._call_llm_once", side_effect=["", "", "valid response"])
    def test_call_llm_succeeds_on_retry(self, mock_once):
        """call_llm should succeed when retry eventually returns content."""
        result = call_llm("test prompt")
        assert result == "valid response"
        assert mock_once.call_count == 3
