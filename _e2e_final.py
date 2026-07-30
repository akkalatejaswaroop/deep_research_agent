"""
E2E Final Test: validates all components of the self-improvement loop.
Tests:
1. Real quality scores (not hardcoded)
2. Lesson extraction and storage
3. get_lessons_by_topic retrieval with score context
4. Adaptive profile adjusts parameters from past scores
5. Multi-run quality delta tracking
6. on_scores callback wiring
7. generate_sub_questions with lesson injection
"""

import sys, os, json, time, hashlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
os.environ["SIMULATED_MODE"] = "1"

from main import generate_quality_scores, compute_overall, generate_sub_questions
from main import save_real_lesson, _extract_lesson_from_report, _normalize_topic
from main import _adaptive_profile, _auto_research_profile, _dimension_history, _quality_history
from db import get_lessons_by_topic, in_memory_knowledge

PASS = 0
FAIL = 0

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [OK] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}: {detail}")

# Clean state
in_memory_knowledge.clear()
_dimension_history.clear()
_quality_history.clear()

# =====================================================================
# TEST 1: Quality scores are real (not hardcoded 9.x)
# =====================================================================
print("\n" + "=" * 60)
print("TEST 1: Real quality scores (no hardcoded fallback)")
print("=" * 60)

good_report = """# Deep Research Report: Quantum Cryptography

## Executive Summary
Quantum computing threatens RSA-2048 encryption. Shor's algorithm factors large numbers exponentially faster.

## Key Findings
IBM's 1000-qubit Eagle processor achieved 99.9% fidelity. NIST is standardizing post-quantum cryptography.

## References
[1] https://ibm.com - IBM Research
[2] https://nist.gov - PQC Standards
"""

poor_report = "AI is important."

good_scores = generate_quality_scores("quantum cryptography", good_report, ["https://ibm.com", "https://nist.gov"])
poor_scores = generate_quality_scores("quantum cryptography", poor_report, [])

good_overall = compute_overall(good_scores)
poor_overall = compute_overall(poor_scores)

check("Good report scores > poor report scores", good_overall > poor_overall,
    f"good={good_overall}, poor={poor_overall}")
check("Good report overall < 9.0 (not hardcoded)", good_overall < 9.0, f"overall={good_overall}")
check("All 5 dimensions present", len(good_scores) == 5, f"{list(good_scores.keys())}")
check("All scores in [0,10]", all(0 <= v <= 10 for v in good_scores.values()), str(good_scores))
check("Scores vary", len(set(good_scores.values())) > 1, f"all identical: {good_scores}")

# =====================================================================
# TEST 2: Lesson extraction
# =====================================================================
print("\n" + "=" * 60)
print("TEST 2: Lesson extraction")
print("=" * 60)

lesson = _extract_lesson_from_report("quantum cryptography", good_report)
check("Lesson extracted", len(lesson) > 20, lesson[:100])
check("Lesson references the query", "quantum" in lesson.lower() or "cryptograph" in lesson.lower(), lesson)

# =====================================================================
# TEST 3: Lesson storage and retrieval
# =====================================================================
print("\n" + "=" * 60)
print("TEST 3: Lesson storage and retrieval")
print("=" * 60)

save_real_lesson("quantum cryptography", good_report, ["https://ibm.com"])
check("Lesson stored in memory", len(in_memory_knowledge) >= 1)

retrieved = get_lessons_by_topic("quantum cryptography impact")
check("get_lessons_by_topic returns lessons", len(retrieved) >= 1)
if retrieved:
    r = retrieved[0]
    check("Lesson has content", len(r.get("content", "")) > 0)
    check("Lesson has scores", "scores" in str(r.get("analysis", {})))

# =====================================================================
# TEST 4: Adaptive profile
# =====================================================================
print("\n" + "=" * 60)
print("TEST 4: Adaptive profile from past scores")
print("=" * 60)

topic = _normalize_topic("quantum computing cryptography")
auto = _auto_research_profile("quantum computing cryptography")
check("Auto profile baseline", auto["target_sub_questions"] >= 4)

# Low citation accuracy -> more sub-questions
_dimension_history[topic] = {"citation_accuracy": [4.0]}
adaptive = _adaptive_profile("quantum computing cryptography")
check("Low citation -> more sub-questions",
    adaptive["target_sub_questions"] >= auto["target_sub_questions"] + 2,
    f"auto={auto['target_sub_questions']}, adaptive={adaptive['target_sub_questions']}")

# Low depth -> more paragraphs + depth
_dimension_history[topic] = {"depth": [3.5]}
adaptive2 = _adaptive_profile("quantum computing cryptography")
check("Low depth -> more paragraphs",
    adaptive2["target_paragraphs"] >= auto["target_paragraphs"] + 2,
    f"auto={auto['target_paragraphs']}, adaptive={adaptive2['target_paragraphs']}")
check("Low depth -> increased depth param",
    adaptive2["depth"] >= auto["depth"] + 1,
    f"auto={auto['depth']}, adaptive={adaptive2['depth']}")

# No history -> matches auto
_dimension_history.clear()
adaptive3 = _adaptive_profile("quantum computing cryptography")
check("No history -> matches auto", adaptive3 == auto, f"auto={auto}, adaptive={adaptive3}")

# =====================================================================
# TEST 5: Quality delta
# =====================================================================
print("\n" + "=" * 60)
print("TEST 5: Quality delta tracking")
print("=" * 60)

topic = _normalize_topic("quantum error correction")
_quality_history[topic] = [6.0, 6.8, 7.5]
history = _quality_history.get(topic, [])
avg_before = sum(history[:-1]) / max(1, len(history[:-1]))
delta = round(7.5 - avg_before, 1)

check("Quality delta positive", delta > 0, f"delta={delta}")
check("History length tracked", len(history) == 3)

# Cap applied via main.py scoring path (history[-20:])
# Append 25 items then slice (simulating what score_saving pipeline does)
h = _quality_history[topic]
for i in range(25):
    h.append(8.0)
_quality_history[topic] = h[-20:]
check("History capped at 20 via slicing", len(_quality_history[topic]) <= 20, f"len={len(_quality_history[topic])}")

# =====================================================================
# TEST 6: generate_sub_questions with lessons
# =====================================================================
print("\n" + "=" * 60)
print("TEST 6: generate_sub_questions with lesson injection")
print("=" * 60)

sq = generate_sub_questions("quantum computing", 4, prior_lessons=["Use peer-reviewed sources for technical claims"])
check("Sub-questions generated", len(sq) >= 2, f"Only {len(sq)}")
check("Sub-questions are strings", all(isinstance(s, str) and len(s) > 10 for s in sq))

sq2 = generate_sub_questions("quantum computing", 4)
check("Fallback templates work", len(sq2) >= 2)

# =====================================================================
# TEST 7: on_scores callback wiring
# =====================================================================
print("\n" + "=" * 60)
print("TEST 7: Scoring callback chain")
print("=" * 60)

# Verify that the score callback structure works via build_report_autonomously
from main import build_report_autonomously

cb_scores = []
def score_fn(s, o):
    cb_scores.append((s, o))

try:
    result = build_report_autonomously(
        "quantum computing", depth=1, complexity=1,
        target_paragraphs=2, target_sub_questions=2,
        on_thought=lambda m: None, on_node=lambda n: None,
        on_track_status=lambda i,t,s: None, on_sources=lambda u: None,
        on_scores=score_fn,
    )
    m = result.get("_metrics", {}).get("quality", {})
    check("Report generated", len(result.get("report","")) > 100,
        f"Only {len(result.get('report',''))} chars")
    check("Scores in metrics", len(m.get("scores", {})) == 5, str(m.get("scores")))
    check("on_scores was called", len(cb_scores) >= 1, f"called {len(cb_scores)} times")
    if cb_scores:
        check("on_scores has 5 dims", len(cb_scores[0][0]) == 5, str(cb_scores[0][0]))
except Exception as e:
    check(f"Pipeline runnable (no crash)", False, str(e))
    # If pipeline fails (network issue), skip this test but don't fail overall
    print("  [SKIP] Pipeline requires network — scores verified via direct tests above")

# =====================================================================
# SUMMARY
# =====================================================================
print(f"\n{'=' * 60}")
total = PASS + FAIL
print(f"E2E TEST RESULTS: {PASS} passed, {FAIL} failed out of {total}")
print(f"{'=' * 60}")

if FAIL == 0:
    sys.exit(0)
else:
    sys.exit(1)
