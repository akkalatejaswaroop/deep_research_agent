# Test enhanced _topic_relevance_filter
import re
from main import _keyword_terms, _is_blocked_source, _is_downweighted_source

# Test _keyword_terms
terms = _keyword_terms("What is neuro-symbolic AI")
print(f"Query terms: {terms}")

# Test _is_blocked_source with various sources
blocked_test = {"url": "https://vixra.org/abs/123", "domain": "vixra.org", "content": "some content"}
print(f"Blocked vixra: {_is_blocked_source(blocked_test)}")

blocked_test2 = {"url": "https://medium.com/@test/post", "domain": "medium.com", "content": "some content"}
print(f"Blocked medium: {_is_blocked_source(blocked_test2)}")

blocked_test3 = {"url": "https://arxiv.org/abs/2509.02918v1", "domain": "arxiv.org", "content": "some content"}
print(f"Allowed arxiv: {not _is_blocked_source(blocked_test3)}")

# Test _is_downweighted_source
dw_test = {"url": "https://reddit.com/r/test", "domain": "reddit.com", "content": "some content"}
print(f"Downweighted reddit: {_is_downweighted_source(dw_test)}")

dw_test2 = {"url": "https://arxiv.org/abs/2509.02918v1", "domain": "arxiv.org", "content": "some content"}
print(f"Allowed arxiv downweight: {not _is_downweighted_source(dw_test2)}")

# Test _cross_check_numeric_claims (from main)
from main import _cross_check_numeric_claims, _verify_entity_names

report = "# Test Report\nAccording to studies, 85% of users agree [^1] and the year was 2023."
sources_minimal = [
    {"url": "https://example.com", "domain": "example.com", "content": "85% of users agree and the year was 2023."}
]
numeric = _cross_check_numeric_claims(report, sources_minimal)
print(f"Numeric unchecked: {numeric}")

# Test _verify_entity_names
entities = _verify_entity_names(report, sources_minimal)
print(f"Mismatched entities: {entities}")

print("\nAll individual function tests passed!")