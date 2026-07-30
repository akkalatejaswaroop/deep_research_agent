"""Test raw requests.post to Ollama API."""
import sys, time
sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None
sys.path.insert(0, r"D:\deep_research_agent\backend")

import requests

t0 = time.perf_counter()
body = {
    "model": "phi3:mini",
    "messages": [{"role": "user", "content": "What is 2+2? Answer briefly."}],
    "temperature": 0.2,
    "stream": False,
    "options": {"num_predict": 20}
}

try:
    r = requests.post("http://127.0.0.1:11434/api/chat", json=body, timeout=10)
    data = r.json()
    content = data.get("message", {}).get("content", "")
    print(f"Time: {time.perf_counter()-t0:.1f}s", flush=True)
    print(f"Response: {content[:200]}", flush=True)
except Exception as e:
    print(f"Error after {time.perf_counter()-t0:.1f}s: {e}", flush=True)
