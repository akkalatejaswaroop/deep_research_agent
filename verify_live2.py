# -*- coding: utf-8 -*-
"""Live pipeline test v2 — unbuffered, per-node timing, hard 20-min cap, 2 sub-questions."""
import os, sys, time, queue, threading
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))
os.environ["LLM_TIMEOUT"] = "300"

from agents.graph import app_graph

initial_state = {
    "messages": [], "query": "Impact of solid-state batteries on electric vehicle adoption",
    "depth": 1, "complexity": 1, "target_paragraphs": 1, "target_sub_questions": 2,
    "current_depth": 0, "sub_questions": [], "search_queries": [], "raw_pages": {},
    "source_urls": [], "scored_chunks": [], "synthesis_results": [], "gap_results": [],
    "gap_iteration": 0, "cited_report": "", "report": "", "findings": [], "sub_tasks": [],
    "feedback": "", "is_valid": False, "prior_lessons": [], "retrieved_memory": [],
    "structured_refs": [], "metrics": {}, "logs": [], "active_node": "",
}

eq = queue.Queue()
config = {"configurable": {"thread_id": "live-test-2", "event_queue": eq, "cancel_event": threading.Event()}}

out = []
def run():
    t0 = time.time()
    order = []
    try:
        for output in app_graph.stream(initial_state, config=config):
            n = list(output.keys())[0]
            order.append(n)
            out.append(f"[{time.time()-t0:7.1f}s] node={n}")
        state = app_graph.get_state(config).values
        out.append(f"REPORT_CHARS={len(state.get('report',''))} SOURCES={len(state.get('source_urls',[]))}")
        out.append(f"PROVENANCE={'dict' if isinstance(state.get('provenance'), dict) and len(state.get('provenance',{}))>0 else str(state.get('provenance'))}")
        synt = state.get("synthesis_results", [])
        insuff = sum(1 for s in synt if "INSUFFICIENT" in s.get("answer",""))
        out.append(f"SYNTHESIS={len(synt)} INSUFFICIENT={insuff}")
        for s in synt:
            out.append(f"  Q: {s.get('sub_question','')[:60]} answer_len={len(s.get('answer',''))}")
        out.append(f"NODE_ORDER={order}")
        out.append("DONE_OK")
    except Exception as e:
        out.append(f"EXC {type(e).__name__}: {e}")
        out.append(f"NODE_ORDER={order}")

t0 = time.time()
th = threading.Thread(target=run, daemon=True)
th.start()
th.join(timeout=1200)
print(f"elapsed={time.time()-t0:.0f}s alive_after_cap={th.is_alive()}", flush=True)
for line in out:
    print(line, flush=True)
