"""Quick diagnostic - find where the hang is."""
import sys, os, time, traceback
sys.path.insert(0, os.path.dirname(__file__))
import main as m

def _fake_search(query, **kwargs):
    return [
        {"url":"https://ex.com","title":"Test","domain":"ex.com",
         "content":"Greenhouse gases trap heat. CO2 levels 420 ppm. Temperature 1.2C."}
        for _ in range(3)
    ]
m.search_all_sources = _fake_search

print("Step 1: build with pre-provided sub_questions...")
t0 = time.perf_counter()
try:
    result = m.build_report_autonomously(
        "greenhouse effect",
        sub_questions=["What is the greenhouse effect?", "What causes global warming?"]
    )
    elapsed = time.perf_counter() - t0
    print(f"  OK in {elapsed:.1f}s — report {len(result.get('report',''))} chars, "
          f"provenance {result.get('provenance',{}).get('total_claims',0)} claims")
except Exception as e:
    print(f"  FAIL: {e}")
    traceback.print_exc()

print()
print("Step 2: build WITHOUT sub_questions (calls ToT planner)...")
t0 = time.perf_counter()
try:
    result = m.build_report_autonomously("greenhouse effect")
    elapsed = time.perf_counter() - t0
    print(f"  OK in {elapsed:.1f}s — report {len(result.get('report',''))} chars, "
          f"provenance {result.get('provenance',{}).get('total_claims',0)} claims")
except Exception as e:
    print(f"  FAIL: {e}")
    traceback.print_exc()
