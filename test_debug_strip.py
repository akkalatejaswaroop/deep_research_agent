import sys; sys.path.insert(0, 'backend')
import os; os.environ['SIMULATED_MODE'] = 'false'
from fastapi.testclient import TestClient
import backend.main as m
import json
from unittest.mock import patch

client = TestClient(m.app)

mock_sources = [
    {'url':'https://example.com/quantum1','title':'Quantum Computing Overview','domain':'example.com','content':'Quantum computing uses qubits that can be in superposition states. This allows exponential speedup for certain calculations. Companies like IBM and Google are leading the development.'},
]

with patch.object(m, 'search_all_sources', return_value=mock_sources), \
     patch.object(m, 'call_llm', return_value='Verified analysis of quantum computing fundamentals with citations [^1].'):
    res = client.post('/api/v1/research/', json={'query':'What is quantum computing?','depth':1,'complexity':1,'paragraphs':1,'subQuestions':1})
    
    for line in res.text.splitlines():
        line = line.strip()
        if line.startswith('data: '):
            try:
                event = json.loads(line[6:])
                if event.get('node') == 'end':
                    report = event.get('report','')
                    print('FINAL REPORT LENGTH: ' + str(len(report)))
                    print('SOURCE NOTES IN FINAL REPORT: ' + str(report.count('Source Notes')))
                    break
            except:
                pass
print('DONE')
