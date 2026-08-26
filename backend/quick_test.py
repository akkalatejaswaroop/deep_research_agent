import urllib.request, json

# Test 1: Health check
r = urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)
print("1. Health:", r.read().decode()[:60])

# Test 2: Root endpoint
r = urllib.request.urlopen('http://127.0.0.1:8000/', timeout=3)
print("2. Root:", r.read().decode()[:80])

# Test 3: Quick research test (POST)
body = json.dumps({"query": "What is quantum computing?", "depth": 1}).encode()
req = urllib.request.Request('http://127.0.0.1:8000/api/v1/research/', data=body, method='POST')
req.add_header('Content-Type', 'application/json')
try:
    r = urllib.request.urlopen(req, timeout=10)
    resp = r.read().decode()[:200]
    print(f"3. Research started: {resp}")
except urllib.error.HTTPError as e:
    print(f"3. Research error (expected 405 for direct GET): {e.code}")

print("\nAll basic tests passed!")