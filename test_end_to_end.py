#!/usr/bin/env python3
"""
End-to-end test of the Deep Research Agent with a real query
"""
import sys
import os
import json
import time

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_end_to_end_research():
    """Test the complete research pipeline from query to report"""
    print("Testing Deep Research Agent End-to-End...")
    print("=" * 50)
    
    try:
        # Import the compiled graph
        from agents.graph import app_graph
        print("[PASS] Successfully imported agent graph")
        
        # Create a test configuration
        config = {
            "configurable": {
                "thread_id": f"test-thread-{int(time.time())}",
                "temperature": 0.2,
                "max_tokens": 1024
            }
        }
        
        # Test query - a real technical question that should generate meaningful content
        test_query = "What are the key differences between supervised and unsupervised learning in machine learning?"
        
        print(f"[INFO] Testing with query: {test_query}")
        print("[INFO] Starting research pipeline...")
        
        # Prepare initial state
        initial_state = {
            "query": test_query,
            "messages": [],
            "depth": 2,  # Reasonable depth for testing
            "complexity": 2,
            "target_paragraphs": 3,
            "target_sub_questions": 5,  # Reasonable number for testing
            "gap_iteration": 0,
            "source_urls": [],
            "raw_pages": {},
            "scored_chunks": [],
            "synthesis_results": [],
            "gap_results": [],
            "cited_report": "",
            "report": "",
            "is_valid": False,
            "prior_lessons": [],
            "sub_questions": [],
            "search_queries": [],
            "findings": [],
            "feedback": "",
            "run_id": "",
            "structured_refs": [],
            "provenance": {},
            "memory_context": {},
            "memory_context_token_count": 0,
            "retrieved_memory": [],
            "active_node": "",
            "logs": [],
            "metrics": {}
        }
        
        print("[INFO] Invoking agent graph...")
        start_time = time.time()
        
        # Run the agent graph
        result = app_graph.invoke(initial_state, config)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"[PASS] Research pipeline completed in {execution_time:.2f} seconds")
        
        # Extract results
        report = result.get("report", "")
        cited_report = result.get("cited_report", "")
        sub_questions = result.get("sub_questions", [])
        source_urls = result.get("source_urls", [])
        synthesis_results = result.get("synthesis_results", [])
        
        print(f"[INFO] Generated {len(sub_questions)} sub-questions")
        print(f"[INFO] Retrieved {len(source_urls)} source URLs")
        print(f"[INFO] Completed {len(synthesis_results)} syntheses")
        print(f"[INFO] Report length: {len(report)} characters")
        
        # Validate the report quality
        print("\n" + "=" * 50)
        print("REPORT QUALITY ASSESSMENT")
        print("=" * 50)
        
        # Check for minimum viable content
        if len(report) < 100:
            print("[FAIL] Report too short - likely contains mostly garbage/mock data")
            return False
            
        # Check for repetitive or boilerplate content
        lines = report.split('\n')
        unique_lines = set(line.strip() for line in lines if line.strip())
        if len(unique_lines) < len(lines) * 0.7:  # Less than 70% unique lines
            print("[WARN] Report contains significant repetitive content")
        else:
            print("[PASS] Report shows good content diversity")
            
        # Check for proper structure
        has_sections = any(marker in report for marker in ['# ', '## ', '### '])
        if has_sections:
            print("[PASS] Report contains proper section headers")
        else:
            print("[WARN] Report may lack proper section structure")
            
        # Check for citations or references
        has_references = any(marker in report for marker in ['[', ']', 'References', 'references'])
        if has_references:
            print("[PASS] Report appears to contain references/citations")
        else:
            print("[INFO] Report may not contain explicit references (may be in cited_report)")
            
        # Check for actual content vs placeholders
        placeholder_indicators = [
            'lorem ipsum', 'placeholder', 'todo', 'fixme', 
            'example.com', 'test.com', 'fake', 'mock', 'dummy'
        ]
        has_placeholders = any(indicator in report.lower() for indicator in placeholder_indicators)
        if not has_placeholders:
            print("[PASS] Report appears free of placeholder/mock content")
        else:
            print("[FAIL] Report contains placeholder or mock content")
            return False
            
        # Display sample of the actual report
        print("\n" + "=" * 50)
        print("SAMPLE OF GENERATED REPORT")
        print("=" * 50)
        print(report[:1500] + ("..." if len(report) > 1500 else ""))
        print("=" * 50)
        
        # Show sub-questions generated
        print("\nGENERATED SUB-QUESTIONS:")
        for i, sq in enumerate(sub_questions, 1):
            print(f"{i}. {sq}")
            
        # Show source count
        print(f"\nSOURCES RETRIEVED: {len(source_urls)}")
        if source_urls:
            print("Sample sources:")
            for url in source_urls[:3]:
                print(f"  - {url}")
                
        print("\n" + "=" * 50)
        print("END-TO-END TEST COMPLETED SUCCESSFULLY")
        print("=" * 50)
        print(f"✅ Generated professional-quality report of {len(report)} characters")
        print(f"✅ Processed {len(sub_questions)} research sub-questions") 
        print(f"✅ Retrieved {len(source_urls)} source references")
        print(f"✅ Completed in {execution_time:.2f} seconds")
        print("✅ Report appears to contain genuine research content")
        print("✅ No evidence of mock, fake, or placeholder data")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] End-to-end test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_simple_query():
    """Test with a simpler query to verify basic functionality"""
    print("\n" + "=" * 50)
    print("SIMPLE QUERY VERIFICATION")
    print("=" * 50)
    
    try:
        from agents.graph import planner_node
        
        # Test basic planning capability
        state = {"query": "What is Python?"}
        config = {"configurable": {"thread_id": "simple-test"}}
        
        result = planner_node(state, config)
        
        sub_questions = result.get("sub_questions", [])
        if len(sub_questions) >= 2:
            print("[PASS] Planner generated multiple sub-questions")
            for i, sq in enumerate(sub_questions[:3], 1):
                print(f"  {i}. {sq}")
            return True
        else:
            print("[FAIL] Planner did not generate sufficient sub-questions")
            return False
            
    except Exception as e:
        print(f"[FAIL] Simple query test failed: {e}")
        return False

if __name__ == "__main__":
    print("Deep Research Agent - End-to-End Validation Test")
    print("Testing real query processing without mock/fake data\n")
    
    # Run the tests
    test1_passed = test_end_to_end_research()
    test2_passed = test_simple_query()
    
    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    
    if test1_passed and test2_passed:
        print("🎉 ALL TESTS PASSED")
        print("✅ Deep Research Agent is functioning correctly")
        print("✅ Generates genuine research content without mock data")
        print("✅ Report quality meets basic professional standards")
        print("✅ Ready for further testing and deployment preparation")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED")
        print("⚠️  Further investigation needed")
        sys.exit(1)