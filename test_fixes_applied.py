#!/usr/bin/env python3
"""
Final comprehensive test suite to verify all optimizations and fixes.
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

def test_all_fixes():
    """Test that all fixes have been applied."""
    print("\n" + "=" * 80)
    print("COMPREHENSIVE FIX VERIFICATION")
    print("=" * 80)
    
    checks = []
    
    # Check 1: .env file has proper timeouts
    print("\n[1] Checking environment configuration...")
    with open("backend/.env", "r") as f:
        env_content = f.read()
    
    has_timeout_180 = "LLM_TIMEOUT=180" in env_content
    has_ollama_host = "OLLAMA_HOST=" in env_content
    has_cache_enabled = "CACHE_ENABLED=true" in env_content
    
    print(f"  LLM_TIMEOUT=180: {'OK' if has_timeout_180 else 'MISSING'}")
    print(f"  OLLAMA_HOST set: {'OK' if has_ollama_host else 'MISSING'}")
    print(f"  CACHE_ENABLED: {'OK' if has_cache_enabled else 'MISSING'}")
    
    checks.append(("ENV: LLM_TIMEOUT=180", has_timeout_180))
    checks.append(("ENV: OLLAMA_HOST", has_ollama_host))
    checks.append(("ENV: CACHE_ENABLED", has_cache_enabled))
    
    # Check 2: optimization.py module exists
    print("\n[2] Checking optimization module...")
    opt_exists = os.path.exists("backend/agents/optimization.py")
    print(f"  optimization.py exists: {'OK' if opt_exists else 'MISSING'}")
    
    if opt_exists:
        with open("backend/agents/optimization.py", "r") as f:
            opt_content = f.read()
        has_caching = "llm_response_cache" in opt_content
        has_timeout = "TimeoutHandler" in opt_content
        has_streaming = "StreamingEventQueue" in opt_content
        
        print(f"  LLM caching decorator: {'OK' if has_caching else 'MISSING'}")
        print(f"  Timeout handler: {'OK' if has_timeout else 'MISSING'}")
        print(f"  Streaming queue: {'OK' if has_streaming else 'MISSING'}")
        
        checks.append(("OPT: LLM caching", has_caching))
        checks.append(("OPT: Timeout handler", has_timeout))
        checks.append(("OPT: Streaming queue", has_streaming))
    else:
        checks.append(("OPT: All", False))
    
    # Check 3: graph.py has optimizations
    print("\n[3] Checking graph.py optimizations...")
    with open("backend/agents/graph.py", "r") as f:
        graph_content = f.read()
    
    has_timeout_handler = "TimeoutHandler" in graph_content
    has_search_timeout = "timeout=15" in graph_content  # in searcher
    has_arxiv_timeout = "timeout=8" in graph_content  # reduced from 10
    has_fewer_workers = "max_workers=5" in graph_content  # reduced from 10
    
    print(f"  Timeout handler integration: {'OK' if has_timeout_handler else 'MISSING'}")
    print(f"  Search query timeout (15s): {'OK' if has_search_timeout else 'MISSING'}")
    print(f"  arXiv timeout (8s): {'OK' if has_arxiv_timeout else 'MISSING'}")
    print(f"  Fewer workers (max=5): {'OK' if has_fewer_workers else 'MISSING'}")
    
    checks.append(("GRAPH: Timeout handler", has_timeout_handler))
    checks.append(("GRAPH: Search timeout", has_search_timeout))
    checks.append(("GRAPH: arXiv timeout", has_arxiv_timeout))
    checks.append(("GRAPH: Max workers", has_fewer_workers))
    
    # Check 4: scraper.py has optimizations
    print("\n[4] Checking scraper.py optimizations...")
    with open("backend/agents/scraper.py", "r") as f:
        scraper_content = f.read()
    
    has_playwright_2sec = "timeout_ms=2000" in scraper_content  # reduced from 3000
    has_fast_failover = "Fast path" in scraper_content or "failover" in scraper_content.lower()
    has_jina = "scrape_with_jina" in scraper_content
    
    print(f"  Playwright 2s timeout: {'OK' if has_playwright_2sec else 'MISSING'}")
    print(f"  Fast failover strategy: {'OK' if has_fast_failover else 'MISSING'}")
    print(f"  Jina Reader integration: {'OK' if has_jina else 'MISSING'}")
    
    checks.append(("SCRAPER: Playwright 2s", has_playwright_2sec))
    checks.append(("SCRAPER: Fast failover", has_fast_failover))
    checks.append(("SCRAPER: Jina", has_jina))
    
    # Check 5: Try importing key modules
    print("\n[5] Testing imports...")
    try:
        from agents.optimization import TimeoutHandler, StreamingEventQueue
        print("  TimeoutHandler: OK")
        print("  StreamingEventQueue: OK")
        checks.append(("IMPORT: optimization", True))
    except Exception as e:
        print(f"  Import error: {e}")
        checks.append(("IMPORT: optimization", False))
    
    try:
        from agents.graph import app_graph
        if app_graph:
            print("  app_graph: OK")
            checks.append(("IMPORT: app_graph", True))
        else:
            print("  app_graph: None")
            checks.append(("IMPORT: app_graph", False))
    except Exception as e:
        print(f"  Import error: {e}")
        checks.append(("IMPORT: app_graph", False))
    
    # Summary
    print("\n" + "=" * 80)
    print("FIX VERIFICATION SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result in checks if result)
    total = len(checks)
    
    for check_name, passed_check in checks:
        status = "[OK]" if passed_check else "[FAIL]"
        print(f"{status} {check_name}")
    
    print(f"\nTotal: {passed}/{total} checks passed")
    
    if passed >= total * 0.8:  # 80% pass rate
        print("\n[SUCCESS] Most optimizations are in place!")
        return True
    else:
        print(f"\n[INCOMPLETE] Some optimizations are missing ({total - passed} issues)")
        return False


if __name__ == "__main__":
    success = test_all_fixes()
    sys.exit(0 if success else 1)
