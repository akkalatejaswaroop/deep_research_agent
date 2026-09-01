import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from backend.main import build_report_autonomously

query = "Agentic AI Trends and Autonomous Software Engineering in 2026"
print(f"Generating research report for query: '{query}'...")

start_time = time.time()
result = build_report_autonomously(
    query=query,
    depth=1,
    complexity=1,
    target_paragraphs=3,
    target_sub_questions=4
)
elapsed = time.time() - start_time

report_text = result.get("report", "")
sources = result.get("source_urls", [])

print(f"\nCompleted in {elapsed:.2f} seconds.")
print(f"Sources found: {len(sources)}")
print(f"Report length: {len(report_text)} characters / {len(report_text.split())} words\n")

# Save to output file
with open("generated_sample_report.md", "w", encoding="utf-8") as f:
    f.write(report_text)

print("SAVED_REPORT_TO_FILE")
