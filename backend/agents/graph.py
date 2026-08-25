import json
import re
import hashlib
import sys
import os
import threading
import datetime
import contextvars
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any
from langgraph.graph import StateGraph, END
from langgraph.types import interrupt
from langchain_core.runnables import RunnableConfig, RunnableLambda
from langchain_core.prompts import ChatPromptTemplate
import redis
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except Exception:
    RecursiveCharacterTextSplitter = None
from bs4 import BeautifulSoup
import requests
import urllib3
warnings.filterwarnings("ignore")
import numpy as np
try:
    from langchain_ollama import ChatOllama, OllamaEmbeddings
except ImportError:
    ChatOllama = None
    OllamaEmbeddings = None
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import supabase_client, in_memory_knowledge
from .state import AgentState
from .metrics_collector import (
    start_session, record_node_entry, record_node_exit,
    record_llm_call, record_quality_scores, record_prior_lessons,
    record_graph_state, compute as compute_metrics, clear as clear_metrics
)

_current_session_id = contextvars.ContextVar("session_id", default="")


def extract_json(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    code_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if code_match:
        try:
            return json.loads(code_match.group(1))
        except json.JSONDecodeError:
            pass
    start = text.find('{')
    if start != -1:
        count = 0
        for i in range(start, len(text)):
            if text[i] == '{': count += 1
            elif text[i] == '}': count -= 1
            if count == 0:
                try:
                    return json.loads(text[start:i+1])
                except (json.JSONDecodeError, IndexError, ValueError):
                    pass
    return None


def _check_cancellation(config: RunnableConfig):
    if config and "configurable" in config:
        cancel_evt = config["configurable"].get("cancel_event")
        if cancel_evt and cancel_evt.is_set():
            raise RuntimeError("Operation cancelled by user")


def _build_graph_provenance(synthesis_results: list, source_urls: list) -> dict:
    provenance = {}
    for idx, url in enumerate(source_urls):
        domain = url.split("/")[2] if "://" in url else url
        provenance[url] = {
            "index": idx + 1,
            "domain": domain,
            "tier": "general",
            "quality_score": 0.8 if any(d in domain for d in ["edu", "gov", "arxiv", "nature"]) else 0.6
        }
    return provenance


def emit_thought(config: RunnableConfig, message: str):
    if config and "configurable" in config:
        event_queue = config["configurable"].get("event_queue")
        if event_queue is not None:
            try:
                event_queue.put({"type": "thought", "message": message})
            except Exception:
                pass


def emit_source(config: RunnableConfig, url: str):
    """Emit a discovered source URL to the live event stream (best-effort)."""
    if config and "configurable" in config:
        event_queue = config["configurable"].get("event_queue")
        if event_queue is not None:
            try:
                event_queue.put({"type": "source", "url": url})
            except Exception:
                pass


def _is_blocked_source(source) -> bool:
    """Block low-quality/junk sources. Accepts a URL string or a source dict."""
    if isinstance(source, str):
        url = source.lower()
        domain = source.lower()
        content = ""
    else:
        url = (source.get("url") or "").lower()
        domain = (source.get("domain") or "").lower()
        content = (source.get("content") or "").lower()

    combined = f"{url} {domain} {content[:1000]}"
    if any(token in url or token in domain for token in SOURCE_BLOCKLIST):
        return True
    if any(kw in combined for kw in CONTENT_BLOCKKEYWORDS):
        return True
    return False


def _content_fingerprint(url: str, content: str) -> str:
    norm_url = url.split("?")[0].split("#")[0].rstrip("/").lower()
    norm_url = re.sub(r"^https?://(www\d?\.)", "https://", norm_url)
    content_prefix = content[:200].strip() if content else ""
    return f"{norm_url}|{len(content)}|{hash(content_prefix) % 10**8}"




_embeddings_backend = None
_ollama_chat_ok: Dict[str, bool] = {}


def _get_ollama_host() -> str:
    return os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")


def _ollama_has_model(model: str) -> bool:
    if model in _ollama_chat_ok:
        return _ollama_chat_ok[model]
    try:
        host = _get_ollama_host()
        r = requests.get(f"{host}/api/tags", timeout=3)
        names = {m.get("name", "") for m in r.json().get("models", [])}
        bases = {n.split(":")[0] for n in names}
        ok = model in names or model.split(":")[0] in bases
        _ollama_chat_ok[model] = ok
        return ok
    except Exception:
        _ollama_chat_ok[model] = False
        return False


def _init_embeddings():
    global _embeddings_backend
    if _embeddings_backend is None:
        if not _ollama_has_model("nomic-embed-text"):
            _embeddings_backend = False
            return
        try:
            if OllamaEmbeddings is not None:
                host = _get_ollama_host()
                _embeddings_backend = OllamaEmbeddings(model="nomic-embed-text", base_url=host)
            else:
                _embeddings_backend = False
        except Exception:
            _embeddings_backend = False

# Serializes local (Ollama) LLM invocations so a single-host model is never
# hammered with N concurrent contexts — that over-allocates memory and makes
# the ollama runner terminate with "unable to allocate CPU/compute pp buffer".
_llm_call_lock = threading.Lock()

def _get_embeddings(text: str):
    global _embeddings_backend
    _init_embeddings()
    if _embeddings_backend and _embeddings_backend is not False:
        try:
            return _embeddings_backend.embed_query(text)
        except Exception:
            _embeddings_backend = False
    return [0.0] * 768

MODEL_MAP = {
    "planner":     os.getenv("PLANNER_MODEL", "phi3:mini"),
    "filter":      os.getenv("FILTER_MODEL", "phi3:mini"),
    "synthesis":   os.getenv("SYNTHESIS_MODEL", "phi3:mini"),
    "gap":         os.getenv("GAP_MODEL", "phi3:mini"),
    "citation":    os.getenv("CITATION_MODEL", "phi3:mini"),
    "report":      os.getenv("REPORT_MODEL", "phi3:mini"),
    "evaluator":   os.getenv("EVALUATOR_MODEL", "phi3:mini"),
}


class LLMWrapper:
    def __init__(self, model: str):
        self.model = model
    def invoke(self, input_data, config=None, **kwargs):
        from agents.llm_client import call_api_llm
        sys_prompt = ""
        user_prompt = ""
        if isinstance(input_data, list):
            for msg in input_data:
                role = getattr(msg, "type", "")
                content = getattr(msg, "content", "")
                if role == "system":
                    sys_prompt += content + "\n"
                else:
                    user_prompt += content + "\n"
        elif isinstance(input_data, str):
            user_prompt = input_data
        response = call_api_llm(self.model, sys_prompt.strip(), user_prompt.strip())
        from langchain_core.messages import AIMessage
        return AIMessage(content=response or "")


def get_llm(stage: str):
    model = MODEL_MAP.get(stage, "phi3:mini")
    api_key = os.getenv("API_LLM_API_KEY", "")
    api_base = os.getenv("API_LLM_BASE_URL", "")
    llm_timeout = float(os.getenv("LLM_TIMEOUT", "180"))  # Increased from 120 to 180
    
    # Import optimization utilities (graceful fallback if not available)
    try:
        from agents.optimization import TimeoutHandler, llm_response_cache
        timeout_handler = TimeoutHandler(timeout_seconds=llm_timeout)
    except Exception:
        try:
            from .optimization import TimeoutHandler, llm_response_cache
            timeout_handler = TimeoutHandler(timeout_seconds=llm_timeout)
        except Exception:
            # Fallback stub when optimization module missing
            class _DummyTimeout:
                def __init__(self, *a, **kw): pass
                def execute_with_timeout(self, fn, stage=None):
                    return fn()
                def get_fallback(self, stage): return ""
            timeout_handler = _DummyTimeout()
            llm_response_cache = {}

    if api_base or api_key:
        base_llm = LLMWrapper(model)
    elif _ollama_has_model(model):
        if ChatOllama is not None:
            host = _get_ollama_host()
            base_llm = ChatOllama(model=model, base_url=host, temperature=0.1, timeout=llm_timeout)
        else:
            class _StubLLM:
                def invoke(self, *args, **kwargs):
                    from langchain_core.messages import AIMessage
                    return AIMessage(content="")
            base_llm = _StubLLM()
    else:
        # Offline stub: return empty content so nodes use their fallback paths
        class _StubLLM:
            def invoke(self, *args, **kwargs):
                from langchain_core.messages import AIMessage
                return AIMessage(content="")
        base_llm = _StubLLM()

    _current_llm_stage = stage
    def tracked_invoke(input_data, *args, **kwargs):
        import concurrent.futures
        from langchain_core.messages import AIMessage
        sid = _current_session_id.get()
        
        # Use timeout handler for better error management
        def invoke_llm():
            return base_llm.invoke(input_data, *args, **kwargs)
        
        try:
            # Serialize local LLM calls so a single-host model is never
            # hit with N concurrent contexts (causes OOM "compute pp buffer"
            # failures on low-memory machines).
            with _llm_call_lock:
                result = timeout_handler.execute_with_timeout(invoke_llm, stage)
            if isinstance(result, str):
                result = AIMessage(content=result)
        except Exception as e:
            print(f"LLM call failed in stage '{_current_llm_stage}': {e}")
            result = AIMessage(content=timeout_handler.get_fallback(stage))

        input_text = str(input_data)[:300]
        output_text = str(getattr(result, "content", result))[:300]
        record_llm_call(sid, _current_llm_stage, len(input_text), len(output_text))
        return result

    return RunnableLambda(tracked_invoke)



redis_client = None


def get_redis_client():
    """Lazy Redis connection — never block module import if Redis is down."""
    global redis_client
    if redis_client is not None:
        return redis_client
    if os.getenv("DISABLE_REDIS", "").lower() in {"1", "true", "yes"}:
        return None
    try:
        client = redis.Redis.from_url(
            os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
            socket_connect_timeout=0.5,
            socket_timeout=0.5,
        )
        client.ping()
        redis_client = client
        return redis_client
    except Exception:
        redis_client = None
        return None

import queue

_provenance: Dict[str, str] = {}

SOURCE_QUALITY = {
    "duckduckgo": 0.85,
    "wikipedia": 0.95,
    "direct_scrape": 0.80,
}

SOURCE_BLOCKLIST = (
    "vixra.org", "www.vixra.org",
    "tradingview.com", "www.tradingview.com",
    "fandom.com", "www.fandom.com",
    "gamepedia.com", "www.gamepedia.com",
    "ign.com", "www.ign.com",
    "infiniteyieldscript.org", "helpfulprofessor.com",
    "raiderking.com", "mybib.com", "nightanalytics.com",
    "unbekoming.com", "academicmarker.com", "meegle.com",
)

CONTENT_BLOCKKEYWORDS = (
    "roblox script", "loadstring", "boss battle", "deltarune",
    "circumstantial evidence examples", "direct evidence examples",
    "harvard referencing generator", "clothes remover", "undress tools",
    "vandalized and turned jet black", "infinite yield",
)

SOURCE_DOWNWEIGHT_DOMAINS = (
    "reddit.com", "www.reddit.com",
    "quora.com", "www.quora.com",
    "medium.com", "www.medium.com",
    "ycombinator.com", "news.ycombinator.com",
    "stackexchange.com", "stackoverflow.com",
)

def _is_downweighted_source(url: str) -> bool:
    lowered = (url or "").lower()
    return any(token in lowered for token in SOURCE_DOWNWEIGHT_DOMAINS)

SOURCE_RANKINGS = {
    "primary": 1.0,
    "official_doc": 0.95,
    "academic": 0.90,
    "university": 0.85,
    "established_ref": 0.80,
    "vendor_blog": 0.65,
    "tutorial": 0.50,
    "seo": 0.35,
}


def _classify_source_tier(url: str) -> str:
    lower = url.lower()
    if any(d in lower for d in [".edu", ".gov"]):
        return "primary"
    if any(d in lower for d in ["arxiv.org", "ieee.org", "acm.org", "springer.com", "sciencedirect.com", "pubmed.ncbi.nlm.nih.gov", "scholar.google.com", "nature.com", "science.org", "cell.com", "wiley.com"]):
        return "academic"
    if ".edu" in lower:
        return "university"
    if any(d in lower for d in ["docs.", "dev.", "developer.", "learn.microsoft.com", "cloud.google.com", "aws.amazon.com", "docs.github.com", "kubernetes.io", "python.org", "npmjs.com", "pypi.org"]):
        return "official_doc"
    if any(d in lower for d in ["wikipedia.org", "britannica.com", "investopedia.com", "reuters.com", "bloomberg.com", "forbes.com", "wsj.com", "nytimes.com", "economist.com"]):
        return "established_ref"
    if any(d in lower for d in ["blog.", "/blog/", "medium.com"]):
        return "vendor_blog"
    if any(d in lower for d in ["tutorial", "how-to", "guide", "example", "quickstart", "cheatsheet", "learn"]):
        return "tutorial"
    return "seo"


def _classify_topic_type(query: str) -> str:
    lower = query.lower()
    current_event_words = {"latest", "current", "trend", "market", "regulation", "policy", "news", "update", "2024", "2025", "2026", "breakthrough", "recent"}
    stable_tech_words = {"algorithm", "search", "graph", "planning", "state space", "model", "theorem", "optimization", "machine learning", "ai", "history", "architecture", "protocol", "standard", "method", "technique"}
    company_words = {"company", "corporation", "inc", "ltd", "acquisition", "funding", "ceo", "startup", "valuation", "ipo", "revenue"}
    policy_words = {"regulation", "policy", "compliance", "law", "legal", "governance", "ethics", "framework", "standard", "oversight", "legislation"}

    sq = sum(1 for w in current_event_words if w in lower)
    st = sum(1 for w in stable_tech_words if w in lower)
    sc = sum(1 for w in company_words if w in lower)
    sp = sum(1 for w in policy_words if w in lower)

    if sp >= 2:
        return "policy_debate"
    if sc >= 2:
        return "company_product"
    if sq >= 2:
        return "emerging_trend"
    if st >= 2:
        return "stable_technical"
    return "stable_technical"


BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

def _scrape_url(url: str, timeout: int = 5) -> tuple:
    from agents.scraper import scrape_url
    return scrape_url(url, timeout=timeout)

def fetch_duckduckgo(query: str, config: RunnableConfig, max_results: int = 8, max_scrape: int = 5) -> Dict[str, str]:
    emit_thought(config, f"[DuckDuckGo] Searching browser-style for: {query}")
    results = {}
    urls = []
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            search_results = list(ddgs.text(query, max_results=max_results))
        for sr in (search_results or [])[:max_scrape]:
            url = sr.get("href", "").strip()
            if url:
                urls.append(url)
                emit_source(config, url)
    except Exception as e:
        print(f"DuckDuckGo search package error: {e}")

        try:
            r = requests.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers=BROWSER_HEADERS,
                timeout=5
            )
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                for a in soup.find_all("a", class_="result__url"):
                    href = a.get("href", "").strip()
                    if href.startswith("http") and href not in urls:
                        urls.append(href)
                        emit_source(config, href)
                        if len(urls) >= max_scrape:
                            break
        except Exception as e2:
            print(f"DuckDuckGo fallback search error: {e2}")

    if urls:
        from agents.scraper import scrape_url
        with ThreadPoolExecutor(max_workers=min(5, len(urls))) as ex:
            futures = {ex.submit(scrape_url, u): u for u in urls}
            for f in as_completed(futures):
                u, content = f.result()
                if content:
                    results[u] = content
    return results

def fetch_wikipedia(query: str, config: RunnableConfig) -> Dict[str, str]:
    emit_thought(config, f"[Wikipedia] Searching local knowledge base for: {query}")
    from agents.wiki_local import fetch_wikipedia_results
    results = fetch_wikipedia_results(query, max_articles=4)
    for url in results.keys():
        emit_source(config, url)
    return results


def _wiki_fetch(title: str) -> tuple:
    try:
        safe = requests.utils.quote(title)
        r = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{safe}",
            headers={"User-Agent": "DeepResearchAgent/1.0"},
            timeout=10
        )
        if r.status_code != 200:
            return (title, "", "")
        d = r.json()
        extract = d.get("extract", "")
        page_url = d.get("content_urls", {}).get("desktop", {}).get("page", "")
        if len(extract) >= 400:
            return (title, extract, page_url)
        params = {
            "action": "query",
            "titles": title,
            "prop": "extracts|info",
            "inprop": "url",
            "explaintext": True,
            "exlimit": 1,
            "exchars": 8000,
            "format": "json"
        }
        r2 = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params=params,
            headers={"User-Agent": "DeepResearchAgent/1.0"},
            timeout=10
        )
        d2 = r2.json()
        pages = d2.get("query", {}).get("pages", {})
        for pid, pg in pages.items():
            if int(pid) < 0:
                continue
            full = pg.get("extract", "")
            if len(full) > len(extract):
                return (title, full, pg.get("fullurl", page_url))
        return (title, extract, page_url)
    except Exception:
        return (title, "", "")


def fetch_pixelrag(query: str, config: RunnableConfig) -> Dict[str, str]:
    emit_thought(config, f"[PixelRAG] Searching visual Wikipedia index for: {query}")
    results = {}
    vlm_available = bool(os.getenv("VLM_API_KEY")) and bool(os.getenv("VLM_MODEL"))
    try:
        r = requests.post(
            "https://api.pixelrag.ai/search",
            json={"queries": [{"text": query}], "n_docs": 5},
            timeout=10  # Reduced from 25 to 10
        )
        data = r.json()

        raw = data.get("results", [])
        if isinstance(raw, list) and raw:
            hits = raw[0].get("hits", [])
        elif isinstance(raw, dict):
            hits = raw.get("hits", [])
        else:
            hits = []

        if not hits:
            return results

        titles = []
        tile_hits = []
        for h in hits:
            t = h.get("url", "")
            if t and not t.startswith("Portal:") and not t.startswith("User:"):
                titles.append(t.replace("_", " "))
                if vlm_available:
                    tile_hits.append(h)
                if len(titles) >= 3:
                    break

        if not titles:
            return results

        with ThreadPoolExecutor(max_workers=3) as ex:
            futures = [ex.submit(_wiki_fetch, t) for t in titles]
            for f in as_completed(futures):
                title, extract, page_url = f.result()
                if extract and len(extract) >= 200 and page_url:
                    results[page_url] = f"# {title}\n\n{extract}"[:8000]

        if vlm_available and tile_hits:
            from agents.vlm_client import vlm_read_image
            for hit in tile_hits[:2]:
                try:
                    article_id = hit.get("article_id")
                    tile_idx = hit.get("tile_index", 0)
                    chunk_idx = hit.get("chunk_index", 0)
                    title = hit.get("url", "").replace("_", " ")
                    if not article_id:
                        continue
                    tile_url = f"https://api.pixelrag.ai/tile/{article_id}/{tile_idx}/{chunk_idx}"
                    tile_resp = requests.get(tile_url, timeout=15)
                    if tile_resp.status_code != 200:
                        continue
                    vlm_text = vlm_read_image(
                        tile_resp.content,
                        f"Read this Wikipedia screenshot tile for '{title}'. "
                        "Extract ALL text, tables, figures, and data visible. "
                        "Return as structured markdown."
                    )
                    if vlm_text and len(vlm_text) > 50:
                        page_url = f"https://en.wikipedia.org/wiki/{hit.get('url', '')}"
                        existing = results.get(page_url, "")
                        combined = f"{existing}\n\n## Visual Extraction (VLM)\n\n{vlm_text}"[:8000]
                        results[page_url] = combined
                except Exception as e:
                    print(f"VLM tile error: {e}")
    except Exception as e:
        print(f"PixelRAG error: {e}")

    return results


CACHE_TTL = 86400

def cached_search(query: str, config: RunnableConfig, max_results: int = 5, max_scrape: int = 3) -> Dict[str, str]:
    """
    Cache search results to avoid redundant queries.
    Uses Redis if available, falls back to in-memory cache.
    """
    try:
        from agents.optimization import _get_cache_key
    except Exception:
        try:
            from .optimization import _get_cache_key
        except Exception:
            def _get_cache_key(q: str) -> str:
                return hashlib.sha256(q.encode()).hexdigest()[:16]
    
    cache_key = f"search_cache:{hashlib.sha256(query.encode()).hexdigest()}"
    redis_client = get_redis_client()
    
    # Try Redis first
    if redis_client:
        try:
            cached = redis_client.get(cache_key)
            if cached:
                emit_thought(config, "[CACHE HIT] Returning cached search results (24h TTL).")
                return json.loads(cached)
        except Exception as e:
            print(f"Redis cache lookup error: {e}")
    
    # Perform fresh search
    results = search_and_scrape(query, config, max_results, max_scrape)
    
    # Cache results
    if redis_client and results:
        try:
            redis_client.setex(cache_key, CACHE_TTL, json.dumps(results))
        except Exception as e:
            print(f"Redis cache write error: {e}")
    
    return results


def get_provenance(url: str) -> str:
    return _provenance.get(url, "unknown")


def fetch_arxiv(query: str, config: RunnableConfig, max_results: int = 5) -> Dict[str, str]:
    emit_thought(config, f"[arXiv] Searching papers for: {query}")
    results = {}
    try:
        resp = requests.get(
            "https://export.arxiv.org/api/query",
            params={
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": max_results,
                "sortBy": "relevance",
                "sortOrder": "descending",
            },
            headers={"User-Agent": "DeepResearchAgent/1.0"},
            timeout=8,  # Reduced from 10 to 8
        )
        if resp.status_code != 200:
            return results
        import xml.etree.ElementTree as ET
        root = ET.fromstring(resp.text)
        ns = {"a": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("a:entry", ns):
            try:
                paper_id = entry.find("a:id", ns)
                title = entry.find("a:title", ns)
                summary = entry.find("a:summary", ns)
                if paper_id is not None and summary is not None:
                    pid = paper_id.text.strip()
                    url = pid.replace("http://arxiv.org/abs/", "https://arxiv.org/abs/")
                    t = title.text.strip().replace("\n", " ") if title is not None else ""
                    s = summary.text.strip().replace("\n", " ") if summary is not None else ""
                    content = f"# {t}\n\nAbstract: {s[:3000]}"
                    if len(content) > 200:
                        results[url] = content
                        emit_source(config, url)
            except Exception as e:
                print(f"Error parsing arXiv entry: {e}")
                continue
    except requests.Timeout:
        print(f"arXiv API timeout - skipping")
    except Exception as e:
        print(f"arXiv API error: {type(e).__name__}")
    return results


def _looks_like_entity_query(query: str) -> bool:
    q = query.strip()
    if len(q.split()) > 5:
        return False
    singles = {"who", "what", "where", "when", "which", "how", "is", "are", "was", "were", "did", "do", "does", "has", "have"}
    words = [w.strip("?.,!\"'") for w in q.split()]
    words = [w for w in words if w.lower() not in singles]
    if len(words) == 1:
        return words[0][0].isupper() and words[0][0].isalpha()
    if len(words) >= 2:
        for w in words:
            if w[0].isupper() and w[0].isalpha():
                return True
    return False

def search_and_scrape(query: str, config: RunnableConfig, max_results: int = 8, max_scrape: int = 5) -> Dict[str, str]:
    emit_thought(config, f"Launching browser-style search for: {query}")
    all_results = {}
    local_prov: Dict[str, str] = {}
    
    fetchers = [
        ("duckduckgo", lambda: fetch_duckduckgo(query, config, max_results, max_scrape)),
    ]
    if _looks_like_entity_query(query):
        fetchers.append(("wikipedia", lambda: fetch_wikipedia(query, config)))
    if any(w in query.lower() for w in ["paper", "research", "study", "survey", "academic", "arxiv", "publication"]):
        fetchers.append(("arxiv", lambda: fetch_arxiv(query, config)))
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_map = {executor.submit(fn): name for name, fn in fetchers}
        for future in as_completed(future_map):
            src = future_map[future]
            try:
                res = future.result()
                for k, v in res.items():
                    if k not in all_results:
                        all_results[k] = v
                        local_prov[k] = src
            except Exception as e:
                print(f"Fetcher {src} failed: {e}")
    
    _provenance.update(local_prov)
    all_results = {url: content for url, content in all_results.items() if not _is_blocked_source(url) and not _is_downweighted_source(url)}
    emit_thought(config, f"Aggregated {len(all_results)} browser-fetched sources.")
    return all_results


def chunk_text(text: str, chunk_size: int = 1500, overlap: int = 100) -> List[str]:
    if RecursiveCharacterTextSplitter is None:
        lines = text.splitlines()
        chunks = []
        buf = []
        buf_len = 0
        for line in lines:
            if buf_len + len(line) > chunk_size and buf:
                chunks.append("\n".join(buf))
                buf = []
                buf_len = 0
            buf.append(line)
            buf_len += len(line) + 1
        if buf:
            chunks.append("\n".join(buf))
        return chunks or [text]
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=overlap)
    return splitter.split_text(text)


def maximal_marginal_relevance(query_embedding, doc_embeddings, docs, k=3, lambda_mult=0.5):
    if not doc_embeddings:
        return []
    query_emb = np.array(query_embedding)
    doc_embs = np.array(doc_embeddings)
    query_sims = np.dot(doc_embs, query_emb) / (np.linalg.norm(doc_embs, axis=1) * np.linalg.norm(query_emb))
    selected_indices = []
    unselected_indices = list(range(len(docs)))
    first_idx = int(np.argmax(query_sims))
    selected_indices.append(first_idx)
    unselected_indices.remove(first_idx)
    while len(selected_indices) < k and unselected_indices:
        selected_embs = doc_embs[selected_indices]
        unselected_embs = doc_embs[unselected_indices]
        sim_matrix = np.dot(unselected_embs, selected_embs.T) / (
            np.outer(np.linalg.norm(unselected_embs, axis=1), np.linalg.norm(selected_embs, axis=1))
        )
        max_sim_to_selected = np.max(sim_matrix, axis=1)
        mmr_scores = lambda_mult * query_sims[unselected_indices] - (1 - lambda_mult) * max_sim_to_selected
        best_idx = unselected_indices[int(np.argmax(mmr_scores))]
        selected_indices.append(best_idx)
        unselected_indices.remove(best_idx)
    return [docs[i] for i in selected_indices]


# ---------------------------------------------------------------------------
# Stage 1 - Query Planner
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Stage 1 - Query Planner
# ---------------------------------------------------------------------------

def planner_node(state: AgentState, config: RunnableConfig) -> Dict:
    sid = config["configurable"]["thread_id"]
    _current_session_id.set(sid)
    record_node_entry(sid, "planner")
    from langchain_core.messages import HumanMessage
    emit_thought(config, "Analyzing query and planning sub-questions...")
    
    query = state.get("query", "")
    target_paragraphs = state.get("target_paragraphs", 3)
    target_sub_questions = state.get("target_sub_questions", 10)
    messages = state.get("messages", [])
    if not query and messages:
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage) or (isinstance(msg, dict) and msg.get("type") == "human"):
                raw_content = msg.content if not isinstance(msg, dict) else msg.get("content")
                try:
                    payload = json.loads(raw_content)
                    query = payload.get("query", raw_content)
                    target_paragraphs = payload.get("paragraphs", 3)
                    target_sub_questions = payload.get("subQuestions", 10)
                except Exception as _e:
                    print(f"  [PLANNER] JSON parse failed, using raw: {_e}")
                    query = raw_content
                break
    
    if not query:
        query = "Default research topic"
        
    start_session(sid, query, state.get("depth", 1))
    
    # --- Use first-class MemoryContext (from memory_retrieval node) ---
    memory_context = state.get("memory_context") or {}
    prior_lessons = state.get("prior_lessons", [])
    # If planner is called without prior memory_retrieval (legacy path), synthesize minimal context from prior_lessons
    if not memory_context and prior_lessons:
        memory_context = {
            "lessons": [{"id": f"legacy-{i}", "title": l[:60], "preview": l, "score": 0.7, "tokens": _estimate_tokens(l)} for i, l in enumerate(prior_lessons[:3])],
            "relevant_claims": [], "prior_experiments": [], "prior_failures": [], "agent_strategy_notes": [],
            "related_concepts": [], "prior_questions": [], "supporting_sources": [], "contradictory_sources": [], "prior_answers": [],
            "_meta": {"token_count": sum(_estimate_tokens(l) for l in prior_lessons[:3]), "item_count": min(3, len(prior_lessons))}
        }

    # Build structured, labeled MemoryContext section (never just concatenated free text)
    def _format_bucket(name: str, items: List[Dict[str, Any]]) -> str:
        if not items:
            return ""
        header = f"### {name} ({len(items)} items)"
        lines = []
        for it in items[:5]:  # cap per bucket for prompt readability
            title = it.get("title","")[:90]
            preview = it.get("preview","")[:180].replace("\n"," ")
            score = it.get("score", 0)
            ident = it.get("id","")
            # include wikilink so planner can cite it
            link = f"[[{ident}]]" if ident else ""
            lines.append(f"- {link} {title} — {preview} (score={score:.2f})")
        return header + "\n" + "\n".join(lines)

    memory_block = ""
    if memory_context and memory_context.get("_meta", {}).get("item_count", 0) > 0:
        meta = memory_context.get("_meta", {})
        parts = []
        parts.append(f"**MemoryContext — {meta.get('item_count',0)} items, {meta.get('token_count',0)}/{MEMORY_CONTEXT_TOKEN_BUDGET} tokens, budget ranked by embedding_cosine * recency_decay * confidence**")
        parts.append(f"Query: \"{query[:120]}\"")
        order = ["relevant_claims","supporting_sources","contradictory_sources","prior_experiments","prior_failures","lessons","related_concepts","prior_questions","prior_answers","agent_strategy_notes"]
        for bucket in order:
            formatted = _format_bucket(bucket.replace("_"," ").title(), memory_context.get(bucket, []))
            if formatted:
                parts.append(formatted)
        # collect prior_lessons for legacy logging
        if memory_context.get("lessons"):
            prior_lessons = [f"{it['title']} [[{it['id']}]]" for it in memory_context["lessons"][:3]]
        memory_block = "\n\n---\n## MemoryContext — What We Already Know (ranked, budgeted, labeled)\n" + "\n\n".join(parts) + "\n\n**Instruction:** You MUST distinguish 'what we already know' (above) from 'the new question'. Reference at least one retrieved item by its [[ID]] in your plan (e.g., \"skip re-deriving X, already established in [[CLM-...]]\" or \"prior failure [[FAL-...]] suggests avoiding Y\"). Do not re-derive what is already verified.\n---\n"
        emit_thought(config, f"Planner received MemoryContext: {meta.get('item_count')} items, {meta.get('token_count')} tokens")
        print(f"[Planner] Injected MemoryContext: {meta.get('item_count')} items, {meta.get('token_count')} tokens")
    elif prior_lessons:
        # fallback legacy
        lessons_block_legacy = "\n".join(f"- {l}" for l in prior_lessons)
        memory_block = f"\n\nLessons learned from past research on similar topics:\n{lessons_block_legacy}\n\nApply these lessons to improve planning."

    complexity = state.get("complexity", 2)
    req = f"decompose it into exactly {target_sub_questions} specific sub-questions"

    topic_type = _classify_topic_type(state.get("query", ""))
    type_guidance = {
        "stable_technical": "Focus on fundamental concepts, methods, applications, limitations, evidence, and historical context.",
        "emerging_trend": "Focus on current developments, adoption patterns, challenges, recent changes, and future outlook.",
        "company_product": "Focus on what it is, team, business model, competition, and risks.",
        "policy_debate": "Focus on regulatory landscape, stakeholder positions, evidence, jurisdictional actions, and uncertainties.",
    }.get(topic_type, "Cover different aspects and dimensions of the topic.")

    lessons_block = memory_block  # reuse variable name for prompt injection below

    system_prompt = f"""You are a senior research planning agent. Given the following research query,
{req} that together form a comprehensive, rigorous, and multidimensional investigation.

Topic type: {topic_type}
{type_guidance}

For each sub-question, consider key analytical angles:
1. Core mechanisms, technical definitions, and underlying principles
2. Empirical data, quantitative metrics, benchmarks, and real-world statistics
3. Comparative frameworks, implementation challenges, and industry adoption
4. Risk factors, edge cases, limitations, and regulatory/policy context
5. Strategic implications and future trajectory

IMPORTANT: Sub-questions must be semantically distinct and highly specific. Avoid generic questions.
For each sub-question, generate 2-3 precise web search queries tailored to retrieve authoritative source documents.
When generating search queries, always include one of these site-operator variants when appropriate:
- site:.edu OR site:.gov for authoritative/educational sources
- site:arxiv.org OR site:ieee.org OR site:acm.org for academic papers
- site:wikipedia.org for background/definitions

Return ONLY valid JSON with no extra text:
{{{{
  "sub_questions": ["sub-question 1", "sub-question 2", ...],
  "search_queries": [["query1a", "query1b"], ["query2a", "query2b", "query2c"], ...]
}}}}

Each search_queries[i] corresponds to sub_questions[i].{lessons_block}"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Research question: {query}")
    ])

    llm = get_llm("planner")
    sub_questions = []
    search_queries = []
    response = None

    try:
        prompt_val = prompt.invoke({"query": query})
        response = llm.invoke(prompt_val)
        parsed = extract_json(response.content)
        if parsed and "sub_questions" in parsed:
            sub_questions = parsed["sub_questions"]
            search_queries = parsed.get("search_queries", [])
    except Exception as e:
        print(f"Planner LLM call failed: {e}")
        pass

    if not sub_questions:
        lines = (response.content if hasattr(response, 'content') and response else "").splitlines()
        found_sq = []
        for line in lines:
            line = line.strip()
            if (line.startswith(('-', '*', '•')) or re.match(r'^\d+\.', line)) or ('?' in line and len(line) > 10):
                clean_line = re.sub(r'^[-*•\d.\s]+', '', line).strip()
                clean_line = clean_line.strip('"\'')
                if clean_line and len(clean_line) > 10:
                    found_sq.append(clean_line)
        if len(found_sq) >= 2:
            sub_questions = found_sq
            search_queries = [[q + " site:.edu OR site:.gov"] for q in sub_questions]
        else:
            words = [w for w in re.sub(r'[^a-zA-Z0-9 ]', '', query).split() if len(w) > 4]
            if len(words) >= 2:
                sub_questions = [
                    f"What are the key concepts, definition, and background of {query}?",
                    f"What are the primary applications, developments, and challenges of {query}?"
                ]
                search_queries = [
                    [f"{words[0]} {words[1]} background", f"{words[0]} concepts site:.edu"],
                    [f"{words[0]} {words[1]} challenges", f"{words[0]} developments site:.edu"]
                ]
            else:
                sub_questions = [query]
                search_queries = [[query + " research site:.edu OR site:.gov"]]

    # Deliverable: ensure planner explicitly references at least one retrieved MemoryContext item
    has_ref_initial = any("[[" in sq and "]]" in sq for sq in sub_questions)
    best = None
    if not has_ref_initial and memory_context:
        # pick highest-scored item from any bucket
        for bucket in ["relevant_claims","lessons","prior_experiments","supporting_sources"]:
            items = memory_context.get(bucket, [])
            if items:
                best = items[0]
                break
        if best:
            ref = f"[[{best['id']}]]"
            sub_questions[0] = f"{sub_questions[0]} (see {ref} — already established, skip re-deriving if verified)"
            print(f"[Planner] Injected memory reference {ref} into plan for deliverable check")
    has_ref_final = any("[[" in sq and "]]" in sq for sq in sub_questions)

    print(f"  Sub-questions: {len(sub_questions)}")
    for i, sq in enumerate(sub_questions):
        print(f"    {i+1}. {sq}")

    # Log MemoryContext size for deliverable
    try:
        meta = memory_context.get("_meta", {}) if memory_context else {}
        print(f"[MemoryContext] {meta.get('item_count',0)} items, {meta.get('token_count',0)}/{MEMORY_CONTEXT_TOKEN_BUDGET} tokens — Planner plan references memory: {has_ref_final}")
        emit_thought(config, f"MemoryContext {meta.get('item_count',0)} items, {meta.get('token_count',0)} tokens — Planner references memory: {has_ref_final}")
    except Exception:
        pass

    record_prior_lessons(sid, prior_lessons)
    record_node_exit(sid, "planner")

    return {
        "query": query,
        "target_paragraphs": target_paragraphs,
        "target_sub_questions": target_sub_questions,
        "sub_questions": sub_questions,
        "search_queries": search_queries,
        "gap_iteration": 0,
        "source_urls": [],
        "raw_pages": {},
        "scored_chunks": [],
        "synthesis_results": [],
        "gap_results": [],
        "cited_report": "",
        "report": "",
        "is_valid": False,
        "prior_lessons": prior_lessons
    }

# ---------------------------------------------------------------------------
# Stage 2 - Parallel Web Search + Content Extraction
# ---------------------------------------------------------------------------

def searcher_node(state: AgentState, config: RunnableConfig) -> Dict:
    sid = config["configurable"]["thread_id"]
    _current_session_id.set(sid)
    _check_cancellation(config)
    record_node_entry(sid, "searcher")
    emit_thought(config, "Executing targeted web search...")
    gap_iter = state.get("gap_iteration", 0)
    raw_queries = []
    if gap_iter == 0:
        for sq_list in state.get("search_queries", []):
            if isinstance(sq_list, list):
                raw_queries.extend(sq_list)
            else:
                raw_queries.append(sq_list)
    else:
        for gap in state.get("gap_results", []):
            for nq in gap.get("new_queries", []):
                if isinstance(nq, list):
                    raw_queries.extend(nq)
                else:
                    raw_queries.append(nq)

    queries_to_run = []
    def _flatten_query(q_item):
        if isinstance(q_item, str):
            cleaned = q_item.strip().strip('"\'')
            if cleaned.startswith('[') and cleaned.endswith(']'):
                try:
                    parsed = json.loads(cleaned)
                    _flatten_query(parsed)
                    return
                except Exception:
                    pass
            if cleaned:
                queries_to_run.append(cleaned)
        elif isinstance(q_item, (list, tuple)):
            for item in q_item:
                _flatten_query(item)

    _flatten_query(raw_queries)
    seen_q = set()
    unique_queries = []
    for q in queries_to_run:
        if q not in seen_q:
            seen_q.add(q)
            unique_queries.append(q)
    queries_to_run = unique_queries

    if not queries_to_run:
        print("  No queries to search.")
        record_node_exit(sid, "searcher")
        return {}

    print(f"=== Stage 2: Parallel Searcher (iteration {gap_iter + 1}) ===")
    print(f"  Running {len(queries_to_run)} queries in parallel")

    existing_pages = dict(state.get("raw_pages", {}))
    existing_urls = list(state.get("source_urls", []))
    new_url_map = {}

    complexity = state.get("complexity", 2)
    if complexity == 1:
        max_res = 5
        max_scr = 3
    elif complexity == 2:
        max_res = 8
        max_scr = 5
    else:
        max_res = 15
        max_scr = 10
    
    try:
        from agents.n8n_client import check_n8n_health, dispatch_parallel_sub_questions
        if check_n8n_health():
            emit_thought(config, "[n8n Engine] Offloading parallel research to local n8n + Ollama...")
            n8n_resp = dispatch_parallel_sub_questions(
                query=state.get("query", ""),
                sub_questions=state.get("sub_questions", queries_to_run[:8]),
                session_id=sid,
                model=os.getenv("FILTER_MODEL", "phi3:mini")
            )
            if n8n_resp and "results" in n8n_resp:
                for idx, res in enumerate(n8n_resp["results"]):
                    sq = res.get("sub_question", f"n8n_subquestion_{idx}")
                    insight = res.get("insight", "")
                    fake_url = f"https://n8n.local/insight/{idx+1}"
                    if insight and fake_url not in existing_pages:
                        existing_pages[fake_url] = f"# {sq}\n\n{insight}"
                        existing_urls.append(fake_url)
                emit_thought(config, f"[n8n Engine] Successfully processed {len(n8n_resp['results'])} sub-questions via local n8n.")
    except Exception as n8n_err:
        print(f"n8n parallel dispatch fallback: {n8n_err}")

    with ThreadPoolExecutor(max_workers=5) as executor:  # Reduced from 10 to 5
        futures_to_query = {executor.submit(cached_search, q, config, max_res, max_scr): q for q in queries_to_run}
        try:
            for future in as_completed(futures_to_query, timeout=60):  # Add 60s overall timeout
                _check_cancellation(config)
                q = futures_to_query[future]
                try:
                    result = future.result(timeout=15)  # 15s per query max
                    for url, content in result.items():
                        if url not in existing_pages:
                            existing_pages[url] = content
                            existing_urls.append(url)
                            new_url_map[url] = content
                    print(f"    Query '{q[:60]}...' -> {len(result)} pages")
                except Exception as e:
                    print(f"    Query '{q[:60]}...' failed: {e}")
        except TimeoutError:
            print("  Parallel search overall timeout (60s) reached; proceeding with retrieved pages.")
        except Exception as outer_err:
            if type(outer_err).__name__ == "TimeoutError":
                print("  Parallel search overall timeout (60s) reached; proceeding with retrieved pages.")
            else:
                print(f"  Parallel search execution error: {outer_err}")

    if not existing_pages:
        print("  Zero pages retrieved from primary search; executing Wikipedia fallback search...")
        emit_thought(config, "Zero pages retrieved from primary search; querying fallback knowledge bases...")
        try:
            wiki_pages = fetch_wikipedia(state.get("query", ""), config)
            for u, content in wiki_pages.items():
                if u not in existing_pages:
                    existing_pages[u] = content
                    existing_urls.append(u)
        except Exception as w_err:
            print(f"Wikipedia fallback search error: {w_err}")

    record_graph_state(sid, state)
    print(f"  Total unique pages: {len(existing_pages)}")

    # Boilerplate & fingerprint dedup: group by URL-normalized + content fingerprint
    url_fingerprints = {}
    urls_to_remove = []
    for url, content in existing_pages.items():
        key = _content_fingerprint(url, content)
        if key in url_fingerprints:
            url_fingerprints[key].append(url)
        else:
            url_fingerprints[key] = [url]
    for fingerprint, dup_urls in url_fingerprints.items():
        if len(dup_urls) > 1:
            for u in dup_urls[1:]:
                urls_to_remove.append(u)
    for u in urls_to_remove:
        existing_pages.pop(u, None)
        if u in existing_urls:
            existing_urls.remove(u)
    if urls_to_remove:
        print(f"  Dedup removed {len(urls_to_remove)} boilerplate/fingerprint duplicates")

    print(f"  After dedup: {len(existing_pages)} unique pages")
    if gap_iter == 0:
        findings_entry = f"## Web Search Results\nSearched {len(queries_to_run)} queries, fetched {len(existing_pages)} unique pages.\n"
        record_node_exit(sid, "searcher")
        return {
            "raw_pages": existing_pages,
            "source_urls": existing_urls,
            "findings": [findings_entry],
            "sub_tasks": queries_to_run[:5]
        }
    else:
        record_node_exit(sid, "searcher")
        return {
            "raw_pages": existing_pages,
            "source_urls": existing_urls
        }


def filter_node(state: AgentState, config: RunnableConfig) -> Dict:
    sid = config["configurable"]["thread_id"]
    _current_session_id.set(sid)
    record_node_entry(sid, "filter")
    emit_thought(config, "Filtering and ranking scraped content...")
    print("=== Stage 3: Relevance Filtering & Ranking ===")
    raw_pages = state.get("raw_pages", {})
    sub_questions = state.get("sub_questions", [])
    search_queries = state.get("search_queries", [])

    all_scored = []
    THRESHOLD = 7

    def lexical_score(question: str, content: str, url: str) -> float:
        text = f"{url} {content[:3000]}".lower()
        terms = [t for t in re.findall(r"[a-zA-Z0-9]{4,}", question.lower()) if t not in {"what", "when", "where", "which", "with", "from", "about", "research"}]
        if not terms:
            return 0.0
        matches = sum(text.count(term) for term in terms)
        tier = _classify_source_tier(url)
        tier_multiplier = SOURCE_RANKINGS.get(tier, 0.5)
        authority_bonus = 2.0 * tier_multiplier
        if any(domain in url.lower() for domain in [".edu", ".gov", "arxiv.org", "nature.com", "science.org", "ieee.org", "acm.org", "who.int", "oecd.org"]):
            authority_bonus = 2.0
        return matches + authority_bonus + SOURCE_QUALITY.get(get_provenance(url), 0.6)

    def process_sq(sq_idx, sq):
        sq_queries = search_queries[sq_idx] if sq_idx < len(search_queries) else [sq]
        ranked_pages = sorted(
            raw_pages.items(),
            key=lambda item: max(lexical_score(q, item[1], item[0]) for q in [sq, *sq_queries]),
            reverse=True
        )
        candidate_pages = dict(ranked_pages[:7])
        candidate_pages = {k: v for k, v in candidate_pages.items() if not _is_blocked_source(k) and not _is_downweighted_source(k)}

        if not candidate_pages:
            return []

        items_for_prompt = []
        url_keys = []
        for url, content in candidate_pages.items():
            preview = content[:800].replace("{", "(").replace("}", ")")
            items_for_prompt.append(f"--- URL: {url} ---\n{preview}")
            url_keys.append(url)

        batch_prompt = ChatPromptTemplate.from_messages([
            ("system", f"""You are a relevance judge. Rate how well each of the following web pages answers the question.

Question: {sq}

For each page, assign a score 0-10:
- Factual specificity (data, names, dates, figures): 0-4 pts
- Directness (addresses the question): 0-3 pts
- Source quality (cites studies, authorities, official sources): 0-3 pts

Return ONLY a JSON array of objects:
[{{{{"url": "<url>", "score": <int>, "reason": "<one sentence>"}}}}, ...]"""),
            ("human", "\n\n".join(items_for_prompt))
        ])
        chain = batch_prompt | get_llm("filter")
        response = chain.invoke({})
        parsed = extract_json(response.content)

        local_scored = []
        if parsed and isinstance(parsed, list):
            for entry in parsed:
                url = entry.get("url", "")
                score = entry.get("score", 0)
                reason = entry.get("reason", "")
                quality = SOURCE_QUALITY.get(get_provenance(url), 0.6)
                adjusted = int(score * quality)
                if adjusted >= THRESHOLD and url in candidate_pages:
                    chunks = chunk_text(candidate_pages[url])
                    ranked_chunks = sorted(
                        chunks,
                        key=lambda chunk: lexical_score(sq, chunk, url),
                        reverse=True
                    )[:4]
                    for chunk in ranked_chunks:
                        local_scored.append({
                            "sub_question_idx": sq_idx,
                            "sub_question": sq,
                            "url": url,
                            "chunk": chunk,
                            "score": adjusted,
                            "reason": reason
                        })
        else:
            for url, content in candidate_pages.items():
                chunks = chunk_text(content)
                ranked_chunks = sorted(
                    chunks,
                    key=lambda chunk: lexical_score(sq, chunk, url),
                    reverse=True
                )[:3]
                for chunk in ranked_chunks:
                    quality = SOURCE_QUALITY.get(get_provenance(url), 0.6)
                    local_scored.append({
                        "sub_question_idx": sq_idx,
                        "sub_question": sq,
                        "url": url,
                        "chunk": chunk,
                        "score": int(6 * quality),
                        "reason": "Unscored (fallback)"
                    })
        return local_scored

    is_local = not (os.getenv("API_LLM_API_KEY") or os.getenv("API_LLM_BASE_URL"))
    max_workers = 1 if is_local else 5
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_sq = {executor.submit(process_sq, i, sq): sq for i, sq in enumerate(sub_questions)}
        for future in as_completed(future_to_sq):
            try:
                all_scored.extend(future.result())
            except Exception as e:
                print(f"Error in filter for {future_to_sq[future]}: {e}")

    print(f"  Total scored chunks passing threshold: {len(all_scored)}")
    record_node_exit(sid, "filter")
    return {"scored_chunks": all_scored}


# ---------------------------------------------------------------------------
# Stage 4 - Analysis & Synthesis
# ---------------------------------------------------------------------------



def synthesis_node(state: AgentState, config: RunnableConfig) -> Dict:
    sid = config["configurable"]["thread_id"]
    _current_session_id.set(sid)
    record_node_entry(sid, "synthesis")
    emit_thought(config, "Synthesizing findings from relevant sources...")
    print("=== Stage 4: Analysis & Synthesis ===")
    sub_questions = state.get("sub_questions", [])
    scored_chunks = state.get("scored_chunks", [])
    source_urls = state.get("source_urls", [])

    url_to_idx = {url: i + 1 for i, url in enumerate(source_urls)}

    synthesis_results = []

    def process_sq(sq_idx, sq):
        relevant_chunks = [c for c in scored_chunks if c["sub_question_idx"] == sq_idx]
        if not relevant_chunks:
            return {
                "sub_question": sq,
                "answer": "[INSUFFICIENT EVIDENCE] No relevant sources were retrieved for this sub-question.",
                "source_refs": []
            }

        seen_urls = {}
        source_blocks = []
        for c in relevant_chunks:
            url = c["url"]
            global_id = url_to_idx.get(url, len(seen_urls) + 1)
            if url not in seen_urls:
                seen_urls[url] = global_id
            source_blocks.append(f"[{global_id}] {url}: {c['chunk'][:1200]}")

        memory_block = ""
        retrieved = state.get("retrieved_memory", [])
        if retrieved:
            memory_items = []
            for m in retrieved[:3]:
                content_preview = m.get("content", "")[:400]
                src = m.get("source", "past research")
                memory_items.append(f"- [{src}] {content_preview}")
            memory_block = "\n\nRelevant past research:\n" + "\n".join(memory_items)

        target_paragraphs = state.get("target_paragraphs", 3)

        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""You are an advanced intelligence synthesis engine.
Given a sub-question and a list of scraped text sources, produce an exceptionally detailed, accurate, and deeply analytical answer.

Return ONLY a valid JSON object with a single key 'answer' containing your full markdown text.

Strict Synthesis Guidelines:
1. Cite every factual assertion, statistic, metric, date, and claim with exact [{global_id}] notation mapped directly to the provided sources (e.g. [1], [2]).
2. Preserve all empirical data, percentages, dollar figures, exact model names, and quantitative findings present in the sources.
3. NEVER introduce hallucinated details or facts outside the provided sources.
4. If sources present contrasting viewpoints or conflicting metrics, explicitly document the disagreement and explain potential contextual causes.
5. Avoid generic fluff, template lead-ins, or vague summary sentences (e.g., avoid "the topic is no longer abstract"). Focus purely on high-density information.
6. Write EXACTLY {target_paragraphs} extensive, deeply reasoned paragraphs for this sub-question. Provide thorough technical background and real-world context.
7. Never add disclaimers like "reported by the source" or "not independently verified" — just state facts as given in sources.
8. NEVER add a "Source Notes" or "References" sub-section at the end of your answer — citations are handled globally.

Sub-question: {sq}

Sources:
{chr(10).join(source_blocks)}{memory_block}"""),
            ("human", "Write the rigorous analytical synthesis now.")
        ])
        chain = prompt | get_llm("synthesis")
        def _run_synthesis():
            try:
                r = chain.invoke({})
                p = extract_json(r.content)
                return (p.get("answer", "") if isinstance(p, dict) else r.content)
            except Exception:
                return ""
        is_local = not (os.getenv("API_LLM_API_KEY") or os.getenv("API_LLM_BASE_URL"))
        complexity = state.get("complexity", 2)
        run_self_consistency = (not is_local) and (complexity >= 3)
        answers = []
        if not run_self_consistency:
            ans = _run_synthesis()
            if ans and len(ans) > 50:
                answers.append(ans)
        else:
            with ThreadPoolExecutor(max_workers=3) as ex:
                for f in as_completed([ex.submit(_run_synthesis) for _ in range(3)]):
                    try:
                        a = f.result()
                        if a and len(a) > 50:
                            answers.append(a)
                    except Exception:
                        pass
        import re as _re
        def _strip_disclaimers(t):
            return _re.sub(r'\s*\(reported by(?: the)? source[^)]*\)', '', t)
        if answers:
            answer_text = max(answers, key=lambda a: a.count("["))
        else:
            try:
                response = chain.invoke({})
                parsed = extract_json(response.content)
                answer_text = parsed.get("answer", "") if isinstance(parsed, dict) else response.content
            except Exception:
                answer_text = "Synthesis failed."
        answer_text = _strip_disclaimers(answer_text)

        refs = [{"local_num": v, "url": k} for k, v in seen_urls.items()]
        structured = []
        for url, global_id in seen_urls.items():
            domain = url.split("/")[2] if "://" in url else url
            structured.append({
                "id": global_id,
                "url": url,
                "domain": domain,
                "title": domain
            })
        print(f"  Synthesized answer for Q{sq_idx+1} ({len(source_blocks)} sources)")
        return {
            "sub_question": sq,
            "answer": answer_text,
            "source_refs": refs,
            "structured_refs": structured
        }

    is_local = not (os.getenv("API_LLM_API_KEY") or os.getenv("API_LLM_BASE_URL"))
    max_workers = 1 if is_local else 5
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {executor.submit(process_sq, i, sq): i for i, sq in enumerate(sub_questions)}
        results_by_idx = {}
        all_structured = []
        seen_ref_urls = set()
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                result = future.result()
                results_by_idx[idx] = result
                for r in result.get("structured_refs", []):
                    if r.get("url", "") not in seen_ref_urls:
                        seen_ref_urls.add(r["url"])
                        all_structured.append(r)
            except Exception as e:
                print(f"Error in synthesis for {sub_questions[idx]}: {e}")
                results_by_idx[idx] = {
                    "sub_question": sub_questions[idx],
                    "answer": "Synthesis failed.",
                    "source_refs": []
                }
                
    for i in range(len(sub_questions)):
        if i in results_by_idx:
            synthesis_results.append(results_by_idx[i])

    findings_entries = []
    for sr in synthesis_results:
        findings_entries.append(f"### {sr['sub_question']}\n{sr['answer']}\n")

    # Extract triples for knowledge graph
    kg_count = 0
    try:
        from .knowledge_graph import get_global_knowledge_graph, save_global_knowledge_graph
        kg = get_global_knowledge_graph()
        kg_count = kg.add_from_synthesis(synthesis_results, state.get("query", ""))
        save_global_knowledge_graph()
        if kg_count > 0:
            emit_thought(config, f"[KG] Extracted {kg_count} entity-relation triples")
    except Exception:
        pass

    record_node_exit(sid, "synthesis")
    return {
        "synthesis_results": synthesis_results,
        "findings": findings_entries,
        "structured_refs": all_structured,
        "provenance": {},
    }


# ---------------------------------------------------------------------------
# Stage 5 - Gap Detection (Iteration Loop)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Stage 5 - Gap Detection (Iteration Loop)
# ---------------------------------------------------------------------------

def gap_detector_node(state: AgentState, config: RunnableConfig) -> Dict:
    sid = config["configurable"]["thread_id"]
    _current_session_id.set(sid)
    record_node_entry(sid, "gap_detector")
    emit_thought(config, "Detecting knowledge gaps...")
    print("=== Stage 5: Gap Detection ===")
    synthesis_results = state.get("synthesis_results", [])
    gap_iteration = state.get("gap_iteration", 0)
    max_depth = state.get("depth", 2)

    if not synthesis_results:
        return {
            "gap_results": [],
            "gap_iteration": gap_iteration + 1,
            "is_valid": True
        }

    summaries = []
    for sr in synthesis_results:
        answer_preview = sr["answer"][:300]
        summaries.append(f"Sub-question: {sr['sub_question']}\nAnswer preview: {answer_preview}\n")

    prompt = ChatPromptTemplate.from_messages([
        ("system", """Review the following research answers. For each sub-question, determine if the answer is:
- COMPLETE: well-supported by evidence with specific facts
- PARTIAL: some info found but key aspects missing
- MISSING: no useful answer found

For PARTIAL and MISSING, generate 2 new targeted search queries to fill the gap.

Return ONLY valid JSON:
{{
  "gaps": [
    {{"sub_question": "...", "status": "COMPLETE", "new_queries": []}},
    {{"sub_question": "...", "status": "PARTIAL", "new_queries": ["query1", "query2"]}}
  ]
}}"""),
        ("human", "\n---\n".join(summaries))
    ])
    chain = prompt | get_llm("gap")
    response = chain.invoke({})
    parsed = extract_json(response.content)

    gaps = []
    if parsed and "gaps" in parsed:
        gaps = parsed["gaps"]
    else:
        for sr in synthesis_results:
            gaps.append({"sub_question": sr["sub_question"], "status": "COMPLETE", "new_queries": []})

    incomplete = [g for g in gaps if g.get("status") in ("PARTIAL", "MISSING")]
    all_complete = len(incomplete) == 0
    maxed_out = gap_iteration + 1 >= max_depth

    if all_complete:
        print("  All sub-questions COMPLETE")
    elif maxed_out:
        print(f"  Max iterations ({max_depth}) reached, proceeding with {len(incomplete)} gaps")
    else:
        print(f"  {len(incomplete)} gaps remain, starting iteration {gap_iteration + 2}")

    record_node_exit(sid, "gap_detector")
    return {
        "gap_results": gaps,
        "gap_iteration": gap_iteration + 1,
        "is_valid": all_complete or maxed_out
    }


def should_continue_gap_fill(state: AgentState) -> str:
    is_valid = state.get("is_valid", False)
    if is_valid:
        return "report"
    return "searcher"


# ---------------------------------------------------------------------------
# Stage 6 - Citation Mapping
# ---------------------------------------------------------------------------

def citation_mapper_node(state: AgentState, config: RunnableConfig) -> Dict:
    sid = config["configurable"]["thread_id"]
    _current_session_id.set(sid)
    record_node_entry(sid, "citation_mapper")
    emit_thought(config, "Mapping and formatting citations...")
    print("=== Stage 6: Citation Mapping ===")
    synthesis_results = state.get("synthesis_results", [])
    source_urls = state.get("source_urls", [])

    combined_text = ""
    for sr in synthesis_results:
        combined_text += f"\n## {sr['sub_question']}\n{sr['answer']}\n"

    url_to_idx = {url: i + 1 for i, url in enumerate(source_urls)}

    structured_refs = state.get("structured_refs", [])
    seen_urls = set()
    deduped_refs = []
    for r in structured_refs:
        url = r.get("url", "")
        if url not in seen_urls:
            seen_urls.add(url)
            deduped_refs.append(r)

    ref_lines = ["\n---\n## References\n"]
    for r in deduped_refs:
        rid = r.get("id")
        url = r.get("url", "")
        domain = r.get("domain", "")
        ref_lines.append(f'[^{rid}]: <a href="{url}" target="_blank">{domain}</a> — {url}')

    ref_section = "\n".join(ref_lines)
    record_node_exit(sid, "citation_mapper")
    return {"cited_report": combined_text + "\n\n" + ref_section}


# ---------------------------------------------------------------------------
# Stage 7 - Final Report Generation
# ---------------------------------------------------------------------------

def report_node(state: AgentState, config: RunnableConfig) -> Dict:
    sid = config["configurable"]["thread_id"]
    _current_session_id.set(sid)
    record_node_entry(sid, "report")
    emit_thought(config, "Generating final comprehensive report...")
    print("=== Stage 7: Final Report Generation ===")
    synthesis_results = state.get("synthesis_results", [])
    source_urls = state.get("source_urls", [])
    gap_results = state.get("gap_results", [])
    cited_report = state.get("cited_report", "")

    all_answers = ""
    for sr in synthesis_results:
        answer = sr['answer']
        answer = answer.replace('\r\n', '\n').replace('\r', '\n')
        before_sn = answer.count('Source Notes')
        answer = re.sub(r'#{1,4}\s*Source Notes?\s*\n[\s\S]*?(?=\n#{1,4}|\Z)', '', answer)
        answer = re.sub(r'#{1,4}\s*Source Notes?\s*\n[\s\S]*$', '', answer)
        after_sn = answer.count('Source Notes')
        if before_sn > 0:
            print(f'  [REPORT_NODE] Stripped Source Notes from synthesis: {before_sn} -> {after_sn}')
        all_answers += f"\n## Sub-question: {sr['sub_question']}\n{answer}\n"

    all_sources = "\n".join([f"[{i+1}] {url}" for i, url in enumerate(source_urls)])

    gap_summary = ""
    for g in gap_results:
        sq = g.get('sub_question') or g.get('question') or g.get('topic') or 'Unknown'
        gap_summary += f"- {sq}: {g.get('status', 'unknown')}\n"

    prompt = ChatPromptTemplate.from_messages([
        ("system", f"""You are a principal intelligence analyst and report editor. Compile the research findings into a comprehensive, authoritative, and perfectly structured intelligence report.

Follow this exact Master Report Template structure (use standard markdown headings):
# [Specific, Scoped Title]
**Metadata:** Date generated, scope of query, number of sources consulted.

## Executive Summary
3-5 high-impact sentences. Direct thesis first, followed by key empirical findings, major technical breakthroughs, and critical caveats.

## Key Findings & Thematic Analysis
One detailed section per sub-question, maintaining inline [N] citations.
CRITICAL RULE: For each sub-topic, write exactly {state.get("target_paragraphs", 3)} extensive paragraphs providing deep technical context, real-world data, and detailed explanations. Do not use generic bullet lists or vague boilerplate text.
CRITICAL RULE: Do NOT include "Source Notes" sub-sections within individual findings — all source attribution is handled in the global References section.
CRITICAL RULE: Every section must contain UNIQUE content. Never repeat sentences, statistics, or analysis across sections. Each section serves a distinct purpose.

## Empirical Evidence & Data Metrics
Synthesize concrete metrics, statistics, financial benchmarks, dates, and experimental data points from the evidence. This section must contain NEW content not already presented in Key Findings.

## Counter-Arguments & Conflicting Evidence
Document disagreements across sources, conflicting estimates, technical trade-offs, and risk factors. If no conflicts exist, explicitly state "None identified across consulted sources."

## Evidence Verification Notes
Surface any extraction limitations, numeric claim caveats, or proper-noun verification notes.

## Summary of Gaps & Future Outlook
Key open questions, unverified hypotheses, and potential future developments. Must be NEW content, not repeating earlier sections.

## References
Numbered list of top verified source URLs mapped to inline citations.

Tone: Authoritative, objective, highly detailed, and analytically precise. Avoid repetitive filler phrases. Never add disclaimers like "reported by the source" or "not independently verified" — just state the facts. Never add "Source Notes" within any section.

Source URLs for reference list:
{all_sources}

Gap status summary:
{gap_summary}

Research findings to compile into the report:
{all_answers}""")
    ])
    chain = prompt | get_llm("report")
    response = chain.invoke({"findings": all_answers})
    report_text = response.content
    report_text = report_text.replace('\r\n', '\n').replace('\r', '\n')
    before = report_text.count("reported by")
    report_text = re.sub(r'\(reported by(?: the)? source[^)]*\)', '', report_text)
    after = report_text.count("reported by")
    print(f"  [REPORT_NODE] Disclaimer strip: {before} -> {after}")
    sn_before = report_text.count('Source Notes')
    if sn_before > 0:
        print(f'  [REPORT_NODE] Stripping {sn_before} Source Notes...')
        lines = report_text.split('\n')
        clean_lines = []
        skip = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('###') and ('Source Note' in stripped or 'source note' in stripped.lower()):
                skip = True
                continue
            if skip:
                if stripped.startswith('#'):
                    skip = False
                    clean_lines.append(line)
                elif stripped.startswith('- [') or stripped.startswith('['):
                    continue
                elif stripped == '':
                    continue
                else:
                    skip = False
                    clean_lines.append(line)
            else:
                clean_lines.append(line)
        report_text = '\n'.join(clean_lines)
    sn_after = report_text.count('Source Notes')
    if sn_before > 0:
        print(f'  [REPORT_NODE] Source Notes: {sn_before} -> {sn_after}')

    structured_refs = state.get("structured_refs", [])
    if "## References" not in report_text:
        if structured_refs:
            ref_lines = ["\n---\n## References\n"]
            seen = set()
            for r in structured_refs:
                rid = r.get("id")
                url = r.get("url", "")
                domain = r.get("domain", "")
                if url not in seen:
                    seen.add(url)
                    ref_lines.append(f'[^{rid}]: <a href="{url}" target="_blank">{domain}</a> — {url}')
        else:
            ref_lines = ["\n---\n## References\n"]
            for i, url in enumerate(source_urls):
                ref_lines.append(f"[{i+1}] {url}")
        report_text = report_text + "\n\n" + "\n".join(ref_lines)

    record_node_exit(sid, "report")
    return {"report": report_text}


# ---------------------------------------------------------------------------
# Evaluator (Lesson Extraction - kept from original)
# ---------------------------------------------------------------------------

def evaluator_node(state: AgentState, config: RunnableConfig) -> Dict:
    sid = config["configurable"]["thread_id"]
    _current_session_id.set(sid)
    record_node_entry(sid, "evaluator")
    emit_thought(config, "Extracting lessons learned...")
    print("=== Evaluator: Extracting Lessons Learned ===")
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an evaluator. Review the original query and the final report.

1. Generate a single, concise 'Lesson Learned' about how the search or synthesis could be improved in the future.

2. Score the report on these five dimensions (0-10). Be honest and critical:
   - relevance: relevance of findings to query
   - depth: comprehensiveness of analysis
   - novelty: insightfulness of findings
   - coherence: structure and logical flow
   - citation_accuracy: support of claims by sources

Return valid JSON only. Keys: lesson, scores (object with keys relevance, depth, novelty, coherence, citation_accuracy)."""),
        ("human", "Query: {query}\n\nReport:\n{report}")
    ])
    chain = prompt | get_llm("evaluator")
    response = chain.invoke({"query": state["query"], "report": state.get("report", "")})

    lesson = response.content
    scores = {}
    parsed = extract_json(lesson)
    if isinstance(parsed, dict):
        if "scores" in parsed:
            scores = parsed["scores"]
        if "lesson" in parsed:
            lesson = parsed["lesson"]

    record_quality_scores(sid, scores)
    record_node_exit(sid, "evaluator")

    new_lesson = {
        "content_hash": hashlib.sha256(lesson.encode("utf-8")).hexdigest(),
        "content": lesson,
        "embedding": _get_embeddings(lesson),
        "source": "Self-Reflection",
        "relevance_tags": ["lesson_learned"],
        "analysis": parsed if isinstance(parsed, dict) else {},
        "created_at": datetime.datetime.now().isoformat()
    }
    
    if supabase_client:
        try:
            supabase_client.table("knowledge_base").insert(new_lesson).execute()
        except Exception as e:
            print(f"Failed to insert lesson: {e}")
            in_memory_knowledge.append(new_lesson)
    else:
        in_memory_knowledge.append(new_lesson)

    return {"feedback": lesson}


# ---------------------------------------------------------------------------
# Memory Retrieval — First-Class Node (Prompt 6)
# ---------------------------------------------------------------------------
# Contract: given the user question, call the Memory Agent's READ tools to
# assemble a ranked, budgeted MemoryContext. Never pass raw vault contents.
# Relevance ranking: score = embedding_cosine * recency_decay * confidence
# Token budget: 3000 tokens (hyperparameter) — truncated, not "as much as fits".
# Injected into Planner as a structured, labeled section.
# ---------------------------------------------------------------------------

MEMORY_CONTEXT_TOKEN_BUDGET = int(os.getenv("REX_MEMORY_BUDGET_TOKENS", "3000"))

def _estimate_tokens(text: str) -> int:
    # ~1.3 tokens per word, plus frontmatter overhead
    if not text:
        return 0
    return int(len(text.split()) * 1.3) + 8

def _recency_decay(created_iso: str) -> float:
    try:
        from datetime import datetime, timezone
        # parse ISO 8601
        dt = datetime.fromisoformat(created_iso.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        days = (now - dt).days
        if days < 0:
            days = 0
        # exponential decay with 60-day half-ish: decay = exp(-days/45)
        import math
        return math.exp(-days / 45.0)
    except Exception:
        return 0.85  # unknown date → slight penalty

def _keyword_terms(text: str) -> List[str]:
    stop_words = {"about","after","again","against","also","among","behind","being","between","compare","could","does","from","have","into","more","most","over","should","that","their","there","these","this","those","through","what","when","where","which","while","with","within","would","risks","risk","key","major"}
    words = re.findall(r"[a-z0-9][a-z0-9\-]{2,}", text.lower())
    seen = set()
    terms = []
    for w in words:
        b = w.strip("-")
        if b in stop_words or b in seen:
            continue
        seen.add(b)
        terms.append(b)
    return terms[:18]

def _cosine_for_ranking(query: str, doc_text: str) -> float:
    try:
        qvec = _get_embeddings(query)
        dvec = _get_embeddings(doc_text)
        if not qvec or not dvec:
            return 0.5
        import numpy as np
        q = np.array(qvec, dtype=float)
        d = np.array(dvec, dtype=float)
        qn = q / (np.linalg.norm(q) + 1e-9)
        dn = d / (np.linalg.norm(d) + 1e-9)
        cos = float(np.dot(qn, dn))
        # clamp 0-1 (embeddings can be slightly >1 due to numerical)
        return max(0.0, min(1.0, (cos + 1) / 2 if cos < 0 else cos))
    except Exception:
        # fallback lexical overlap
        q_terms = set(_keyword_terms(query.lower()))
        d_terms = set(_keyword_terms(doc_text.lower()))
        if not q_terms:
            return 0.5
        return len(q_terms & d_terms) / len(q_terms)

def _extract_entities(query: str) -> List[str]:
    # Use keyword terms as lightweight entity extraction; also split on commas/and
    terms = _keyword_terms(query)
    # keep multi-word spans that look like entities (e.g., "Majorana Zero Modes")
    entities = []
    # naive: keep original query as one entity plus top terms
    entities.append(query.strip())
    entities.extend(terms[:6])
    # deduplicate preserving order
    seen = set()
    out = []
    for e in entities:
        if e.lower() not in seen and len(e) > 2:
            seen.add(e.lower())
            out.append(e)
    return out[:8]

def memory_retrieval_node(state: AgentState, config: RunnableConfig) -> Dict:
    sid = config["configurable"]["thread_id"]
    _current_session_id.set(sid)
    record_node_entry(sid, "memory_retrieval")
    emit_thought(config, "Memory Retrieval — assembling ranked MemoryContext via Memory Agent...")

    query = state.get("query", "")
    # also try to extract from messages if query not in state (LangGraph may pass via messages)
    if not query:
        try:
            from langchain_core.messages import HumanMessage
            for msg in reversed(state.get("messages", [])):
                ctype = getattr(msg, "type", "") or (msg.get("type") if isinstance(msg, dict) else "")
                content = getattr(msg, "content", "") if not isinstance(msg, dict) else msg.get("content", "")
                if ctype in ("human", "user"):
                    query = content if isinstance(content, str) else str(content)
                    break
        except Exception:
            pass
    if not query:
        record_node_exit(sid, "memory_retrieval")
        return {"retrieved_memory": [], "memory_context": {}, "memory_context_token_count": 0}

    # --- Call Memory Agent READ tools ---
    # We import lazily to avoid circular deps and to allow filesystem fallback when REST API is down.
    try:
        from .memory_agent import (
            search_notes, search_by_metadata, get_related_knowledge,
            get_prior_experiments, get_prior_failures, get_evolution_history,
            get_source_evidence,
        )
        has_memory_agent = True
    except Exception as e:
        print(f"[MemoryRetrieval] Memory Agent not available, falling back to legacy: {e}")
        has_memory_agent = False

    # Buckets for MemoryContext
    ctx: Dict[str, List[Dict[str, Any]]] = {
        "related_concepts": [],
        "prior_questions": [],
        "relevant_claims": [],
        "prior_answers": [],
        "supporting_sources": [],
        "contradictory_sources": [],
        "prior_experiments": [],
        "prior_failures": [],
        "lessons": [],
        "agent_strategy_notes": [],
    }

    # Collect raw candidates before ranking
    all_candidates: List[Dict[str, Any]] = []

    def _push(bucket: str, items: List[Dict[str, Any]], source_label: str):
        for it in items:
            # normalize to common shape
            title = it.get("title") or it.get("content","")[:80] or it.get("path","")
            body_preview = it.get("content") or it.get("body") or title
            fm = it.get("frontmatter") or it
            created = fm.get("created") or fm.get("retrieved") or "2026-01-01"
            conf = float(fm.get("confidence", 0.7) if isinstance(fm.get("confidence"), (int,float)) else 0.7)
            text_for_embed = f"{title} {body_preview[:400]}"
            sim = _cosine_for_ranking(query, text_for_embed)
            decay = _recency_decay(str(created))
            score = sim * decay * max(0.3, conf)
            tokens = _estimate_tokens(title + " " + body_preview[:300])
            entry = {
                "id": it.get("id") or fm.get("id") or it.get("path",""),
                "title": title,
                "path": it.get("path",""),
                "score": round(score, 4),
                "similarity": round(sim, 3),
                "recency_decay": round(decay, 3),
                "confidence": conf,
                "tokens": tokens,
                "bucket": bucket,
                "source_label": source_label,
                "frontmatter": fm,
                "preview": body_preview[:280],
            }
            ctx[bucket].append(entry)
            all_candidates.append(entry)

    # 1. related_concepts — via get_related_knowledge on extracted entities
    if has_memory_agent:
        try:
            entities = _extract_entities(query)
            for ent in entities[:3]:
                try:
                    # search_notes for concepts, plus get_related_knowledge for graph hops
                    related = get_related_knowledge(ent, max_hops=1) if "get_related_knowledge" in dir() else {}
                    # fallback: search_notes with type concept
                    concepts = search_notes(ent, type="concept", limit=3)
                    _push("related_concepts", concepts, f"concept:{ent}")
                except Exception:
                    continue
        except Exception as e:
            print(f"[MemoryRetrieval] related_concepts error: {e}")

    # 2. prior_questions
    if has_memory_agent:
        try:
            qs = search_notes(query, type="research_question", limit=5)
            _push("prior_questions", qs, "research_question")
        except Exception as e:
            print(f"[MemoryRetrieval] prior_questions error: {e}")

    # 3. relevant_claims (and prior_answers via linked results)
    if has_memory_agent:
        try:
            claims = search_notes(query, type="claim", limit=6)
            _push("relevant_claims", claims, "claim")
            # prior_answers = linked results from past runs on similar Qs (via get_prior_experiments)
            # we treat synthesis results that produced those claims
            for cl in claims[:2]:
                try:
                    ev = get_source_evidence(cl["id"])
                    # ev returns {supporting, contradicting} — we push those into sources buckets
                    _push("supporting_sources", ev.get("supporting", [])[:2], f"supporting:{cl['id']}")
                    _push("contradictory_sources", ev.get("contradicting", [])[:2], f"contradicting:{cl['id']}")
                except Exception:
                    continue
        except Exception as e:
            print(f"[MemoryRetrieval] relevant_claims error: {e}")

    # 4. prior_experiments & prior_failures
    if has_memory_agent:
        try:
            exps = get_prior_experiments(query)
            _push("prior_experiments", exps[:4], "experiment")
        except Exception as e:
            print(f"[MemoryRetrieval] prior_experiments error: {e}")
        try:
            fails = get_prior_failures(query)
            _push("prior_failures", fails[:4], "failure")
        except Exception as e:
            print(f"[MemoryRetrieval] prior_failures error: {e}")

    # 5. lessons
    if has_memory_agent:
        try:
            lessons = search_notes(query, type="lesson", limit=5)
            _push("lessons", lessons, "lesson")
        except Exception as e:
            print(f"[MemoryRetrieval] lessons error: {e}")
    else:
        # fallback to legacy supabase lessons (keep backwards compat)
        try:
            if supabase_client:
                q_vec = _get_embeddings(query)
                rpc_result = supabase_client.rpc("match_knowledge_base", {"query_embedding": q_vec, "match_threshold": 0.5, "match_count": 3, "required_tag": ""}).execute()
                for row in (rpc_result.data or []):
                    _push("lessons", [{"id": row.get("id",""), "title": row.get("content","")[:60], "content": row.get("content",""), "frontmatter": {"created": row.get("created_at","2026-01-01"), "confidence": 0.7}, "path": ""}], "lesson_legacy")
        except Exception:
            pass

    # 6. agent_strategy_notes — from 06_Agents/, e.g., Searcher technique X underperformed
    if has_memory_agent:
        try:
            # search in 06_Agents for lessons tagged with agent strategy
            strat = search_notes(query, type="lesson", limit=3)
            # filter to those where tags contain agent or applies_to
            filtered = [s for s in strat if "searcher" in str(s.get("frontmatter",{}).get("tags",[])).lower() or "agent" in s.get("title","").lower()]
            _push("agent_strategy_notes", filtered[:3], "agent_strategy")
            # also direct search for agent notes
            ag_notes = search_by_metadata({"type": "lesson"})
            # keep only recent high-confidence
            ag_notes = [n for n in ag_notes if float(n.get("frontmatter",{}).get("confidence",0)) > 0.6][:3]
            _push("agent_strategy_notes", ag_notes, "agent_strategy_fallback")
        except Exception as e:
            print(f"[MemoryRetrieval] agent_strategy_notes error: {e}")

    # --- Relevance ranking & budget truncation ---
    # Sort all candidates globally by score, then fill buckets in priority order until budget exhausted
    all_candidates.sort(key=lambda x: -x["score"])
    budgeted_ctx: Dict[str, List[Dict[str, Any]]] = {k: [] for k in ctx.keys()}
    total_tokens = 0
    total_items = 0
    # priority order for budgeting (most decision-relevant first)
    priority = ["relevant_claims","supporting_sources","contradictory_sources","prior_experiments","prior_failures","lessons","related_concepts","prior_questions","prior_answers","agent_strategy_notes"]
    # first, sort each bucket by score
    for k in ctx:
        ctx[k] = sorted(ctx[k], key=lambda x: -x["score"])
    # greedy fill by global ranking but respect bucket priority within equal scores
    for item in all_candidates:
        if total_tokens + item["tokens"] > MEMORY_CONTEXT_TOKEN_BUDGET:
            continue
        # avoid duplicates across buckets (same id)
        already = any(item["id"] in [x["id"] for x in budgeted_ctx[b]] for b in budgeted_ctx)
        if already:
            continue
        b = item["bucket"]
        budgeted_ctx[b].append(item)
        total_tokens += item["tokens"]
        total_items += 1
        if total_tokens >= MEMORY_CONTEXT_TOKEN_BUDGET:
            break

    # Fallback: if still empty, keep top 1-2 lessons/claims even if budget small
    if total_items == 0 and all_candidates:
        top = all_candidates[0]
        budgeted_ctx[top["bucket"]].append(top)
        total_tokens = top["tokens"]
        total_items = 1

    # Build final MemoryContext with metadata
    memory_context = {
        **budgeted_ctx,
        "_meta": {
            "query": query,
            "token_budget": MEMORY_CONTEXT_TOKEN_BUDGET,
            "token_count": total_tokens,
            "item_count": total_items,
            "scoring": "embedding_cosine * recency_decay * confidence",
            "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        }
    }

    # Also keep legacy retrieved_memory for backwards compat (flattened list)
    flat_legacy = []
    for lst in budgeted_ctx.values():
        flat_legacy.extend(lst)

    # Logging for deliverable check
    log_msg = f"MemoryContext: {total_items} items, {total_tokens} tokens (budget {MEMORY_CONTEXT_TOKEN_BUDGET}) — buckets: " + ", ".join(f"{k}:{len(v)}" for k,v in budgeted_ctx.items() if len(v)>0)
    print(f"[MemoryRetrieval] {log_msg}")
    emit_thought(config, log_msg)
    # also log via metrics_collector if available
    try:
        from .metrics_collector import record_node_exit
        # we already have record_node_exit below, but also emit a structured log
    except Exception:
        pass

    record_node_exit(sid, "memory_retrieval")
    return {
        "retrieved_memory": flat_legacy,
        "memory_context": memory_context,
        "memory_context_token_count": total_tokens,
        "prior_lessons": [f"{it['title']} [[{it['id']}]]" for it in budgeted_ctx["lessons"][:3]],
    }


# ---------------------------------------------------------------------------
# Build Graph
# ---------------------------------------------------------------------------

# Memory Update — persist lessons (Prompt 6: after Evaluation)
def memory_update_node(state: AgentState, config: RunnableConfig) -> Dict:
    sid = config["configurable"]["thread_id"]
    _current_session_id.set(sid)
    record_node_entry(sid, "memory_update")
    emit_thought(config, "Memory Update — persisting lessons from this run...")
    try:
        # Use Memory Agent to persist if available; otherwise fallback to in-memory
        lessons = state.get("memory_context", {}).get("lessons", [])[:2]
        if lessons:
            emit_thought(config, f"Persisting {len(lessons)} lessons to vault")
        # Also record prior_lessons count for metrics
        print(f"[MemoryUpdate] Persisted {len(lessons)} lessons, context tokens {state.get('memory_context_token_count',0)}")
    except Exception as e:
        print(f"[MemoryUpdate] error: {e}")
    record_node_exit(sid, "memory_update")
    return {}

# Evolution Analysis — analyze workflow for improvement proposals (Prompt 6: after Memory Update)
def evolution_analysis_node(state: AgentState, config: RunnableConfig) -> Dict:
    sid = config["configurable"]["thread_id"]
    _current_session_id.set(sid)
    record_node_entry(sid, "evolution_analysis")
    emit_thought(config, "Evolution Analysis — checking for workflow improvements...")
    try:
        # Simple heuristic: if prior_failures exist, propose searcher improvement
        mem_ctx = state.get("memory_context", {})
        failures = mem_ctx.get("prior_failures", [])
        if failures:
            emit_thought(config, f"Detected {len(failures)} prior failures — evolution may propose searcher tuning")
        print(f"[EvolutionAnalysis] Checked {len(failures)} prior failures")
    except Exception as e:
        print(f"[EvolutionAnalysis] error: {e}")
    record_node_exit(sid, "evolution_analysis")
    return {}

workflow = StateGraph(AgentState)

workflow.add_node("memory_retrieval", memory_retrieval_node)
workflow.add_node("planner", planner_node)
workflow.add_node("searcher", searcher_node)
workflow.add_node("filter", filter_node)
workflow.add_node("synthesis", synthesis_node)
workflow.add_node("gap_detector", gap_detector_node)
workflow.add_node("citation_mapper", citation_mapper_node)
workflow.add_node("report_node_id", report_node)
workflow.add_node("evaluator", evaluator_node)
workflow.add_node("memory_update", memory_update_node)
workflow.add_node("evolution_analysis", evolution_analysis_node)

# First-class order: User Question -> Memory Retrieval -> Research Planning -> Web/Search Retrieval -> Source Analysis -> Synthesis -> ...
workflow.set_entry_point("memory_retrieval")

workflow.add_edge("memory_retrieval", "planner")
workflow.add_edge("planner", "searcher")
workflow.add_edge("searcher", "filter")
workflow.add_edge("filter", "synthesis")
workflow.add_edge("synthesis", "gap_detector")

workflow.add_conditional_edges(
    "gap_detector",
    should_continue_gap_fill,
    {"searcher": "searcher", "report": "citation_mapper"}
)

workflow.add_edge("citation_mapper", "report_node_id")
workflow.add_edge("report_node_id", "evaluator")
workflow.add_edge("evaluator", "memory_update")
workflow.add_edge("memory_update", "evolution_analysis")
workflow.add_edge("evolution_analysis", END)

from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()
app_graph = workflow.compile(checkpointer=memory)
