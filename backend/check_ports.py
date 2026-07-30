import urllib.request
import urllib.error
import json

urls = [
    "http://localhost:8002/health",
    "http://localhost:8002/api/copilotkit",
    "http://localhost:8002/api/v1/sessions",
    "http://localhost:8001/health",
    "http://localhost:8001/api/copilotkit"
]

for url in urls:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=2) as response:
            print(f"URL: {url} -> STATUS: {response.status}, BODY: {response.read()[:200]}")
    except urllib.error.HTTPError as e:
        print(f"URL: {url} -> HTTPError: {e.code}, BODY: {e.read()[:200]}")
    except Exception as e:
        print(f"URL: {url} -> Error: {e}")
