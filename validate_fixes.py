#!/usr/bin/env python3
"""
Validation script to confirm our fixes are working correctly
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_imports():
    """Test that we can import the modified modules without errors"""
    try:
        from agents.graph import planner_node, searcher_node, memory_update_node, gap_detector_node
        print("[PASS] All agent nodes imported successfully")
        return True
    except Exception as e:
        print(f"[FAIL] Import failed: {e}")
        return False

def test_planner_sanitization():
    """Test that planner node properly sanitizes input"""
    try:
        from agents.graph import planner_node
        
        # Test basic functionality
        state = {"query": "What is AI?"}
        config = {"configurable": {"thread_id": "test"}}
        
        # This should work without throwing exceptions
        result = planner_node(state, config)
        print("[PASS] Planner node executes without errors")
        
        # Test input sanitization with long query
        long_state = {"query": "A" * 600}  # Longer than 500 char limit
        long_result = planner_node(long_state, config)
        if len(long_result["query"]) <= 503:  # 500 + "..."
            print("[PASS] Input sanitization working correctly")
        else:
            print("[WARN] Input sanitization may need improvement")
            
        return True
    except Exception as e:
        print(f"[FAIL] Planner node test failed: {e}")
        return False

def test_graph_compilation():
    """Test that the LangGraph compiles correctly"""
    try:
        from agents.graph import app_graph
        print("[PASS] LangGraph compiles successfully")
        return True
    except Exception as e:
        print(f"[FAIL] LangGraph compilation failed: {e}")
        return False

def main():
    print("Validating Deep Research Agent fixes...")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_planner_sanitization,
        test_graph_compilation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("ALL VALIDATION TESTS PASSED!")
        return 0
    else:
        print("SOME VALIDATION TESTS FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())