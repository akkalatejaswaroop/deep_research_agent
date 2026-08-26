from main import run_qa_pass, _cross_check_numeric_claims, _verify_entity_names
import re
from collections import Counter

# Test report with some issues
report = """# Deep Research Report: Neuro-Symbolic AI

Executive Summary
The deep-research pipeline for Neuro-Symbolic AI is taking longer than the 540s budget on this local host (CPU-only inference + live web scraping). 55 source(s) were gathered before the timeout; a complete report will be available shortly via the /api/v1/sessions endpoint.

Analyzed & Cited Primary Sources (55)
1 arxiv.org https://arxiv.org/abs/2509.02918v1
2 arxiv.org https://arxiv.org/abs/2608.01528v1
3 arxiv.org https://arxiv.org/abs/2412.15588v1
4 arxiv.org https://arxiv.org/abs/2506.01121v1
5 arxiv.org https://arxiv.org/abs/2211.15566v2
"""

# Test sources (minimal)
sources = [
    {"url": "https://arxiv.org/abs/2509.02918v1", "domain": "arxiv.org", "content": "Neuro-symbolic AI combines neural networks with symbolic reasoning approaches."},
    {"url": "https://en.wikipedia.org/wiki/Neuro-symbolic_AI", "domain": "wikipedia.org", "content": "Neuro-symbolic AI is an approach to artificial intelligence that combines neural and symbolic methods."},
    {"url": "https://ieeexplore.ieee.org/document/10251249", "domain": "ieeexplore.ieee.org", "content": "Research on neuro-symbolic integration for reasoning tasks."},
]

# Test section texts
section_texts = [
    "Neuro-symbolic AI combines neural networks with symbolic reasoning approaches.",
    "Research on neuro-symbolic integration for reasoning tasks.",
]

query = "Neuro-Symbolic AI"

result = run_qa_pass(report, section_texts, sources, query)
print('QA Pass result:')
print(f'  passed: {result["passed"]}')
print(f'  issues: {result["issues"]}')
print(f'  should_regenerate: {result["should_regenerate"]}')

# Test numeric claims check
numeric = _cross_check_numeric_claims(report, sources)
print(f'\nNumeric claims unchecked: {numeric}')

# Test entity verification
entities = _verify_entity_names(report, sources)
print(f'Verified entities: {entities}')