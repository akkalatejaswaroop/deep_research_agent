#!/usr/bin/env python3
"""
Comprehensive application test suite to identify all issues.
"""
import sys
import os
import json
import asyncio
import traceback
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

def test_imports():
    """Test all critical imports."""
    print("=" * 80)
    print("TEST 1: Critical Imports")
    print("=" * 80)
    
    try:
        print("✓ Importing FastAPI...")
        from fastapi import FastAPI
        print("✓ FastAPI imported")
        
        print("✓ Importing LangGraph...")
        from langgraph.graph import StateGraph
        print("✓ LangGraph imported")
        
        print("✓ Importing backend.agents.state...")
        from agents.state import AgentState
        print("✓ AgentState imported")
        
        print("✓ Importing backend.agents.graph...")
        from agents.graph import (
            planner_node, searcher_node, filter_node, synthesis_node,
            gap_detector_node, citation_mapper_node, report_node, evaluator_node,
            app_graph
        )
        print("✓ All graph nodes imported")
        print("✓ app_graph imported")
        
        print("✓ Importing backend.db...")
        from db import supabase_client, in_memory_knowledge
        print(f"  - Supabase client: {type(supabase_client)}")
        print(f"  - In-memory knowledge: {len(in_memory_knowledge)} items")
        
        print("\n✅ All critical imports successful!")
        return True
    except Exception as e:
        print(f"\n❌ Import error: {e}")
        traceback.print_exc()
        return False

def test_graph_structure():
    """Test LangGraph structure."""
    print("\n" + "=" * 80)
    print("TEST 2: LangGraph Structure")
    print("=" * 80)
    
    try:
        from agents.graph import app_graph
        
        if app_graph is None:
            print("❌ app_graph is None!")
            return False
            
        print(f"✓ Graph type: {type(app_graph)}")
        print(f"✓ Graph has {len(app_graph.nodes)} nodes")
        print("  Nodes:")
        for node_name in app_graph.nodes:
            print(f"    - {node_name}")
        
        print(f"✓ Graph has edges")
        print("\n✅ Graph structure valid!")
        return True
    except Exception as e:
        print(f"\n❌ Graph structure error: {e}")
        traceback.print_exc()
        return False

def test_config_env():
    """Test environment configuration."""
    print("\n" + "=" * 80)
    print("TEST 3: Environment Configuration")
    print("=" * 80)
    
    from dotenv import load_dotenv
    load_dotenv()
    
    critical_vars = [
        "OLLAMA_HOST",
        "LLM_TIMEOUT",
        "CORS_ORIGINS",
        "PLANNER_MODEL",
        "FILTER_MODEL",
        "SYNTHESIS_MODEL",
        "REPORT_MODEL",
    ]
    
    print("Environment variables:")
    for var in critical_vars:
        value = os.getenv(var, "NOT SET")
        print(f"  {var}: {value if len(value) < 50 else value[:47] + '...'}")
    
    print("\n✅ Environment check complete")
    return True

def test_simple_query():
    """Test a simple query execution."""
    print("\n" + "=" * 80)
    print("TEST 4: Simple Query Execution")
    print("=" * 80)
    
    try:
        from agents.graph import app_graph
        from agents.state import AgentState
        import uuid
        
        # Create a minimal state
        initial_state = {
            "messages": [],
            "query": "What is artificial intelligence?",
            "depth": 1,
            "complexity": 1,
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
                "event_queue": None,
            }
        }
        
        print(f"✓ Initial state created")
        print(f"✓ Thread ID: {thread_id}")
        print(f"✓ Query: {initial_state['query']}")
        
        # Try to run just the planner node
        print("\n✓ Running planner node...")
        from agents.graph import planner_node
        from queue import Queue
        
        config["configurable"]["event_queue"] = Queue()
        result = planner_node(initial_state, config)
        
        print(f"  - Sub-questions generated: {len(result.get('sub_questions', []))}")
        print(f"  - Search queries generated: {len(result.get('search_queries', []))}")
        
        if result.get('sub_questions'):
            for i, sq in enumerate(result['sub_questions'][:3]):
                print(f"    {i+1}. {sq[:60]}...")
        
        print("\n✅ Query execution test passed!")
        return True
    except Exception as e:
        print(f"\n❌ Query execution error: {e}")
        traceback.print_exc()
        return False

def test_llm_availability():
    """Test LLM availability."""
    print("\n" + "=" * 80)
    print("TEST 5: LLM Availability")
    print("=" * 80)
    
    try:
        from agents.graph import _ollama_has_model, get_llm
        import os
        
        models_to_check = [
            "phi3:mini",
            "llama2:latest",
            "neural-chat",
        ]
        
        print("Checking local Ollama models:")
        for model in models_to_check:
            has_it = _ollama_has_model(model)
            print(f"  {model}: {'✓ Available' if has_it else '✗ Not available'}")
        
        # Check API LLM
        api_key = os.getenv("API_LLM_API_KEY")
        api_base = os.getenv("API_LLM_BASE_URL")
        
        if api_key or api_base:
            print(f"\n  API LLM configured: Yes")
            print(f"    - API_LLM_API_KEY: {'***SET***' if api_key else 'NOT SET'}")
            print(f"    - API_LLM_BASE_URL: {api_base or 'NOT SET'}")
        else:
            print(f"\n  API LLM configured: No")
        
        print("\n✅ LLM availability check complete")
        return True
    except Exception as e:
        print(f"\n❌ LLM check error: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "DEEP RESEARCH AGENT - COMPREHENSIVE TEST" + " " * 18 + "║")
    print("╚" + "═" * 78 + "╝")
    
    tests = [
        ("Critical Imports", test_imports),
        ("LangGraph Structure", test_graph_structure),
        ("Environment Configuration", test_config_env),
        ("LLM Availability", test_llm_availability),
        ("Simple Query Execution", test_simple_query),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            results.append((test_name, test_func()))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' crashed: {e}")
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
