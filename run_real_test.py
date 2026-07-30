import sys; sys.path.insert(0, 'backend')
import os; os.environ['SIMULATED_MODE'] = 'false'
from fastapi.testclient import TestClient
import backend.main as m
import json

client = TestClient(m.app)
res = client.post('/api/v1/research/', json={'query':'What is quantum computing?','depth':1,'complexity':1,'paragraphs':1,'subQuestions':2})

for line in res.text.splitlines():
    line = line.strip()
    if line.startswith('data: '):
        try:
            event = json.loads(line[6:])
            if event.get('node') == 'end':
                report = event.get('report','')
                metrics = event.get('metrics')
                print(f'REPORT_LENGTH: {len(report)}')
                qual = metrics.get('quality',{}).get('overall','N/A') if metrics else 'N/A'
                print(f'QUALITY_SCORE: {qual}')
                with open('D:\\deep_research_agent\\real_report.txt', 'w', encoding='utf-8') as f:
                    f.write(report)
                print('Report saved to real_report.txt')
        except:
            pass
print('DONE')
