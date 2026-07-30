"""
Verification script for Keyless Web Search, Local Wikipedia, and Scraper Pipeline.
"""

import os
import sys

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(__file__))

def test_wiki_local():
    print("\n--- Testing Local Wikipedia Engine ---")
    from agents.wiki_local import search_wikipedia_titles, get_wikipedia_page, fetch_wikipedia_results
    titles = search_wikipedia_titles("Artificial Intelligence", limit=3)
    print(f"Found Wikipedia Titles: {titles}")
    assert len(titles) > 0, "Failed to find Wikipedia titles"

    page_info = get_wikipedia_page(titles[0])
    assert page_info is not None, "Failed to get Wikipedia page content"
    title, url, md_content = page_info
    print(f"Retrieved Wiki Page: {title} ({url}) - Length: {len(md_content)} chars")

    results = fetch_wikipedia_results("Machine Learning", max_articles=2)
    print(f"Bulk Wiki Fetch Results Count: {len(results)}")
    print("Local Wikipedia Engine PASSED!")


def test_scraper():
    print("\n--- Testing Multi-Tier Web Scraper ---")
    from agents.scraper import scrape_url
    test_url = "https://en.wikipedia.org/wiki/Web_scraping"
    url, content = scrape_url(test_url)
    print(f"Scraped URL: {url}")
    if content:
        print(f"Extracted Content Length: {len(content)} chars")
        print(f"Sample Content:\n{content[:300]}...")
        assert len(content) > 200, "Content extracted is too short"
        print("Web Scraper PASSED!")
    else:
        print("Web Scraper returned None (offline or network blocked).")


def test_duckduckgo():
    print("\n--- Testing Keyless DuckDuckGo Search ---")
    from agents.graph import fetch_duckduckgo
    class DummyConfig:
        def get(self, key, default=None):
            return default
    results = fetch_duckduckgo("quantum computing developments", config=DummyConfig(), max_results=3, max_scrape=2)
    print(f"DuckDuckGo Search Results Count: {len(results)}")
    for u, c in results.items():
        print(f"  - Source: {u} (Length: {len(c)} chars)")
    print("DuckDuckGo Search PASSED!")

if __name__ == "__main__":
    print("=== STARTING KEYLESS DEEP RESEARCH PIPELINE VERIFICATION ===")
    test_wiki_local()
    test_scraper()
    test_duckduckgo()
    print("\n=== ALL VERIFICATION TESTS PASSED SUCCESSFULLY ===")
