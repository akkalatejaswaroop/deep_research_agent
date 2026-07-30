#!/usr/bin/env python3
"""Run a research query and inspect report quality."""
import requests, json, sys, os, re

base = "http://localhost:8000"
query = "What are the best agentic AI companies growing in 2026?"

print(f"Query: {query}")
print("="*80)

payload = {
    "query": query,
    "options": {"complexity": 1, "max_pages": 5, "model": "phi3:mini"}
}

report = None
events = []

with requests.post(f"{base}/api/v1/research", json=payload, timeout=600, stream=True) as r:
    for line in r.iter_lines():
        if not line: continue
        decoded = line.decode("utf-8", errors="replace")
        if decoded.startswith("data: "):
            data = json.loads(decoded[6:])
            events.append(data)
            if data.get("node") == "end":
                report = data.get("report", "")
                break

if not report:
    print("FAIL: No report generated")
    sys.exit(1)

print(f"Report length: {len(report)} chars")
print("="*80)

# --- Quality checks ---

# Check 1: Sub-questions don't repeat the full query
sqs = re.findall(r'^### (.+)$', report, re.MULTILINE)
print(f"\n[CHECK 1] Sub-question headings ({len(sqs)}):")
for sq in sqs:
    # Check if sub-question repeats the full query
    overlap = len(set(sq.lower().split()) & set(query.lower().split()))
    total = max(1, len(set(sq.lower().split())))
    ratio = overlap / total
    flag = " **REPEATS QUERY**" if ratio > 0.5 else ""
    print(f"  {sq[:100]}{flag}")

# Check 2: Boilerplate phrases in report
boilerplate = [
    "cookie", "subscribe", "sign up", "all rights reserved",
    "skip to content", "click here", "read more",
    "Architecture and types of", "How to implement",
    "Before we jump into", "key takeaways",
    "Double click on what's possible", "A free way off",
    "From search to action", "In this guide, we",
]
print(f"\n[CHECK 2] Boilerplate content in report:")
hits = []
for phrase in boilerplate:
    count = report.lower().count(phrase)
    if count > 0:
        hits.append((phrase, count))
if hits:
    for phrase, count in hits:
        print(f"  FOUND {count}x: '{phrase}'")
else:
    print("  None found (good)")

# Check 3: Duplicate paragraphs (identical blocks >100 chars)
print(f"\n[CHECK 3] Duplicate paragraphs:")
para_pattern = re.compile(r'(?<=\n\n)(.+?)(?=\n\n)', re.DOTALL)
paras = para_pattern.findall(report)
para_texts = [p.strip() for p in paras if len(p.strip()) > 100]
seen = {}
dupes = 0
for pt in para_texts:
    norm = pt[:200]
    if norm in seen:
        dupes += 1
    seen[norm] = seen.get(norm, 0) + 1
if dupes > 0:
    print(f"  {dupes} duplicate paragraph blocks found!")
else:
    print("  No duplicate paragraphs found (good)")

# Check 4: LLM disclaimer phrases
disclaimers = ["reported by the source", "not independently verified", "reported by source"]
print(f"\n[CHECK 4] LLM disclaimers:")
for d in disclaimers:
    c = report.lower().count(d)
    if c > 0:
        print(f"  FOUND {c}x: '{d}'")

# Check 5: Report structure
print(f"\n[CHECK 5] Report sections:")
sections = re.findall(r'^## (.+)$', report, re.MULTILINE)
for s in sections:
    print(f"  {s}")

# Check 6: n8n usage
print(f"\n[CHECK 6] n8n used in pipeline:")
n8n_used = any("[n8n Engine]" in json.dumps(e) for e in events)
print(f"  {'YES' if n8n_used else 'NO'}")

# Check 7: Source diversity
urls = re.findall(r'https?://[^\s)]+', report)
domains = set()
for u in urls:
    m = re.match(r'https?://([^/]+)', u)
    if m:
        domains.add(m.group(1))
print(f"\n[CHECK 7] Domains cited: {len(domains)}")
for d in sorted(domains):
    print(f"  {d}")

print("\n" + "="*80)
if hits or dupes > 0:
    print("ISSUES FOUND - see above")
    sys.exit(1)
else:
    print("ALL CHECKS PASSED")
