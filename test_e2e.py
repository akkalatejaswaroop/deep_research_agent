import sys; sys.path.insert(0, 'backend')
import os; os.environ['SIMULATED_MODE'] = 'true'
from fastapi.testclient import TestClient
import backend.main as m

client = TestClient(m.app)
r = client.post('/api/v1/research/', json={
    'query': 'test', 'depth': 1, 'complexity': 1,
    'paragraphs': 1, 'subQuestions': 2
})

nodes = set()
source_urls = []
structured_refs = []
metrics = None
report = ""
error = False

for line in r.text.splitlines():
    line = line.strip()
    if line.startswith('data: '):
        try:
            import json
            e = json.loads(line[6:])
            if e.get('node') == 'error':
                error = True
            if e.get('node'):
                nodes.add(e['node'])
            if 'source_urls' in e:
                source_urls = e['source_urls']
            if 'structured_refs' in e:
                structured_refs = e['structured_refs']
            if '_metrics' in e:
                metrics = e['_metrics']
            if 'report' in e:
                report = e['report']
        except:
            pass

expected = {'planner','memory_retrieval','searcher','filter','synthesis','gap_detector','citation_mapper','report_node_id','evaluator','end'}
missing = expected - nodes

print(f'NODES: {len(nodes)}/{len(expected)}')
print(f'MISSING: {missing if missing else "none"}')
print(f'REPORT: {len(report)} chars' if report else 'NO REPORT')
print(f'URLS: {len(source_urls)}' if source_urls else 'NO URLS')
print(f'REFS: {len(structured_refs)}' if structured_refs else 'NO REFS')
print(f'METRICS: {metrics is not None}' if metrics else 'NO METRICS')
print(f'STATUS: {"PASS" if not error and not missing else "FAIL"}')
