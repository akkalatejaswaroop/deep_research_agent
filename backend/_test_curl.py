"""Test subprocess curl to Ollama."""
import sys, time, json, subprocess

t0 = time.perf_counter()
body = json.dumps({
    "model": "phi3:mini",
    "prompt": "What is 2+2? Answer briefly.",
    "temperature": 0.2,
    "stream": False,
    "options": {"num_predict": 20}
})

try:
    r = subprocess.run(
        ["curl", "-s", "--max-time", "10",
         "-d", body,
         "http://127.0.0.1:11434/api/generate"],
        capture_output=True, text=True, timeout=15
    )
    print(f"Return code: {r.returncode}", flush=True)
    print(f"Time: {time.perf_counter()-t0:.1f}s", flush=True)
    if r.returncode == 0:
        data = json.loads(r.stdout)
        print(f"Response: {data.get('response','')[:200]}", flush=True)
    else:
        print(f"Stderr: {r.stderr[:300]}", flush=True)
except Exception as e:
    print(f"Error after {time.perf_counter()-t0:.1f}s: {e}", flush=True)
