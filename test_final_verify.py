import sys; sys.path.insert(0, 'backend')
import os; os.environ['SIMULATED_MODE'] = 'false'
from fastapi.testclient import TestClient
import backend.main as m

client = TestClient(m.app)
res = client.post('/api/v1/research/', json={
    'query': 'What is quantum computing?',
    'depth': 1, 'complexity': 1,
    'paragraphs': 1, 'subQuestions': 2
})

report = ''
nodes = set()
has_error = False

for line in res.text.splitlines():
    line = line.strip()
    if line.startswith('data: '):
        import json
        try:
            e = json.loads(line[6:])
            if e.get('node'):
                nodes.add(e['node'])
            if e.get('node') == 'error':
                has_error = True
            if e.get('report'):
                report = e['report']
        except:
            pass

print(f'Nodes: {len(nodes)} ({", ".join(sorted(nodes))})')
print(f'Report chars: {len(report)}')
print(f'Has error: {has_error}')
print(f'Source Notes count: {report.count("Source Notes")}')
print(f'First 300 chars: {report[:300]}')
print(f'Last 200 chars: {report[-200:]}')
print('PASS' if not has_error and len(report) > 1000 and report.count('Source Notes') == 0 else 'FAIL')
