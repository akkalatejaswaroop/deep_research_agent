"""Test call_llm from the main module."""
import sys, time, os
sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None
sys.path.insert(0, r"D:\deep_research_agent\backend")

t0 = time.perf_counter()
import main as m
print(f"Import: {time.perf_counter()-t0:.1f}s", flush=True)

t1 = time.perf_counter()
result = m.call_llm("What is 2+2? Answer briefly.", "")
elapsed = time.perf_counter() - t1
print(f"call_llm: {elapsed:.1f}s", flush=True)
print(f"Result: '{result[:200]}'", flush=True)
