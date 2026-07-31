import http.client
import json
import sys
import time
import re

conn = http.client.HTTPConnection('127.0.0.1', 8000, timeout=300)
body = json.dumps({
    'query': 'deep learning basics',
    'depth': 1,
    'complexity': 1,
    'paragraphs': 2,
    'subQuestions': 3
})
conn.request('POST', '/api/v1/research/', body=body, headers={'Content-Type': 'application/json'})
resp = conn.getresponse()
sys.stdout.write('Status: ' + str(resp.status) + ' ' + str(resp.reason) + '\n')

t0 = time.time()
buffer = b''
report = None
scores = None

while True:
    try:
        chunk = resp.read(4096)
        if not chunk:
            break
        buffer += chunk
        text = buffer.decode('utf-8', errors='replace')
        for line in text.split('\n'):
            if line.startswith('data: '):
                try:
                    data = json.loads(line[6:])
                    if 'report' in data:
                        report = data['report']
                    if data.get('type') == 'quality_scores':
                        scores = data
                except:
                    pass
        elapsed = time.time() - t0
        if int(elapsed) % 30 == 0 and elapsed > 0:
            status = 'report done' if report else 'streaming'
            sys.stdout.write('  [' + str(int(elapsed)) + 's] ' + str(len(buffer)) + ' bytes - ' + status + '\n')
            sys.stdout.flush()
    except Exception as e:
        sys.stdout.write('Read error: ' + str(e) + '\n')
        break
    if report and scores:
        break
    if time.time() - t0 > 240:
        sys.stdout.write('Timeout reached\n')
        break

elapsed = time.time() - t0
sys.stdout.write('\n=== RESULTS ===\n')
sys.stdout.write('Time: ' + str(int(elapsed)) + 's\n')
sys.stdout.write('Bytes: ' + str(len(buffer)) + '\n')
sys.stdout.write('Report: ' + str(report is not None) + '\n')
sys.stdout.write('Scores: ' + str(scores is not None) + '\n')

if report:
    sys.stdout.write('Report length: ' + str(len(report)) + ' chars\n')
    headers = re.findall(r'^## (.+)$', report, re.MULTILINE)
    sys.stdout.write('Sections: ' + str(headers) + '\n')
    if scores:
        s = scores['scores']
        sys.stdout.write('Quality: rel=' + str(s.get('relevance')) + ' depth=' + str(s.get('depth')) +
            ' nov=' + str(s.get('novelty')) + ' coh=' + str(s.get('coherence')) +
            ' cit=' + str(s.get('citation_accuracy')) + ' overall=' + str(scores.get('overall')) + '\n')
    # Check empty sections
    empty_count = 0
    for s in re.split(r'^## ', report, flags=re.MULTILINE)[1:]:
        parts = s.split('\n', 1)
        if len(parts) > 1 and len(parts[1].strip()) < 50:
            empty_count += 1
        elif len(parts) == 1:
            empty_count += 1
    sys.stdout.write('Empty sections: ' + str(empty_count) + '\n')
    if 'INSUFFICIENT EVIDENCE' in report:
        sys.stdout.write('WARNING: INSUFFICIENT EVIDENCE markers found\n')
    sys.stdout.write('\n--- PREVIEW (first 1500 chars) ---\n')
    sys.stdout.write(report[:1500] + '\n')
else:
    sys.stdout.write('\n--- No report in response ---\n')
    # Show last 5 lines
    lines = buffer.decode('utf-8', errors='replace').split('\n')
    sys.stdout.write('Last events:\n')
    for l in lines[-5:]:
        sys.stdout.write('  ' + l[:200] + '\n')

sys.stdout.flush()
