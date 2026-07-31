import http.client
import json
import sys
import time
import re

body = json.dumps({
    'query': 'What is deep learning?',
    'depth': 1,
    'complexity': 1,
    'paragraphs': 2,
    'subQuestions': 3
})

conn = http.client.HTTPConnection('127.0.0.1', 8000, timeout=600)
conn.request('POST', '/api/v1/research/', body=body, headers={'Content-Type': 'application/json'})
resp = conn.getresponse()

t0 = time.time()
sys.stdout.write('Connected, status: ' + str(resp.status) + '\n')
sys.stdout.flush()

buffer = b''
report = None
scores = None
nodes_seen = []
last_report_time = 0

while True:
    if time.time() - t0 > 540:
        sys.stdout.write('Loop timeout at 540s\n')
        break
    try:
        chunk = resp.read1(8192)
        if not chunk:
            time.sleep(0.5)
            continue
        buffer += chunk
    except Exception as e:
        sys.stdout.write('Read error: ' + str(e) + '\n')
        break

    text = buffer.decode('utf-8', errors='replace')
    for line in text.split('\n'):
        if line.startswith('data: '):
            try:
                data = json.loads(line[6:])
                node = data.get('node')
                if node and isinstance(node, str) and node not in ('start', ''):
                    if node not in nodes_seen:
                        nodes_seen.append(node)
                if 'report' in data:
                    report = data['report']
                    last_report_time = time.time()
                if data.get('type') == 'quality_scores':
                    scores = data
            except:
                pass

    elapsed = time.time() - t0
    if int(elapsed) % 30 == 0 and elapsed > 0:
        status = 'DONE' if (report and scores) else 'running'
        sys.stdout.write('  [' + str(int(elapsed)) + 's] ' + str(len(buffer)) + ' bytes | nodes: ' + str(nodes_seen) + ' | ' + status + '\n')
        sys.stdout.flush()

    if report and scores:
        sys.stdout.write('Report + scores received, waiting for final flush...\n')
        break
    if report and (time.time() - last_report_time) > 10:
        break

total_time = time.time() - t0

sys.stdout.write('\n' + '='*60 + '\n')
sys.stdout.write('RESULTS\n')
sys.stdout.write('='*60 + '\n')
sys.stdout.write('Total time: ' + str(round(total_time, 1)) + 's\n')
sys.stdout.write('Bytes received: ' + str(len(buffer)) + '\n')
sys.stdout.write('Nodes executed: ' + str(nodes_seen) + '\n')
sys.stdout.write('Report generated: ' + str(report is not None) + '\n')

if report:
    sys.stdout.write('Report length: ' + str(len(report)) + ' chars\n')
    headers = re.findall(r'^## (.+)$', report, re.MULTILINE)
    sys.stdout.write('Sections: ' + str(headers) + '\n')

if scores:
    s = scores['scores']
    overall = scores.get('overall')
    sys.stdout.write('\nQuality Scores:\n')
    for k in ['relevance','depth','novelty','coherence','citation_accuracy']:
        sys.stdout.write('  ' + k + ': ' + str(s.get(k)) + '/10\n')
    sys.stdout.write('  overall: ' + str(overall) + '/10\n')

if report:
    empty_count = 0
    for s in re.split(r'^## ', report, flags=re.MULTILINE)[1:]:
        parts = s.split('\n', 1)
        body_content = parts[1].strip() if len(parts) > 1 else ''
        if len(body_content) < 50:
            empty_count += 1
    sys.stdout.write('Empty sections: ' + str(empty_count) + '\n')
    if 'INSUFFICIENT EVIDENCE' in report:
        sys.stdout.write('WARNING: INSUFFICIENT EVIDENCE markers found\n')

    sys.stdout.write('\n--- REPORT PREVIEW (first 2000 chars) ---\n')
    sys.stdout.write(report[:2000] + '\n')
else:
    sys.stdout.write('\nERROR: No report was generated\n')
    text = buffer.decode('utf-8', errors='replace')
    lines = text.split('\n')
    sys.stdout.write('Last events:\n')
    for l in lines[-10:]:
        sys.stdout.write('  ' + l[:200] + '\n')

sys.stdout.flush()
conn.close()
