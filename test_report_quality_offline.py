import pytest
import re
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from backend.main import (
    _extract_display_topic,
    _deduplicate_paragraphs,
    generate_future_outlook,
    generate_gap_analysis,
    generate_implications_section,
    _generate_data_highlights,
    generate_verification_notes,
)
from backend.agents.scraper import clean_markdown_text


def test_clean_markdown_text_strips_web_garbage():
    raw_html = """
    Skip to content
    Welcome to the article on AI agents.
    Accept Cookies - We use cookies for analytics.
    Subscribe to our newsletter for more updates.
    All rights reserved © 2026.
    """
    cleaned = clean_markdown_text(raw_html)
    assert "Accept Cookies" not in cleaned
    assert "Subscribe to our newsletter" not in cleaned
    assert "All rights reserved" not in cleaned
    assert "Welcome to the article on AI agents." in cleaned


def test_extract_display_topic():
    query = "What are the best agentic AI companies growing in 2026?"
    topic = _extract_display_topic(query)
    assert "What are the best" not in topic
    assert topic.lower() == "agentic ai companies" or "agentic ai" in topic.lower()
    # Check that topic is natural word order, not sorted alphabetically
    assert not topic.startswith("2026")


def test_deduplicate_paragraphs():
    block = "This is a long paragraph explaining the core architecture and details of autonomous agents in depth. " * 3
    report = f"## Section 1\n\n{block}\n\n## Section 2\n\n{block}\n\n"
    deduped = _deduplicate_paragraphs(report)
    assert deduped.count(block.strip()) == 1


def test_section_fallbacks_no_meta_apologies():
    query = "quantum computing developments"
    sources = [{"url": "https://example.com/quantum", "content": "IBM revealed a 1,000 qubit quantum processor in 2026."}]
    
    outlook = generate_future_outlook(query, sources)
    assert "consider increasing search depth" not in outlook.lower()
    assert "did not contain enough" not in outlook.lower()
    
    gaps = generate_gap_analysis(query, ["Section text about qubits."], sources)
    assert "insufficient evidence in the available sources" not in gaps.lower()
    
    implications = generate_implications_section(query, sources)
    assert "consider increasing search depth" not in implications.lower()
    
    highlights = _generate_data_highlights(sources)
    assert "consider increasing search depth" not in highlights.lower()
    assert "1,000 qubit" in highlights or "quantum processor" in highlights or "empirical" in highlights.lower()


def test_verification_notes_no_disclaimers():
    query = "AI models"
    sources = [{"url": "https://example.com/ai", "content": "GPT-4 was released in 2023."}]
    section_texts = ["In 2026, model capacity expanded 100x."]
    notes = generate_verification_notes(query, sources, section_texts)
    assert "reported by source; not independently corroborated" not in notes
    assert "(reported by source" not in notes.lower()


if __name__ == "__main__":
    test_clean_markdown_text_strips_web_garbage()
    test_extract_display_topic()
    test_deduplicate_paragraphs()
    test_section_fallbacks_no_meta_apologies()
    test_verification_notes_no_disclaimers()
    print("ALL OFFLINE REPORT QUALITY TESTS PASSED SUCCESSFUL!")
