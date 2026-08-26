# -*- coding: utf-8 -*-
import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))

from main import build_report_autonomously

print("=== Running End-to-End Report Generation Verification ===")

query = "Impact of Artificial Intelligence on Healthcare in 2026"
print(f"Query: {query}")
t0 = time.time()

result = build_report_autonomously(query, depth=1, complexity=1, target_paragraphs=2, target_sub_questions=2)
elapsed = time.time() - t0

report = result.get("report", "")
source_urls = result.get("source_urls", [])
structured_refs = result.get("structured_refs", [])

print(f"\n✅ Report Generation Completed in {elapsed:.2f}s!")
print(f"📊 Total Sources Cited: {len(source_urls)}")
print(f"📄 Report Length: {len(report)} characters ({len(report.split())} words)")
print("\n" + "=" * 80)
print("GENERATED REPORT OUTPUT:")
print("=" * 80)
print(report)
print("=" * 80)

assert len(report) > 300, "Report length is too short"
assert "# " in report, "Missing H1 header in report"
assert "## Executive Summary" in report or "## Key Findings" in report, "Missing key report sections"
assert "reported by" not in report.lower(), "Found forbidden disclaimer text"
assert "source notes" not in report.lower(), "Found forbidden Source Notes header"

print("\n🎉 REPORT GENERATION VERIFICATION PASSED PERFECTLY!")
