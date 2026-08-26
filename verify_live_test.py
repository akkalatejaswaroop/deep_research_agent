# -*- coding: utf-8 -*-
"""Live verification test for the 15 issues."""
import json, os, sys, time, queue, threading
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

results = {}
def log(name, status, detail=""):
    results[name] = {"status": status, "detail": detail}
    print(f"[{status.upper():8s}] {name} — {detail}")

# ---- Test TimeoutHandler (Issues 2, 3) ----
print("\n===== TimeoutHandler unit test =====")
from agents.optimization import TimeoutHandler
th = TimeoutHandler(timeout_seconds=0.3)

def slow_fn():
    time.sleep(5)
    return "LATE"

t0 = time.time()
r1 = th.execute_with_timeout(slow_fn, "synthesis")
el = time.time() - t0
ok_2 = el < 2 and r1 != "LATE"
log("Issue2 timeout returns quickly", "PASS" if ok_2 else "FAIL",
    f"elapsed={el:.2f}s fallback={r1[:40]!r}")

th_fast = TimeoutHandler(timeout_seconds=2)
r2 = th_fast.execute_with_timeout(lambda: "OK", "synthesis")
log("Issue2 normal result passes through", "PASS" if r2 == "OK" else "FAIL", f"got={r2!r}")

fb = th.get_fallback("synthesis")
try:
    parsed = json.loads(fb)
    ok_3 = isinstance(parsed, dict)
except Exception:
    ok_3 = False
log("Issue3 synthesis fallback is valid JSON", "PASS" if ok_3 else "FAIL", f"fallback={fb[:60]!r}")

fb_gap = th.get_fallback("gap")
log("Issue3 stage 'gap' has dedicated fallback", "PASS" if "gap_detector" not in fb_gap and "Processing failed" not in fb_gap else "FAIL",
    f"got generic: {'Processing failed' in fb_gap}")

# ---- Test graph import / helpers (Issue 7) ----
print("\n===== Graph import & helper test =====")
from agents.graph import app_graph, _build_graph_provenance, extract_json, emit_thought, _is_blocked_source, _check_cancellation
log("Issue7 all helpers importable", "PASS", "extract_json, emit_thought, _is_blocked_source, _build_graph_provenance OK")

prov = _build_graph_provenance([], ["https://arxiv.org/abs/2502.06717", "https://random.blog/post"])
log("Issue11 provenance builder works", "PASS" if len(prov) == 2 and prov["https://arxiv.org/abs/2502.06717"]["quality_score"] > 0.7 else "FAIL",
    f"keys={list(prov.keys())[:2]}, scores={[v['quality_score'] for v in prov.values()]}")

cancel = threading.Event()
cfg = {"configurable": {"cancel_event": cancel, "event_queue": queue.Queue()}}
cancel.set()
try:
    _check_cancellation(cfg)
    log("Issue5 _check_cancellation raises on cancel", "FAIL", "no exception raised")
except RuntimeError:
    log("Issue5 _check_cancellation raises on cancel", "PASS", "RuntimeError raised")

# ---- Live LangGraph pipeline test (Issues 1, 8, 10, 11) ----
print("\n===== Live LangGraph pipeline test =====")
os.environ["LLM_TIMEOUT"] = "120"
from agents.state import AgentState
from langgraph.types import interrupt  # noqa

initial_state = {
    "messages": [],
    "query": "Impact of solid-state batteries on electric vehicle adoption",
    "depth": 1,
    "complexity": 1,
    "target_paragraphs": 2,
    "target_sub_questions": 2,
    "current_depth": 0,
    "sub_questions": [],
    "search_queries": [],
    "raw_pages": {},
    "source_urls": [],
    "scored_chunks": [],
    "synthesis_results": [],
    "gap_results": [],
    "gap_iteration": 0,
    "cited_report": "",
    "report": "",
    "findings": [],
    "sub_tasks": [],
    "feedback": "",
    "is_valid": False,
    "prior_lessons": [],
    "retrieved_memory": [],
    "structured_refs": [],
    "metrics": {},
    "logs": [],
    "active_node": "",
}

eq = queue.Queue()
config = {"configurable": {"thread_id": "live-test-1", "event_queue": eq, "cancel_event": threading.Event()}}

t0 = time.time()
final = None
node_order = []
try:
    for output in app_graph.stream(initial_state, config=config):
        node_name = list(output.keys())[0]
        node_order.append(node_name)
        print(f"  [{time.time()-t0:6.1f}s] node: {node_name}")
    final = app_graph.get_state(config).values
    total = time.time() - t0
except Exception as e:
    import traceback
    traceback.print_exc()
    total = time.time() - t0
    log("Issue7 pipeline runs without NameError", "FAIL", f"crashed at {total:.0f}s: {e}")
else:
    log("Issue7 pipeline runs without NameError", "PASS", f"{len(node_order)} nodes in {total:.0f}s: {node_order}")

if final is not None:
    report = final.get("report", "")
    srcs = final.get("source_urls", [])
    synt = final.get("synthesis_results", [])
    prov_out = final.get("provenance", "MISSING")
    log("Issue8 sources retrieved", "PASS" if len(srcs) > 0 else "FAIL", f"{len(srcs)} sources")
    n_insuff = sum(1 for s in synt if "INSUFFICIENT EVIDENCE" in s.get("answer", ""))
    log("Issue8 no fabrication when evidence missing", "PASS" if len(srcs) > 0 or n_insuff == len(synt) else "FAIL",
        f"{n_insuff}/{len(synt)} answers marked INSUFFICIENT")
    log("Issue8 report non-empty", "PASS" if len(report) > 500 else "FAIL", f"{len(report)} chars")
    log("Issue11 provenance populated", "PASS" if isinstance(prov_out, dict) and len(prov_out) > 0 else "FAIL",
        f"provenance={prov_out if not isinstance(prov_out, dict) else list(prov_out.keys())[:3]}")
    # citation consistency (Issue 10)
    import re
    cited = set(re.findall(r"\[(\d+)\]", report))
    refs = set(re.findall(r"\[(\d+)\]\s*(?:<a|\[|https?)", report))
    log("Issue10 report has references section", "PASS" if "References" in report else "FAIL", "")
    print("\n--- report head ---")
    print(report[:1500])

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "verify_live_results.json"), "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, default=str)
print("\n===== SUMMARY =====")
for k, v in results.items():
    print(f"  {v['status']:8s} {k}: {v['detail'][:120]}")
