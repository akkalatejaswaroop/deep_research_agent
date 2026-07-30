import urllib.request, json, time

t0 = time.perf_counter()
payload = json.dumps({
    "model": "phi3:mini",
    "prompt": "What is 2+2? Answer briefly.",
    "stream": False,
    "options": {"num_predict": 20}
}).encode()
resp_raw = urllib.request.urlopen(
    "http://localhost:11434/api/generate",
    data=payload,
    timeout=30
)
resp = json.loads(resp_raw.read())
elapsed = time.perf_counter() - t0
eval_dur = resp.get("eval_duration", 0) / 1e9
print(f"Time: {elapsed:.1f}s, eval_dur: {eval_dur:.1f}s")
print(f"Response: {resp.get('response','')[:200]}")
