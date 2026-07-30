"""Test Phase 2: quality-based adaptive pipeline parameters"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
os.environ["SIMULATED_MODE"] = "1"

from main import _normalize_topic, _adaptive_profile, _dimension_history, _auto_research_profile, _save_quality_history, _load_quality_history
print("imports done")

# Ensure clean state
_dimension_history.clear()

topic = _normalize_topic("quantum computing impact")
auto = _auto_research_profile("quantum computing impact")
adaptive = _adaptive_profile("quantum computing impact")
print(f"[2.1] No history: auto={auto}, adaptive={adaptive}")
assert adaptive == auto, "Without history, adaptive should match auto"
print("[2.1] PASS: no history match")

_dimension_history[topic] = {"citation_accuracy": [4.5]}
adapt2 = _adaptive_profile("quantum computing impact")
print(f"[2.1] Low citation 4.5 -> sub_questions: {adapt2['target_sub_questions']} (auto was {auto['target_sub_questions']})")
assert adapt2["target_sub_questions"] >= auto["target_sub_questions"] + 2
print("[2.1] PASS: low citation increases sub_questions")

_dimension_history[topic] = {"depth": [4.0]}
adapt3 = _adaptive_profile("quantum computing impact")
print(f"[2.1] Low depth 4.0 -> paragraphs: {adapt3['target_paragraphs']} (auto {auto['target_paragraphs']}), depth: {adapt3['depth']} (auto {auto['depth']})")
assert adapt3["target_paragraphs"] >= auto["target_paragraphs"] + 2
assert adapt3["depth"] >= auto["depth"] + 1
print("[2.1] PASS: low depth increases paragraphs and depth")

import main as main_mod
main_mod._dimension_history["test_topic"] = {"relevance": [8.0, 9.0]}
main_mod._save_quality_history()
main_mod._dimension_history.clear()
main_mod._load_quality_history()
restored = main_mod._dimension_history.get("test_topic", {})
print(f"[2.2] Persisted dim history: {restored}")
assert restored.get("relevance") == [8.0, 9.0]
print("[2.2] PASS: persistence round-trip")

print("\n=== ALL PHASE 2 TESTS PASSED ===")
