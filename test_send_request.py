import json, urllib.request, sys, time

body = json.dumps({"query":"What is quantum computing?", "depth":1, "complexity":1, "paragraphs":1, "subQuestions":2}).encode()
req = urllib.request.Request("http://localhost:8000/api/v1/research/", data=body, headers={"Content-Type":"application/json"})
req.method = "POST"
print(f"Request sent at {time.strftime('%H:%M:%S')}", flush=True)

try:
    resp = urllib.request.urlopen(req, timeout=900)
    text = resp.read().decode()
    print(f"Response received at {time.strftime('%H:%M:%S')}", flush=True)
    print(f"Response length: {len(text)}", flush=True)

    node_events = []
    report = ""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("data: "):
            try:
                e = json.loads(line[6:])
                if "node" in e:
                    node_events.append(e["node"])
                if e.get("report"):
                    report = e["report"]
            except:
                pass

    print(f"Node events ({len(node_events)}): {', '.join(node_events)}", flush=True)
    print(f"Report length: {len(report)}", flush=True)
    if report:
        idx = report.find("### Source Notes")
        print(f"First ### Source Notes at offset: {idx}", flush=True)
        print(f"Report preview: {report[:300]}", flush=True)
except Exception as e:
    print(f"ERROR: {e}", flush=True)
