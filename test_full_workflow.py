# -*- coding: utf-8 -*-
"""Full workflow E2E test: 9 agents + report generation against live backend."""
import json
import re
import sys
import time
import requests

BASE = "http://127.0.0.1:8000"
ALL_NODES = [
    "planner", "memory_retrieval", "searcher", "filter", "synthesis",
    "gap_detector", "citation_mapper", "report_node_id", "evaluator",
]

def log(msg):
    print(f"[WORKFLOW] {msg}", flush=True)

log("=== REX Full Workflow Test: 9 Agents + Report Generation ===")

health = requests.get(f"{BASE}/health", timeout=10)
log(f"Health check: {health.status_code} {health.json()}")
assert health.status_code == 200 and health.json().get("status") == "ok"

query = "Impact of solid-state batteries on electric vehicle adoption in 2026"
payload = {
    "query": query,
    "depth": 1,
    "complexity": 1,
    "paragraphs": 3,
    "subQuestions": 6,
}

log(f"POST /api/v1/research/ query={query!r}")
t0 = time.time()
with requests.post(f"{BASE}/api/v1/research/", json=payload, stream=True, timeout=600) as resp:
    session_id = resp.headers.get("X-Session-Id")
    log(f"Status: {resp.status_code} | Session ID: {session_id}")
    assert resp.status_code == 200

    nodes_seen = []
    node_times = {}
    last_node = None
    last_node_time = None
    sources = []
    report = None
    metrics = None
    thoughts = []
    scores = None

    for raw_line in resp.iter_lines(decode_unicode=True):
        if not raw_line or not raw_line.startswith("data: "):
            continue
        data_str = raw_line[6:]
        if data_str == "[DONE]":
            break
        try:
            event = json.loads(data_str)
        except Exception:
            continue

        node = event.get("node")
        now = time.time()
        if isinstance(node, str) and node not in ("start", "end", "cancelled"):
            if node != last_node:
                if last_node:
                    node_times[last_node] = round(now - last_node_time, 1)
                last_node = node
                last_node_time = now
            if node not in nodes_seen:
                nodes_seen.append(node)
                log(f"  agent#{len(nodes_seen)} [{node}] started")

        if event.get("type") == "thought":
            thoughts.append(event.get("message", ""))
        if event.get("source_urls"):
            for u in event["source_urls"]:
                if u not in sources:
                    sources.append(u)
        if event.get("type") == "quality_scores":
            scores = event
        if "report" in event and event.get("report"):
            report = event["report"]
        if "metrics" in event:
            metrics = event["metrics"]

    if last_node:
        node_times[last_node] = round(time.time() - last_node_time, 1)

elapsed = time.time() - t0
log(f"=== DONE in {elapsed:.1f}s ===")

missing = [n for n in ALL_NODES if n not in nodes_seen]
log(f"Agents executed ({len(nodes_seen)}/9): {nodes_seen}")
log(f"Missing agents: {missing or 'NONE'}")
log(f"Node timings (s): {node_times}")
log(f"Sources found: {len(sources)}")
log(f"Thoughts streamed: {len(thoughts)}")

assert not missing, f"Workflow incomplete - agents missing: {missing}"
assert report and len(report) > 500, "Report missing or too short"
log(f"Report: {len(report)} chars, {len(report.split())} words")

words = len(report.split())
assert words >= 150, "Report too short to be a real synthesis"

if scores:
    s = scores.get("scores", {})
    log("Quality scores: " + ", ".join(f"{k}={v}" for k, v in s.items() if k != "overall") + f" | overall={scores.get('overall')}")

out_path = r"D:\deep_research_agent\workflow_test_report.md"
with open(out_path, "w", encoding="utf-8") as f:
    f.write(report)
log(f"Report saved to {out_path}")

print("\n" + "=" * 70)
print("REPORT CONTENT")
print("=" * 70)
print(report)
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"Total time: {elapsed:.1f}s")
print(f"Session ID: {session_id}")
print(f"Agents (9/9): {', '.join(nodes_seen)}")
print(f"Sources: {len(sources)}")
print(f"Report: {len(report)} chars / {words} words")
print(f"Saved to: {out_path}")
