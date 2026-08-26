import urllib.request
import json
import sys
import time

print("=== PERFORMANCE OPTIMIZATION ===")
print()

# 1. Test request latency
start = time.time()
try:
    r = urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5)
    elapsed = time.time() - start
    print(f"1. Health check latency: {elapsed:.3f}s - OK")
except Exception as e:
    print(f"1. Health check latency: ERROR - {e}")

# 2. Test response size
r = urllib.request.urlopen('http://127.0.0.1:8000/', timeout=5)
content = r.read().decode()
print(f"2. Root response size: {len(content)} bytes")

# 3. Test quality scoring speed
import sys
sys.path.insert(0, r'D:\deep_research_agent\backend')
from real_quality_scorer import compute_quality_scores, compute_overall
start = time.time()
scores = compute_quality_scores('test', 'test report', [{'url': 'x', 'domain': 'x', 'content': 'test content here'}])
elapsed = time.time() - start
overall = compute_overall(scores)
print(f"3. Quality scoring: {elapsed*1000:.1f}ms, overall: {overall}/10")

# 4. Test keyword extraction speed
from main import _keyword_terms
start = time.time()
terms = _keyword_terms("What is quantum computing and how does it work?", "What are the key technical capabilities")
elapsed = time.time() - start
print(f"4. Keyword extraction: {elapsed*1000:.1f}ms, terms: {len(terms)}")

# 5. Test cache key generation speed
import hashlib
start = time.time()
key = hashlib.sha256("test query".encode("utf-8")).hexdigest()[:16]
elapsed = time.time() - start
print(f"5. Cache key generation: {elapsed*1000:.1f}ms")

print()
print("=== PERFORMANCE SUMMARY ===")
print("All performance metrics collected successfully")