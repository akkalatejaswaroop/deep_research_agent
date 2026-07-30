"""Quick E2E - measure import vs execution time separately."""
import time, sys
sys.path.insert(0, r"D:\deep_research_agent\backend")

t0 = time.perf_counter()
import main as m
ti = time.perf_counter()
print(f"Import: {ti-t0:.1f}s")

m.search_all_sources = lambda q, **kw: [
    {"url":"https://ex.com","title":"T","domain":"ex.com",
     "content":"Greenhouse gases trap heat. CO2 420 ppm. Temperature 1.2C."}
    for _ in range(3)
]

t1 = time.perf_counter()
result = m.build_report_autonomously(
    "greenhouse effect",
    sub_questions=["What is the greenhouse effect?", "What causes it?"],
)
tb = time.perf_counter()
print(f"Build: {tb-t1:.1f}s")

report = result.get("report", "")
prov = result.get("provenance", {})
print(f"Report: {len(report)} chars")
print(f"Provenance: {prov.get('total_claims', 0)} claims")
print(f"Total: {tb-t0:.1f}s")
print("OK" if report else "FAIL")
