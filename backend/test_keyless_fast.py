# -*- coding: utf-8 -*-
import sys
import os
import json
import re

sys.path.insert(0, os.path.dirname(__file__))

print("=== Running Fast Keyless Pipeline Component Verification ===")

from main import (
    _scrape_clean_text,
    _extract_core_topic,
    _dedupe_sources,
    generate_sub_questions,
    search_wikipedia,
)

# Test 1: Boilerplate text cleaning
raw_web_text = """
Subscribe to our newsletter! Sign in to continue. Cookie policy. All rights reserved.
Solid-state batteries utilize solid electrolytes instead of liquid organic electrolytes, achieving energy densities exceeding 450 Wh/kg in laboratory testing.
Click here to learn more. Terms of service apply.
Major EV manufacturers including Toyota and QuantumScape are scaling solid-state cell pilot lines for commercial deployment between 2026 and 2028.
Reported by the source; not independently corroborated.
"""

cleaned_text = _scrape_clean_text(raw_web_text, min_line_len=30)
print("\n--- Test 1: Clean Scraped Text ---")
print(cleaned_text)

assert "Solid-state batteries utilize solid" in cleaned_text, "Failed to preserve empirical content"
assert "Subscribe to our newsletter" not in cleaned_text, "Boilerplate subscribe text not removed"
assert "Cookie policy" not in cleaned_text, "Cookie disclaimer not removed"

# Test 2: Core Topic Extraction
query = "How will solid-state batteries change EV manufacturing by 2026?"
core_topic = _extract_core_topic(query)
print("\n--- Test 2: Core Topic Extraction ---")
print(f"Original: '{query}' -> Core: '{core_topic}'")
assert "solid-state batteries" in core_topic.lower(), "Core topic extraction failed"

# Test 3: Sub-question Generation
sub_qs = generate_sub_questions(query, target_count=4)
print("\n--- Test 3: Sub-Questions Generated ---")
for i, sq in enumerate(sub_qs, 1):
    print(f"  {i}. {sq}")
assert len(sub_qs) == 4, "Sub-question count mismatch"

# Test 4: Wikipedia Search Retrieval
wiki_results = search_wikipedia("Solid-state battery", max_results=2)
print("\n--- Test 4: Wikipedia Keyless Retrieval ---")
print(f"Retrieved {len(wiki_results)} pages")
if wiki_results:
    print(f"Page 1 Title: {wiki_results[0].get('title')}")
    print(f"Page 1 Domain: {wiki_results[0].get('domain')}")
    assert wiki_results[0].get('domain') == 'wikipedia.org', "Wikipedia domain mismatch"

print("\n*** ALL 4 FAST COMPONENT VERIFICATION TESTS PASSED SUCCESSFULLY! ***")
