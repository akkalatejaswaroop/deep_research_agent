#!/usr/bin/env python3
"""Test just the sub-question generation function in isolation."""
import re

def _extract_core_topic(query: str) -> str:
    q = query.strip().rstrip("?.")
    for p in ("what are the best ", "what is the best ", "which are the best ",
              "what are ", "what is ", "who are ", "tell me about ",
              "best ", "top ", "leading "):
        if q.lower().startswith(p):
            q = q[len(p):]
            break
    q = re.sub(r'\s+in (the |)(current|today.s|modern|202[45678]) (market|landscape|world|industry)', '', q, flags=re.I)
    q = re.sub(r'\s+that are growing', '', q, flags=re.I)
    q = q.replace("marlet", "market").replace("artifical", "artificial")
    return q.strip()[:60] or query[:40]

# Test with the user's query
queries = [
    "What are the best agentic AI companies growing in 2026?",
    "What are the latest advancements in quantum computing as of 2026?",
    "Top AI coding assistants in 2026",
]

for q in queries:
    topic = _extract_core_topic(q)
    templates = [
        f"Which companies lead in {topic} and what is their market position?",
        f"What measurable ROI and business impact do {topic} solutions show?",
        f"How do the top {topic} platforms compare on features and performance?",
        f"What specific use cases and real deployments of {topic} exist?",
        f"What are the key technical capabilities that define {topic} systems?",
        f"What challenges and limitations affect {topic} adoption?",
        f"How fast is the {topic} market growing and what drives adoption?",
        f"What distinguishes leading {topic} vendors from competitors?",
    ]
    print(f"Query: {q}")
    print(f"Topic: '{topic}'")
    print(f"Sub-questions:")
    for i, sq in enumerate(templates[:6], 1):
        print(f"  {i}. {sq}")
    print()
