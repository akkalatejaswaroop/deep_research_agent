"""Quick test for Phase 1.1 + 1.2"""
import sys, os, hashlib, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

os.environ["SIMULATED_MODE"] = "1"

from db import get_lessons_by_topic, in_memory_knowledge, save_lesson_local
from main import generate_sub_questions, generate_sub_questions_tot, _normalize_topic

# === Test 1.1: get_lessons_by_topic ===
in_memory_knowledge.clear()
lessons_data = [
    ("quantum computing impact cryptography", "Need more academic sources for quantum topics"),
    ("solid state battery advances", "Include comparative density tables for battery reports"),
    ("quantum error correction methods", "Use peer-reviewed citation models for physics claims"),
]
for q, lesson in lessons_data:
    save_lesson_local({
        "content_hash": hashlib.sha256(lesson.encode()).hexdigest(),
        "content": lesson,
        "query": q,
        "source": "Self-Reflection",
        "relevance_tags": ["lesson_learned"],
        "analysis": {"scores": {"relevance": 8.0, "depth": 7.0}, "lesson": lesson},
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    })

result = get_lessons_by_topic("quantum computing cryptography")
print(f"[1.1] Quantum query: {len(result)} lessons")
for l in result:
    print(f"  - {l['content'][:80]}")
assert len(result) >= 1
assert "quantum" in result[0]["content"].lower() or "quantum" in result[0].get("query","").lower()

result2 = get_lessons_by_topic("climate change policy")
print(f"[1.1] Climate query: {len(result2)} lessons (fallback)")
assert len(result2) >= 1

print("PASS Phase 1.1")

# === Test 1.2: generate_sub_questions ===
# Test WITHOUT lessons (template path - fast)
sqs2 = generate_sub_questions("quantum computing", 4)
print(f"[1.2] Without lessons: {len(sqs2)} questions (template)")
for s in sqs2:
    print(f"  - {s}")
assert len(sqs2) >= 2

# Test TOT wrapper without lessons
sqs3 = generate_sub_questions_tot("quantum computing", 4)
print(f"[1.2] TOT wrapper (no lessons): {len(sqs3)} questions")
assert len(sqs3) >= 2

# Test WIH lessons (will fallback to template if Ollama unavailable - which is fine)
sqs4 = generate_sub_questions("quantum computing", 4, prior_lessons=["test lesson"])
print(f"[1.2] With lessons: {len(sqs4)} questions (template if Ollama unavailable)")
assert len(sqs4) >= 2

print("PASS Phase 1.2")

# === Test _normalize_topic ===
topic = _normalize_topic("quantum computing impact cryptography")
print(f"[1.x] Normalized topic: '{topic}'")
assert topic, "Topic should not be empty"

print("\n=== ALL PHASE 1 TESTS PASSED ===")
