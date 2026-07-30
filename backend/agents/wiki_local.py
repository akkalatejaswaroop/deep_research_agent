"""
Local Open-Source Wikipedia Engine with SQLite Disk Caching.
Provides fast keyless knowledge retrieval using open-source Wikipedia packages
and Wikipedia REST endpoints with persistent local caching.
"""

import os
import sqlite3
import hashlib
import time
import requests
from typing import Dict, List, Tuple, Optional

try:
    import wikipedia
    wikipedia.set_lang("en")
except ImportError:
    wikipedia = None

WIKI_CACHE_DB = os.path.join(os.path.dirname(__file__), "..", "wiki_cache.db")
WIKI_USER_AGENT = "LocalDeepResearchAgent/2.0 (OpenSource/WikipediaLocal)"


def _get_wiki_db():
    conn = sqlite3.connect(WIKI_CACHE_DB)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS wiki_cache (
            key_hash TEXT PRIMARY KEY,
            title TEXT,
            url TEXT,
            content TEXT,
            timestamp REAL
        )
        """
    )
    return conn


def _get_cached_wiki(key: str) -> Optional[Tuple[str, str, str]]:
    key_hash = hashlib.sha256(key.lower().strip().encode("utf-8")).hexdigest()
    try:
        conn = _get_wiki_db()
        cursor = conn.cursor()
        cursor.execute("SELECT title, url, content FROM wiki_cache WHERE key_hash = ?", (key_hash,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return row[0], row[1], row[2]
    except Exception as e:
        print(f"Wiki cache error: {e}")
    return None


def _set_cached_wiki(key: str, title: str, url: str, content: str):
    if not content or len(content) < 100:
        return
    key_hash = hashlib.sha256(key.lower().strip().encode("utf-8")).hexdigest()
    try:
        conn = _get_wiki_db()
        conn.execute(
            "INSERT OR REPLACE INTO wiki_cache (key_hash, title, url, content, timestamp) VALUES (?, ?, ?, ?, ?)",
            (key_hash, title, url, content, time.time()),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Wiki cache write error: {e}")


def search_wikipedia_titles(query: str, limit: int = 5) -> List[str]:
    """Search for relevant Wikipedia article titles."""
    if wikipedia is not None:
        try:
            results = wikipedia.search(query, results=limit)
            if results:
                return results
        except Exception:
            pass

    # Fallback to direct Wikimedia REST search
    try:
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": limit,
            "format": "json",
        }
        r = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params=params,
            headers={"User-Agent": WIKI_USER_AGENT},
            timeout=5,
        )
        if r.status_code == 200:
            data = r.json()
            hits = data.get("query", {}).get("search", [])
            return [h["title"] for h in hits if "title" in h]
    except Exception as e:
        print(f"Wiki REST search error: {e}")

    return []


def get_wikipedia_page(title: str) -> Optional[Tuple[str, str, str]]:
    """
    Fetch full article/summary for a title.
    Returns (title, url, formatted_markdown).
    """
    cached = _get_cached_wiki(title)
    if cached:
        return cached

    # Try Wikipedia python library
    if wikipedia is not None:
        try:
            page = wikipedia.page(title, auto_suggest=False)
            url = page.url
            summary = page.summary
            content = page.content or summary
            md_text = f"# {page.title}\n\n{content[:8000]}"
            _set_cached_wiki(title, page.title, url, md_text)
            return page.title, url, md_text
        except Exception:
            pass

    # Fallback to REST endpoint
    try:
        safe_title = requests.utils.quote(title)
        r = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{safe_title}",
            headers={"User-Agent": WIKI_USER_AGENT},
            timeout=5,
        )
        if r.status_code == 200:
            d = r.json()
            extract = d.get("extract", "")
            page_url = d.get("content_urls", {}).get("desktop", {}).get("page", "")
            if extract and page_url:
                md_text = f"# {title}\n\n{extract[:8000]}"
                _set_cached_wiki(title, title, page_url, md_text)
                return title, page_url, md_text
    except Exception as e:
        print(f"Wiki REST summary error: {e}")

    return None


def _wiki_key_terms(query: str) -> str:
    import re
    stop = {"what", "when", "where", "which", "how", "does", "can", "are", "the", "and", "for", "with", "that", "this", "from", "have", "been", "were", "about", "their", "they", "will", "would", "could", "should", "into", "more", "most", "over", "such", "than", "then", "also", "after", "other", "some", "these", "those", "through"}
    words = re.findall(r"[a-zA-Z0-9\-]{3,}", query.lower())
    key = [w for w in words if w not in stop]
    return " ".join(key[:8]) if key else query

def fetch_wikipedia_results(query: str, max_articles: int = 4) -> Dict[str, str]:
    """
    Local Open-Source Wikipedia search & retrieval entry point.
    Returns Dict[url, markdown_content].
    """
    results: Dict[str, str] = {}
    titles = search_wikipedia_titles(_wiki_key_terms(query), limit=max_articles)
    if not titles:
        return results

    from concurrent.futures import ThreadPoolExecutor, as_completed

    with ThreadPoolExecutor(max_workers=min(4, len(titles))) as executor:
        futures = [executor.submit(get_wikipedia_page, t) for t in titles]
        for f in as_completed(futures):
            try:
                res = f.result()
                if res:
                    title, url, md_content = res
                    if url and md_content:
                        results[url] = md_content
            except Exception as e:
                print(f"Wiki worker error: {e}")

    return results
