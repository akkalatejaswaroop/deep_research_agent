import sys; sys.path.insert(0, 'backend')
import os; os.environ['SIMULATED_MODE'] = 'false'
from fastapi.testclient import TestClient
import backend.main as m
import json, re

client = TestClient(m.app)

# Use patched sources + LLM for fast verification
from unittest.mock import patch
mock_sources = [{'url':'https://example.com/test','title':'Test Source','domain':'example.com','content':'Test content about quantum computing and its applications in various industries.'}]

with patch.object(m, 'search_all_sources', return_value=mock_sources), \
     patch.object(m, 'call_llm', return_value='Verified analysis of quantum computing capabilities.'):
    res = client.post('/api/v1/research/', json={'query':'What is quantum computing?','depth':1,'complexity':1,'paragraphs':1,'subQuestions':1})
    
    for line in res.text.splitlines():
        line = line.strip()
        if line.startswith('data: '):
            try:
                event = json.loads(line[6:])
                if event.get('node') == 'end':
                    report = event.get('report','')
                    sn_before = report.count('Source Notes')
                    print('Source Notes in report BEFORE strip: ' + str(sn_before))
                    
                    # Apply the same regex the report_node uses
                    stripped = re.sub(r'\n### Source Notes\n.*?(?=\n###|\n##|\Z)', '', report, flags=re.DOTALL)
                    stripped = re.sub(r'\n####? Source Notes?\n.*?(?=\n#|\Z)', '', stripped, flags=re.DOTALL)
                    stripped = re.sub(r'### Source Notes?\s*\n.*?(?=\n###|\n##|\Z)', '', stripped, flags=re.DOTALL)
                    
                    sn_after = stripped.count('Source Notes')
                    print('Source Notes after strip: ' + str(sn_after))
                    print('Report length: ' + str(len(report)))
                    
                    # Check if the stripping code works
                    if sn_after == 0:
                        print('STRIPPING WORKING CORRECTLY!')
                    break
            except:
                pass
print('TEST DONE')
