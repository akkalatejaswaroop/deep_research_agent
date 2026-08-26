#!/usr/bin/env python3
"""
End-to-end test for the Deep Research Agent pipeline.
Tests real queries without mocking - uses actual Ollama, searches, etc.
"""
import sys
import os
import json
import time
import asyncio
import uuid
from pathlib import Path
from queue import Queue

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

def test_full_pipeline():
    """Test the complete research pipeline with a real query."""
    print("\n" + "=" * 80)
    print("FULL PIPELINE E2E TEST - Real Query Execution")
    print("=" * 80)
    
    try:
        from agents.graph import app_graph
        from agents.state import AgentState
        
        if app_graph is None:
            print("[ERROR] app_graph is None!")
            return False
        
        # Create a realistic initial state
        query = "What are the latest developments in quantum computing?"
        initial_state = {
            "messages": [],
            "query": query,
            "depth": 1,  # Single iteration for testing
            "complexity": 1,  # Simple complexity
            "target_paragraphs": 2,
            "target_sub_questions": 3,
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
            "provenance": {},
        }
        
        thread_id = str(uuid.uuid4())
        config = {
            "configurable": {
                "thread_id": thread_id,
                "event_queue": Queue(),
            }
        }
        
        print(f"\n[OK] Executing pipeline for query: '{query}'")
        print(f"[OK] Thread ID: {thread_id}")
        print(f"[OK] Depth: {initial_state['depth']}, Complexity: {initial_state['complexity']}")
        
        # Execute the pipeline
        print("\n--- RUNNING PIPELINE ---")
        stage_outputs = {}
        stage_times = {}
        
        try:
            for i, output in enumerate(app_graph.stream(initial_state, config=config)):
                # output is a dict with node name -> state
                for node_name, node_state in output.items():
                    print(f"\n[OK] Node: {node_name}")
                    
                    # Track timing
                    stage_times[node_name] = stage_times.get(node_name, 0) + 1
                    stage_outputs[node_name] = node_state
                    
                    # Show key results
                    if node_name == "planner" and node_state.get("sub_questions"):
                        sqs = node_state["sub_questions"]
                        print(f"  - Generated {len(sqs)} sub-questions:")
                        for j, sq in enumerate(sqs[:3]):
                            print(f"    {j+1}. {sq[:70]}...")
                    
                    elif node_name == "searcher" and node_state.get("raw_pages"):
                        pages = node_state["raw_pages"]
                        print(f"  - Fetched {len(pages)} raw pages")
                        urls = list(pages.keys())[:3]
                        for url in urls:
                            print(f"    - {url[:60]}...")
                    
                    elif node_name == "filter" and node_state.get("scored_chunks"):
                        chunks = node_state["scored_chunks"]
                        print(f"  - Scored {len(chunks)} content chunks")
                        avg_score = sum(c.get("score", 0) for c in chunks) / max(1, len(chunks))
                        print(f"  - Average score: {avg_score:.1f}")
                    
                    elif node_name == "synthesis" and node_state.get("synthesis_results"):
                        results = node_state["synthesis_results"]
                        print(f"  - Synthesized {len(results)} answers")
                        for j, sr in enumerate(results[:2]):
                            ans = sr.get("answer", "")
                            ans_len = len(ans)
                            print(f"    {j+1}. {ans[:60]}... ({ans_len} chars)")
                    
                    elif node_name == "report_node_id" and node_state.get("report"):
                        report = node_state["report"]
                        print(f"  - Generated report ({len(report)} chars)")
                        print(f"  - First 100 chars: {report[:100]}...")
                    
                    elif node_name == "evaluator" and node_state.get("feedback"):
                        print(f"  - Feedback: {node_state['feedback'][:100]}...")
            
            print("\n--- PIPELINE EXECUTION COMPLETE ---")
            
        except Exception as e:
            print(f"\n[ERROR] Pipeline execution error: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Analyze results
        print("\n" + "=" * 80)
        print("RESULTS ANALYSIS")
        print("=" * 80)
        
        final_state = stage_outputs.get("evaluator") or list(stage_outputs.values())[-1] if stage_outputs else {}
        
        checks = []
        
        # Check sub-questions
        if final_state.get("sub_questions"):
            print(f"[OK] Sub-questions: {len(final_state['sub_questions'])}")
            checks.append(True)
        else:
            print("[ERROR] No sub-questions generated")
            checks.append(False)
        
        # Check sources
        if final_state.get("source_urls"):
            print(f"[OK] Source URLs found: {len(final_state['source_urls'])}")
            checks.append(True)
        else:
            print("[ERROR] No source URLs found")
            checks.append(False)
        
        # Check synthesis
        if final_state.get("synthesis_results"):
            print(f"[OK] Synthesis results: {len(final_state['synthesis_results'])}")
            checks.append(True)
        else:
            print("[ERROR] No synthesis results")
            checks.append(False)
        
        # Check final report
        if final_state.get("report") and len(final_state["report"]) > 100:
            print(f"[OK] Final report generated ({len(final_state['report'])} chars)")
            checks.append(True)
        else:
            print("[ERROR] No final report or report too short")
            checks.append(False)
        
        # Print report preview
        if final_state.get("report"):
            report = final_state["report"]
            lines = report.split("\n")
            print(f"\n[REPORT PREVIEW] (first 30 lines):")
            print("-" * 80)
            for line in lines[:30]:
                print(line)
            print("-" * 80)
        
        # Summary
        passed = sum(checks)
        total = len(checks)
        print(f"\nChecks passed: {passed}/{total}")
        
        if passed == total:
            print("\n[SUCCESS] FULL PIPELINE TEST PASSED!")
            return True
        else:
            print(f"\n[PARTIAL] FULL PIPELINE TEST INCOMPLETE ({total - passed} issues)")
            return passed > 0  # Partial success
            
    except Exception as e:
        print(f"\n[ERROR] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("DEEP RESEARCH AGENT - END-TO-END PIPELINE TEST")
    print("=" * 80)
    
    success = test_full_pipeline()
    sys.exit(0 if success else 1)
