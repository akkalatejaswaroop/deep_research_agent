"""Test urllib in a thread - does it timeout properly?"""
import sys, time, json, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

def call_llm(prompt):
    body = json.dumps({
        "model": "phi3:mini",
        "prompt": prompt,
        "temperature": 0.2,
        "stream": False,
        "options": {"num_predict": 50}
    }).encode()
    r = urllib.request.urlopen("http://127.0.0.1:11434/api/generate", data=body, timeout=10)
    data = json.loads(r.read())
    return data.get("response", "")

t0 = time.perf_counter()

# Test 1: single call
try:
    result = call_llm("What is 2+2? Answer briefly.")
    print(f"Single call: {time.perf_counter()-t0:.1f}s -> {result[:100]}", flush=True)
except Exception as e:
    print(f"Single call error after {time.perf_counter()-t0:.1f}s: {e}", flush=True)

# Test 2: 3 concurrent calls
t1 = time.perf_counter()
with ThreadPoolExecutor(max_workers=3) as ex:
    futures = [ex.submit(call_llm, "What is 2+2? Answer briefly.") for _ in range(3)]
    for f in as_completed(futures):
        try:
            r = f.result()
            print(f"  Concurrent: {time.perf_counter()-t1:.1f}s -> {r[:100]}", flush=True)
        except Exception as e:
            print(f"  Concurrent error: {e}", flush=True)
print(f"Total: {time.perf_counter()-t0:.1f}s", flush=True)
