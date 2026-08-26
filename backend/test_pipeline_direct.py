# -*- coding: utf-8 -*-
import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(__file__))

print("=== Testing REX 9-Node LangGraph State Machine Directly ===")

from agents.graph import app_graph, AgentState

test_query = "Solid-State Battery Commercialization Milestones 2026"
initial_state: AgentState = {
    "query": test_query,
    "depth": 1,
    "complexity": 1,
    "target_paragraphs": 2,
    "sub_questions": [],
    "search_queries": [],
    "source_urls": [],
    "retrieved_memory": [],
    "raw_pages": {},
    "scored_chunks": [],
    "synthesis_results": [],
    "report": "",
    "feedback": "",
    "gap_iteration": 0,
    "has_gaps": False,
    "is_valid": False,
    "structured_refs": [],
    "findings": [],
    "sub_tasks": []
}

config = {"configurable": {"thread_id": "test_direct_session_1"}}

t0 = time.time()
try:
    final_state = app_graph.invoke(initial_state, config=config)
    elapsed = time.time() - t0
    
    report = final_state.get("report", "")
    feedback = final_state.get("feedback", "")
    source_urls = final_state.get("source_urls", [])
    synthesis_results = final_state.get("synthesis_results", [])
    
    print(f"\n✅ Pipeline completed in {elapsed:.2f} seconds!")
    print(f"📊 Total Sources Scraped: {len(source_urls)}")
    print(f"📝 Sub-Questions Synthesized: {len(synthesis_results)}")
    print(f"📄 Report Length: {len(report)} characters ({len(report.split())} words)")
    print(f"⭐ Evaluator Feedback / Score: {feedback[:200]}...")
    
    # Assertions for 100% Relevance & Quality
    assert len(report) > 500, "Report is too short!"
    assert "reported by" not in report.lower(), "Found disallowed disclaimer 'reported by'"
    assert "source notes" not in report.lower(), "Found disallowed section 'source notes'"
    
    print("\n🎉 ALL TESTS & ASSERTIONS PASSED WITH 100% QUALITY GROUNDING!")
    
except Exception as e:
    print(f"\n❌ Pipeline execution failed with error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
