import sys; sys.path.insert(0, 'backend')
import os; os.environ['SIMULATED_MODE'] = 'false'
from fastapi.testclient import TestClient
import backend.main as m
import json, re

client = TestClient(m.app)

res = client.post('/api/v1/research/', json={'query':'What is quantum computing?','depth':1,'complexity':1,'paragraphs':1,'subQuestions':2})

for line in res.text.splitlines():
    line = line.strip()
    if line.startswith('data: '):
        try:
            event = json.loads(line[6:])
            if event.get('node') == 'end':
                report = event.get('report','')
                print('Report chars: ' + str(len(report)))
                
                # Check actual characters at Source Notes
                idx = report.find('### Source Notes')
                print('First ### Source Notes at offset ' + str(idx))
                print('Context (repr): ' + repr(report[idx-20:idx+120]))
                
                # Check if it uses actual newlines or literal \n
                surrounding = report[idx-20:idx+120]
                print('Has actual newlines: ' + str('\n' in surrounding))
                print('Has literal backslash-n: ' + str('\\n' in surrounding))
                
                # Test the exact regex on the report
                normalized = report.replace('\r\n', '\n').replace('\r', '\n')
                pattern = r'#{1,4}\s*Source Notes?\s*\n[\s\S]*?(?=\n#{1,4}|\Z)'
                result = re.sub(pattern, '', normalized)
                remaining = result.count('Source Notes')
                print('\nAfter regex strip: ' + str(remaining) + ' Source Notes remaining')
                
                # If still remaining, try more aggressive patterns
                if remaining > 0:
                    # Try removing everything from ### Source Notes to next ###
                    result2 = re.sub(r'### Source Notes[\s\S]*?(?=\n#)', '', normalized)
                    remaining2 = result2.count('Source Notes')
                    print('After aggressive strip (1): ' + str(remaining2))
                    
                    result3 = re.sub(r'#{1,4}\s*Source Notes[\s\S]*?(?=\n#{1,4})', '', normalized)
                    remaining3 = result3.count('Source Notes')
                    print('After aggressive strip (2): ' + str(remaining3))
                    
                    # Simplest possible match
                    result4 = normalized.replace('### Source Notes', '### REMOVED')
                    remaining4 = result4.count('Source Notes')
                    print('After simple replace: ' + str(remaining4))
                break
        except:
            pass
print('DONE')
