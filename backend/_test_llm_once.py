"""Test a single real LLM call."""
import sys, os, time
os.environ["PREFER_LLM"] = "true"
sys.path.insert(0, r"D:\deep_research_agent\backend")

import main as m

print("Testing call_llm with real Ollama (qwen2.5:3b)...", flush=True)
t0 = time.perf_counter()
result = m.call_llm("What is the greenhouse effect? Answer in one sentence.", "You are a helpful assistant.")
elapsed = time.perf_counter() - t0
print(f"Result: {str(result)[:200] if result else 'EMPTY'}", flush=True)
print(f"Time: {elapsed:.1f}s", flush=True)
print(f"Model: qwen2.5:3b", flush=True)
print(f"Ollama models: {m._ollama_model_ok.get('_all', [])}", flush=True)
