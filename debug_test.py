#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

import main

print("Checking main module attributes:")
attrs = [attr for attr in dir(main) if not attr.startswith('_')]
print(f"Public attributes: {attrs}")

print("\nChecking for rate limiting attributes:")
rate_attrs = [attr for attr in dir(main) if 'rate' in attr.lower() or 'RATE' in attr]
print(f"Rate limiting attributes: {rate_attrs}")

print("\nChecking specifically:")
print(f"_RATE_LIMIT_ENABLED: {hasattr(main, '_RATE_LIMIT_ENABLED')}")
print(f"_RATE_LIMIT_REQUESTS_PER_MINUTE: {hasattr(main, '_RATE_LIMIT_REQUESTS_PER_MINUTE')}")
print(f"_rate_limit_storage: {hasattr(main, '_rate_limit_storage')}")
print(f"_rate_limit_lock: {hasattr(main, '_rate_limit_lock')}")

if hasattr(main, '_RATE_LIMIT_ENABLED'):
    print(f"_RATE_LIMIT_ENABLED value: {main._RATE_LIMIT_ENABLED}")
if hasattr(main, '_RATE_LIMIT_REQUESTS_PER_MINUTE'):
    print(f"_RATE_LIMIT_REQUESTS_PER_MINUTE value: {main._RATE_LIMIT_REQUESTS_PER_MINUTE}")