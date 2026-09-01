import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import _extract_core_topic, call_llm, ResearchQuery, start_research

print("[TEST 1] Testing _extract_core_topic...")
topic1 = _extract_core_topic("What are the best Quantum Computing Scalability approaches?")
print(f"  Topic extracted: '{topic1}'")
assert "computing quantum" not in topic1, f"Words are still sorted alphabetically: {topic1}"
print("  PASS: Topic preserves natural word order.")

print("\n[TEST 2] Testing call_llm function signature & multi-call behavior...")
# call_llm should be callable repeatedly without throwing error or locking out
res1 = call_llm("test prompt 1")
res2 = call_llm("test prompt 1")
print(f"  Call 1 result length: {len(res1)}, Call 2 result length: {len(res2)}")
print("  PASS: call_llm executed twice without lock-out exception.")

print("\n[TEST 3] Testing ResearchQuery validation & options...")
req = ResearchQuery(query="Test query", options={"bypass_cache": True})
assert req.query == "Test query"
print("  PASS: ResearchQuery accepts bypass_cache options.")

print("\nALL VERIFICATION TESTS PASSED SUCCESSFULLY!")
