#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
from main import generate_sub_questions, _extract_core_topic

topic = _extract_core_topic("What are the best agentic AI companies growing in 2026?")
print(f"Extracted topic: '{topic}'")

sqs = generate_sub_questions("What are the best agentic AI companies growing in 2026?", 8)
print(f"Sub-questions ({len(sqs)}):")
for i, sq in enumerate(sqs, 1):
    print(f"  {i}. {sq}")
