import urllib.request
import json
import sys
import io
import re
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

body = json.dumps({
    'query': 'What is deep learning?',
    'depth': 1,
    'complexity': 1,
    'paragraphs': 2,
    'subQuestions': 4
}).encode()

req = urllib.request.Request(
    'http://127.0.0.1:8000/api/v1/research/',
    data=body,
    headers={'Content-Type': 'application/json'}
)

t0 = time.time()
try:
    resp = urllib.request.urlopen(req, timeout=300)
    buffer = b''
    while True:
        chunk = resp.read(8192)
        if not chunk:
            break
        buffer += chunk
except Exception as e:
    sys.stdout.write('ERROR: ' + str(e) + '\n')
    sys.stdout.flush()
    exit(1)

text = buffer.decode('utf-8', errors='replace')
elapsed = time.time() - t0

# Parse events
report = None
scores = None
nodes = []
thoughts = []
for line in text.split('\n'):
    if line.startswith('data: '):
        try:
            data = json.loads(line[6:])
            if 'report' in data:
                report = data['report']
            if data.get('type') == 'quality_scores':
                scores = data
            if 'node' in data and isinstance(data.get('node'), str):
                if data['node'] not in ('start', ''):
                    nodes.append(data['node'])
            if data.get('type') == 'thought':
                thoughts.append(data['message'][:80])
        except:
            pass

sys.stdout.write(f'Time: {elapsed:.1f}s\n')
sys.stdout.write(f'Events: {len(text.split(chr(10)))} lines\n')
sys.stdout.write(f'Nodes executed: {len(set(nodes))} - {list(dict.fromkeys(nodes))}\n')

if scores:
    s = scores['scores']
    sys.stdout.write(f'Quality: rel={s.get("relevance")} depth={s.get("depth")} nov={s.get("novelty")} coh={s.get("coherence")} cit={s.get("citation_accuracy")} overall={scores.get("overall")}\n')

if report:
    sys.stdout.write(f'Report: {len(report)} chars\n')
    # Check structure
    headers = re.findall(r'^## (.+)$', report, re.MULTILINE)
    sys.stdout.write(f'Sections: {headers}\n')
    # Check for issues
    issues = []
    if 'INSUFFICIENT EVIDENCE' in report:
        issues.append('INSUFFICIENT_EVIDENCE markers')
    sections = re.split(r'^## ', report, flags=re.MULTILINE)
    empty_count = 0
    for s in sections[1:]:
        h = s.split('\n')[0].strip()
        b = '\n'.join(s.split('\n')[1:]).strip()
        if not b or len(b) < 50:
            empty_count += 1
            issues.append(f'empty section: {h}')
    if empty_count:
        sys.stdout.write(f'Empty sections: {empty_count}\n')
    sys.stdout.write(f'Issues: {issues if issues else "None"}\n')
    sys.stdout.write('\n--- Report Preview (first 1500 chars) ---\n')
    sys.stdout.write(report[:1500] + '\n')
else:
    sys.stdout.write('NO REPORT FOUND\n')
    # Show last few events
    last_events = text.split('\n')[-10:]
    sys.stdout.write('Last events:\n')
    for ev in last_events:
        sys.stdout.write('  ' + ev[:200] + '\n')

sys.stdout.flush()
