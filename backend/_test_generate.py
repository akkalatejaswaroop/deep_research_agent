"""Test raw requests.post to Ollama /api/generate endpoint."""
import sys, time, requests

t0 = time.perf_counter()
body = {
    "model": "phi3:mini",
    "prompt": "What is 2+2? Answer briefly.",
    "stream": False,
    "options": {"num_predict": 20}
}

try:
    r = requests.post("http://127.0.0.1:11434/api/generate", json=body, timeout=10)
    data = r.json()
    content = data.get("response", "")
    print(f"Time: {time.perf_counter()-t0:.1f}s", flush=True)
    print(f"Response: {content[:200]}", flush=True)
except Exception as e:
    print(f"Error after {time.perf_counter()-t0:.1f}s: {e}", flush=True)
