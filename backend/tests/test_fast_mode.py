import os
import sys
import json
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_build_fast_report_returns_complete_report():
    from main import build_report_autonomously

    with patch("main.search_all_sources", return_value=[]), \
         patch("main.call_llm", return_value=""):
        result = build_report_autonomously("AI safety", depth=1, complexity=1)

    assert "Deep Research Report" in result["report"]
    assert "Executive Summary" in result["report"]
    assert "Key Findings" in result["report"]
    assert isinstance(result["source_urls"], list)
    assert isinstance(result["structured_refs"], list)


def test_build_fast_report_avoids_canned_generic_language():
    from main import build_report_autonomously

    with patch("main.search_all_sources", return_value=[]), \
         patch("main.call_llm", return_value=""):
        result = build_report_autonomously("state space search", depth=1, complexity=1)

    report = result["report"].lower()
    assert "evolving research and implementation domain" not in report
    assert "most important pattern is that the topic is no longer abstract" not in report
    assert "insufficient evidence" in report


def test_search_all_sources_blocks_vixra_sources():
    from main import search_all_sources

    with patch("main.search_wikipedia", return_value=[]), \
         patch("main.search_web_duckduckgo", return_value=[
        {"url": "https://vixra.org/pdf/1234", "title": "Vixra", "domain": "vixra.org", "content": "Draft"},
        {"url": "https://example.com/paper", "title": "Example", "domain": "example.com", "content": "Valid source"},
    ]):
        results = search_all_sources("state space search", max_sources=10)

    urls = [item["url"] for item in results]
    assert "https://vixra.org/pdf/1234" not in urls
    assert "https://example.com/paper" in urls


def test_evidence_matrix_marks_extraction_failure():
    from main import generate_evidence_matrix

    matrix = generate_evidence_matrix([
        {"url": "https://example.com", "title": "Empty page", "domain": "example.com", "content": ""}
    ])

    assert "[EXTRACTION FAILED]" in matrix


def test_sub_questions_are_forced_to_be_more_specific():
    from main import _coerce_sub_questions

    result = _coerce_sub_questions(
        "state space search",
        ["What are the latest developments, current research findings, and key examples involving state space search?"],
        4,
    )

    assert len(result) == 4
    assert not any("latest developments" in item.lower() for item in result)
    assert any("benchmark" in item.lower() or "historical" in item.lower() or "implementation" in item.lower() for item in result)


def test_auto_research_profile_sets_parameters_from_query():
    from main import _auto_research_profile

    history_profile = _auto_research_profile("history of ai research")
    technical_profile = _auto_research_profile("state space search algorithms for AI planning")

    assert history_profile["target_sub_questions"] <= technical_profile["target_sub_questions"]
    assert technical_profile["target_paragraphs"] >= 3
    assert technical_profile["depth"] >= history_profile["depth"]
