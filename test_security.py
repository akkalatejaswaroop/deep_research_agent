#!/usr/bin/env python3
"""
Test the security fixes (rate limiting, input validation, auth).
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_rate_limiting_config():
    """Test that rate limiting configuration is present."""
    print("Testing rate limiting configuration...")
    
    try:
        import main
        
        # Check that rate limiting config exists
        assert hasattr(main, '_RATE_LIMIT_ENABLED')
        assert hasattr(main, '_RATE_LIMIT_REQUESTS_PER_MINUTE')
        assert hasattr(main, '_rate_limit_storage')
        assert hasattr(main, '_rate_limit_lock')
        assert hasattr(main, '_is_rate_limited')
        
        print("[PASS] Rate limiting configuration present")
        print(f"    Rate limiting enabled: {main._RATE_LIMIT_ENABLED}")
        print(f"    Requests per minute: {main._RATE_LIMIT_REQUESTS_PER_MINUTE}")
        return True
    except Exception as e:
        print(f"[FAIL] Rate limiting configuration test: {e}")
        return False

def test_input_validation():
    """Test that input validation works."""
    print("\nTesting input validation...")
    
    try:
        from main import ResearchQuery
        
        # Test valid input
        query = ResearchQuery(query="test query", depth=1, complexity=1)
        assert query.query == "test query"
        print("[PASS] Valid input accepted")
        
        # Test empty query rejection
        try:
            ResearchQuery(query="", depth=1)
            print("[FAIL] Empty query should have been rejected")
            return False
        except Exception:
            print("[PASS] Empty query correctly rejected")
            
        # Test query length limit
        try:
            ResearchQuery(query="x" * 1001, depth=1)
            print("[FAIL] Long query should have been rejected")
            return False
        except Exception:
            print("[PASS] Long query correctly rejected")
            
        # Test parameter bounds
        try:
            ResearchQuery(query="test", depth=15)  # Should be max 10
            print("[FAIL] Depth >10 should have been rejected")
            return False
        except Exception:
            print("[PASS] Depth >10 correctly rejected")
            
        return True
    except Exception as e:
        print(f"[FAIL] Input validation test failed: {e}")
        return False

def test_auth_config():
    """Test that authentication configuration is present."""
    print("\nTesting authentication configuration...")
    
    try:
        import main
        
        # Check that auth config exists
        assert hasattr(main, '_AUTH_ENABLED')
        assert hasattr(main, '_API_KEYS')
        assert hasattr(main, '_verify_api_key')
        
        print("[PASS] Authentication configuration present")
        print(f"    Auth enabled: {main._AUTH_ENABLED}")
        print(f"    API keys configured: {len(main._API_KEYS)}")
        return True
    except Exception as e:
        print(f"[FAIL] Authentication configuration test: {e}")
        return False

def test_endpoints_have_security():
    """Test that endpoints have security checks."""
    print("\nTesting endpoint security integration...")
    
    try:
        import main
        import inspect
        
        # Check that start_research function has the security parameters
        start_research_source = inspect.getsource(main.start_research)
        assert 'request: Request' in start_research_source
        assert '_verify_api_key(request)' in start_research_source
        assert '_is_rate_limited(client_ip)' in start_research_source
        
        print("[PASS] start_research endpoint has security checks")
        return True
    except Exception as e:
        print(f"[FAIL] Endpoint security test: {e}")
        return False

def main():
    """Run all security tests."""
    print("=" * 60)
    print("TESTING REX SECURITY FIXES")
    print("=" * 60)
    
    tests = [
        test_rate_limiting_config,
        test_input_validation,
        test_auth_config,
        test_endpoints_have_security,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed}/{total} security tests passed")
    
    if passed == total:
        print("ALL SECURITY TESTS PASSED!")
        return True
    else:
        print("SOME SECURITY TESTS FAILED")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)