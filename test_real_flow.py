import sys; sys.path.insert(0, 'backend')
import os; os.environ['SIMULATED_MODE'] = 'false'
from fastapi.testclient import TestClient
import backend.main as m
import json, re

client = TestClient(m.app)

print('Sending real research query...')
res = client.post('/api/v1/research/', json={'query':'What is quantum computing?','depth':1,'complexity':1,'paragraphs':1,'subQuestions':2})

for line in res.text.splitlines():
    line = line.strip()
    if line.startswith('data: '):
        try:
            event = json.loads(line[6:])
            nd = event.get('node','')
            if nd:
                sys.stdout.write('.'); sys.stdout.flush()
            if nd == 'end':
                report = event.get('report','')
                metrics = event.get('metrics',{})
                qual = metrics.get('quality',{})
                sn_count = report.count('Source Notes')
                print()
                print()
                print('='*60)
                print('RESULT SUMMARY')
                print('='*60)
                print('Report length: ' + str(len(report)) + ' chars')
                print('Source Notes remaining: ' + str(sn_count))
                print('Quality overall: ' + str(qual.get('overall','N/A')))
                scores = qual.get('scores',{})
                print('Scores: ' + str(scores))
                
                if sn_count == 0:
                    print()
                    print('SUCCESS: All Source Notes stripped!')
                else:
                    print()
                    print('WARNING: ' + str(sn_count) + ' Source Notes still present')
                    positions = []
                    idx = 0
                    while True:
                        idx = report.find('Source Notes', idx)
                        if idx == -1:
                            break
                        positions.append(idx)
                        idx += 1
                    for p in positions:
                        ctx = report[max(0,p-50):p+100]
                        print('  At pos ' + str(p) + ': ...' + repr(ctx) + '...')
        except:
            pass
print('DONE')
