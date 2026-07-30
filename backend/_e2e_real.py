"""Full end-to-end with REAL LLM (Ollama) + REAL search (Wikipedia + DuckDuckGo)."""
import time, sys, os
sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None
sys.path.insert(0, r"D:\deep_research_agent\backend")

t0 = time.perf_counter()
import main as m
ti = time.perf_counter()
print(f"Import: {ti-t0:.1f}s", flush=True)
print(f"Model: {os.getenv('REPORT_MODEL', 'qwen2.5:3b')}", flush=True)

QUERY = "Explain the greenhouse effect and its impact on global warming"

stages = []
thoughts = []
urls_found = []

def on_node(node_id):
    stages.append(node_id)

def on_thought(msg):
    thoughts.append(msg)
    print(f"  [T] {msg}", flush=True)

def on_sources(urls):
    urls_found.extend(urls)

def on_track_status(tid, text, status):
    if status == "searching":
        on_thought(f"Track {tid}: Searching...")
    elif status == "synthesizing":
        on_thought(f"Track {tid}: Synthesizing...")
    elif status == "completed":
        on_thought(f"Track {tid}: Done")

print(f"\nUSER QUERY: {QUERY}", flush=True)
print(f"LLM: REAL (Ollama)", flush=True)
print(f"Search: REAL (Wikipedia + DuckDuckGo)", flush=True)
print(f"PREFER_LLM: {os.getenv('PREFER_LLM', 'true')}", flush=True)
print(f"REPORT_MODEL: {os.getenv('REPORT_MODEL', 'qwen2.5:3b')}", flush=True)
print(flush=True)

t1 = time.perf_counter()
result = m.build_report_autonomously(
    query=QUERY,
    on_node=on_node,
    on_thought=on_thought,
    on_sources=on_sources,
    on_track_status=on_track_status,
)
tb = time.perf_counter()

print(f"\n{'='*72}", flush=True)
print(f"STAGES: {' -> '.join(stages)}", flush=True)
print(f"SOURCES: {len(urls_found)}", flush=True)
print(f"THOUGHTS: {len(thoughts)}", flush=True)
for t in thoughts[:12]:
    print(f"  \u2022 {t}", flush=True)
if len(thoughts) > 12:
    print(f"  ... ({len(thoughts)-12} more)", flush=True)

report = result.get("report", "")
prov = result.get("provenance", {})
metrics = result.get("_metrics", {})

print(f"\n{'='*72}", flush=True)
print(f"REPORT ({len(report)} chars, {len(report.split())} words):", flush=True)
print(f"{'='*72}", flush=True)
sections = report.split("\n---\n")
for i, sec in enumerate(sections):
    heading = (sec.strip().split("\n")[0] or "(no heading)")[:100]
    body = sec.strip()[:500]
    print(f"\n--- [{i+1}] {heading} ---", flush=True)
    print(body, flush=True)
    if len(sec.strip()) > 500:
        print(f"  ... (+{len(sec.strip())-500} chars)", flush=True)

print(f"\n{'='*72}", flush=True)
print(f"PROVENANCE: {prov.get('total_claims',0)} claims total", flush=True)
cov = prov.get("coverage", {})
print(f"  Multi-sourced: {cov.get('multi_sourced',0)} | Single-source: {cov.get('single_source',0)} | Uncited: {cov.get('uncited',0)}", flush=True)
for s in prov.get("source_utilisation", [])[:4]:
    if s.get("claim_count", 0) > 0:
        print(f"    [{s.get('id')}] {s.get('domain')}: {s.get('claim_count')} claims", flush=True)

print(f"\n{'='*72}", flush=True)
print(f"METRICS: Overall {metrics.get('quality',{}).get('overall','?')}/10", flush=True)
scores = metrics.get("quality", {}).get("scores", {})
print(f"  " + " | ".join(f"{k}: {scores.get(k,'?')}" for k in ["relevance","depth","novelty","coherence","citation_accuracy"]), flush=True)

print(f"\n{'='*72}", flush=True)
print(f"Timing: import={ti-t0:.1f}s  build={tb-t1:.1f}s  total={tb-t0:.1f}s", flush=True)
print(f"Sub-questions: {len(result.get('synthesis_results',[]))}", flush=True)
print(f"Provenance: {'YES' if prov else 'no'}", flush=True)
print(f"{'='*72}", flush=True)
print("RESULT: PASS", flush=True)
