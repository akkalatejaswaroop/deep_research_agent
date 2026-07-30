"""Full end-to-end user query test with detailed output."""
import sys, os, time, json
sys.path.insert(0, os.path.dirname(__file__))

from main import build_report_autonomously

QUERY = "Explain the greenhouse effect and its impact on global warming"

stages = []
thoughts = []
sources = []

def on_node(node_id):
    stages.append(node_id)

def on_thought(msg):
    thoughts.append(msg)

def on_sources(urls):
    sources.extend(urls)

def on_track_status(tid, text, status):
    if status == "searching":
        on_thought(f"Track {tid}: Searching for '{text[:60]}...'")
    elif status == "synthesizing":
        on_thought(f"Track {tid}: Synthesizing '{text[:60]}...'")

print("=" * 70)
print(f"USER QUERY: {QUERY}")
print("=" * 70)

t0 = time.perf_counter()
result = build_report_autonomously(
    query=QUERY,
    on_node=on_node,
    on_thought=on_thought,
    on_sources=on_sources,
    on_track_status=on_track_status,
)
elapsed = time.perf_counter() - t0

print(f"\n{'=' * 70}")
print(f"STAGES EXECUTED ({len(stages)}):")
print(f"  {' -> '.join(stages)}")
print(f"THOUGHTS ({len(thoughts)}):")
for t in thoughts:
    print(f"  [THOUGHT] {t}")
print(f"SOURCES FOUND: {len(sources)}")

print(f"\n{'=' * 70}")
print("REPORT:")
print(f"{'=' * 70}")
report = result.get("report", "")
print(report[:5000])

print(f"\n{'=' * 70}")
print("PROVENANCE:")
print(f"{'=' * 70}")
prov = result.get("provenance", {})
print(json.dumps(prov, indent=2, default=str)[:2000])

print(f"\n{'=' * 70}")
print("METRICS:")
print(f"{'=' * 70}")
metrics = result.get("_metrics", {})
print(json.dumps(metrics, indent=2, default=str)[:2000])

print(f"\n{'=' * 70}")
print(f"Total time: {elapsed:.1f}s")
print(f"Report length: {len(report)} chars")
print(f"Quality score: {metrics.get('quality', {}).get('overall', 'N/A')}/10")
print(f"{'=' * 70}")
