import json, re, urllib.request, urllib.error, sys

host = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
body = json.dumps({"query":"What is quantum computing?","depth":1,"complexity":1,"paragraphs":1,"subQuestions":2}).encode()
req = urllib.request.Request(host + "/api/v1/research/", data=body, headers={"Content-Type":"application/json"})
req.method = "POST"

try:
    resp = urllib.request.urlopen(req, timeout=900)
    text = resp.read().decode()
    report = ""
    source_urls = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("data: "):
            try:
                e = json.loads(line[6:])
                if e.get("report"):
                    report = e["report"]
                if e.get("source_urls"):
                    source_urls = e["source_urls"]
            except:
                pass
    print("Report chars: " + str(len(report)))
    idx = report.find("### Source Notes")
    print("First ### Source Notes at offset " + str(idx))
    print("After regex strip: " + str(report.count("Source Notes")) + " Source Notes remaining")
    print("Source URLs: " + str(len(source_urls)))
    print("DONE")
except Exception as e:
    print("ERROR: " + str(e))
