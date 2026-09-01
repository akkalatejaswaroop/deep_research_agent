#!/usr/bin/env python3
"""
Test runner for Deep Research Agent
"""
import unittest
import sys
import os

# Add the backend directory to the path so we can import agents
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def run_all_tests():
    """Discover and run all unit tests"""
    # Discover tests in the tests/unit directory
    loader = unittest.TestLoader()
    start_dir = 'tests/unit'
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return exit code based on test results
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    exit_code = run_all_tests()
    sys.exit(exit_code)