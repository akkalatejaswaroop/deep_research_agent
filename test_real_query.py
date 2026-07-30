import json, urllib.request, sys

body = json.dumps({"query":"What is quantum computing?", "depth":1, "complexity":1, "paragraphs":1, "subQuestions":2}).encode()
req = urllib.request.Request("http://localhost:8000/api/v1/research/", data=body, headers={"Content-Type":"application/json"})
req.method = "POST"
print("Sending request...", flush=True)

try:
    resp = urllib.request.urlopen(req, timeout=900)
    text = resp.read().decode()
    print(f"Response: {len(text)} bytes", flush=True)

    for line in text.splitlines():
        line = line.strip()
        if line.startswith("data: "):
            try:
                e = json.loads(line[6:])
                if e.get("node") == "end":
                    r = e.get("report", "")
                    print(f"Report: {len(r)} chars", flush=True)
                    print(f"Source Notes count: {r.count('Source Notes')}", flush=True)
                    print(f"Preview: {r[:300]}", flush=True)
                elif e.get("node") == "error":
                    print(f"ERROR: {e}", flush=True)
            except json.JSONDecodeError:
                pass

    # Count node events
    import re
    nodes = []
    for line in text.splitlines():
        m = re.search(r'"node":"([^"]+)"', line)
        if m:
            nodes.append(m.group(1))
    print(f"Nodes seen: {set(nodes)}", flush=True)
except Exception as e:
    print(f"FAILED: {e}", flush=True)
