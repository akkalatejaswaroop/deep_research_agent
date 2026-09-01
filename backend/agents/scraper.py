"""
Multi-Tier Open-Source Web Scraper System.
Integrates Trafilatura (Tier 1), BeautifulSoup4 (Tier 2), and Playwright (Tier 3)
to extract clean, structured text and markdown from web pages without API keys.
"""

import os
import re
import sqlite3
import hashlib
import time
import requests
from typing import Tuple, Optional
from bs4 import BeautifulSoup

# Optional imports
try:
    import trafilatura
except ImportError:
    trafilatura = None

try:
    from playwright.sync_api import sync_playwright
    _PW_IMPORT_OK = True
except ImportError:
    sync_playwright = None
    _PW_IMPORT_OK = False

_PLAYWRIGHT_ENABLED = None


CACHE_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "scraper_cache.db")

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def _get_cache_db():
    conn = sqlite3.connect(CACHE_DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS page_cache (
            url_hash TEXT PRIMARY KEY,
            url TEXT,
            content TEXT,
            timestamp REAL
        )
        """
    )
    return conn


def _get_cached_page(url: str, ttl_seconds: int = 86400) -> Optional[str]:
    url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()
    try:
        conn = _get_cache_db()
        cursor = conn.cursor()
        cursor.execute("SELECT content, timestamp FROM page_cache WHERE url_hash = ?", (url_hash,))
        row = cursor.fetchone()
        conn.close()
        if row:
            content, timestamp = row
            if time.time() - timestamp < ttl_seconds:
                return content
    except Exception as e:
        print(f"Scraper cache read error: {e}")
    return None


def _set_cached_page(url: str, content: str):
    if not content or len(content) < 100:
        return
    url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()
    try:
        conn = _get_cache_db()
        conn.execute(
            "INSERT OR REPLACE INTO page_cache (url_hash, url, content, timestamp) VALUES (?, ?, ?, ?)",
            (url_hash, url, content, time.time()),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Scraper cache write error: {e}")


def clean_markdown_text(text: str) -> str:
    """Normalize whitespace and remove web garbage (cookies, popups, boilerplate)."""
    if not text:
        return ""
    # Remove image markdown
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    
    junk_patterns = (
        "cookie policy", "accept cookies", "we use cookies", "privacy settings",
        "subscribe to our newsletter", "sign up for our", "skip to content",
        "all rights reserved", "terms of use", "privacy policy", "copyright ©",
        "double click on what's possible", "skip to main content"
    )
    
    lines = []
    for line in text.splitlines():
        line_str = line.strip()
        if line_str.startswith("```"):
            continue
        lower_line = line_str.lower()
        if any(junk in lower_line for junk in junk_patterns):
            continue
        if line_str or line_str.startswith("#"):
            lines.append(line_str)
    return "\n".join(lines).strip()


def scrape_with_trafilatura(url: str, html_content: Optional[str] = None) -> Optional[str]:
    """Tier 1: Trafilatura main content extraction."""
    if trafilatura is None:
        return None
    try:
        if not html_content:
            downloaded = trafilatura.fetch_url(url)
        else:
            downloaded = html_content

        if downloaded:
            extracted = trafilatura.extract(
                downloaded,
                include_links=True,
                include_images=False,
                output_format="markdown",
                include_tables=True,
                favor_precision=True,
            )
            if extracted and len(extracted) >= 200:
                return clean_markdown_text(extracted[:12000])
    except Exception as e:
        print(f"Trafilatura scraping failed for {url}: {e}")
    return None


def scrape_with_bs4(html_content: str) -> Optional[str]:
    """Tier 2: BeautifulSoup4 text extraction with noise element removal."""
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "aside", "form", "iframe"]):
            tag.decompose()
        
        # Extract main text
        text = soup.get_text(separator="\n", strip=True)
        lines = [l for l in text.splitlines() if len(l.strip()) > 35]
        clean_text = "\n".join(lines[:120])
        if len(clean_text) >= 200:
            return clean_markdown_text(clean_text[:12000])
    except Exception as e:
        print(f"BS4 extraction failed: {e}")
    return None


def _pw_available() -> bool:
    global _PLAYWRIGHT_ENABLED
    if _PLAYWRIGHT_ENABLED is False:
        return False
    if not _PW_IMPORT_OK or sync_playwright is None:
        _PLAYWRIGHT_ENABLED = False
        return False
    return True

def scrape_with_playwright(url: str, timeout_ms: int = 2500) -> str:
    """Tier 3: Headless Playwright browser fallback for JS-rendered pages."""
    if not _pw_available():
        return ""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
            try:
                context = browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent=BROWSER_HEADERS["User-Agent"],
                    ignore_https_errors=True,
                )
                page = context.new_page()
                # Block heavy resources to speed up loading
                page.route("**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2,ico,font}", lambda route: route.abort())
                try:
                    # Use faster wait condition
                    page.goto(url, timeout=timeout_ms, wait_until="load")
                    html = page.content()
                except Exception as e:
                    # Fallback to whatever loaded
                    try:
                        html = page.content()
                    except:
                        html = ""
                finally:
                    try:
                        context.close()
                    except:
                        pass
                return html
            except Exception as e:
                print(f"Playwright browser error: {e}")
            finally:
                try:
                    browser.close()
                except:
                    pass
    except Exception as e:
        em = str(e)
        print(f"Playwright scraping failed for {url}: {type(e).__name__}")
    return ""


def scrape_with_jina(url: str, timeout: int = 8) -> str:
    """Tier 3a: Jina Reader API — keyless markdown conversion (~0.6-1.5s)."""
    try:
        resp = requests.get(
            f"https://r.jina.ai/{url}",
            headers={
                "Accept": "text/markdown",
                "User-Agent": BROWSER_HEADERS["User-Agent"]
            },
            timeout=timeout
        )
        if resp.status_code == 200 and len(resp.text) > 200:
            return clean_markdown_text(resp.text[:12000])
    except Exception:
        pass
    return ""



def scrape_url(url: str, timeout: int = 5, use_cache: bool = True) -> Tuple[str, Optional[str]]:
    """
    Main keyless entry point for URL scraping with fast failover.
    Fast path: requests + Trafilatura / BeautifulSoup (~0.5s max)
    Fallback: Jina Reader for markdown extraction (~1.5s)
    Last resort: Playwright for JS-heavy pages (max 2.5s, then fail)
    """
    if not url or not url.startswith("http"):
        return url, None

    # Check cache first
    if use_cache:
        cached = _get_cached_page(url)
        if cached:
            return url, cached

    # Fast path: standard HTTP + parsing
    html_raw = None
    try:
        # Use shorter timeout for initial request
        resp = requests.get(url, headers=BROWSER_HEADERS, timeout=min(timeout, 3), verify=False)
        if resp.status_code == 200 and len(resp.text) > 300:
            html_raw = resp.text
    except Exception as e:
        print(f"Initial request failed for {url}: {type(e).__name__}")
    
    # Try extraction if we got HTML
    if html_raw:
        # Tier 1: Trafilatura
        try:
            res_tf = scrape_with_trafilatura(url, html_content=html_raw)
            if res_tf and len(res_tf) >= 300:
                _set_cached_page(url, res_tf)
                return url, res_tf
        except Exception as e:
            print(f"Trafilatura failed: {type(e).__name__}")
        
        # Tier 2: BS4
        try:
            res_bs4 = scrape_with_bs4(html_raw)
            if res_bs4 and len(res_bs4) >= 300:
                _set_cached_page(url, res_bs4)
                return url, res_bs4
        except Exception as e:
            print(f"BS4 failed: {type(e).__name__}")

    # Tier 3a: Jina Reader (fast, reliable keyless markdown)
    try:
        res_jina = scrape_with_jina(url, timeout=min(timeout, 5))
        if res_jina and len(res_jina) >= 200:
            _set_cached_page(url, res_jina)
            return url, res_jina
    except Exception as e:
        print(f"Jina failed: {type(e).__name__}")

    # Tier 3: Playwright Fallback (JS-heavy only, SHORT timeout)
    try:
        res_pw = scrape_with_playwright(url, timeout_ms=2000)  # 2 second max
        if res_pw and len(res_pw) > 300:
            try:
                res_bs4 = scrape_with_bs4(res_pw)
                if res_bs4 and len(res_bs4) >= 200:
                    _set_cached_page(url, res_bs4)
                    return url, res_bs4
            except:
                pass
    except Exception as e:
        print(f"Playwright failed: {type(e).__name__}")

    # Return empty - page couldn't be scraped
    return url, None


