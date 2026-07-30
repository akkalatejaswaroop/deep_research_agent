import urllib.request
import json
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

body = json.dumps({
    'query': 'What are the latest advances in quantum computing?',
    'depth': 1,
    'complexity': 1,
    'paragraphs': 2,
    'subQuestions': 3
}).encode()

req = urllib.request.Request(
    'http://127.0.0.1:8000/api/v1/research/',
    data=body,
    headers={'Content-Type': 'application/json'}
)

try:
    resp = urllib.request.urlopen(req, timeout=120)
    report = None
    for line in resp.read().decode('utf-8').split('\n'):
        if line.startswith('data: '):
            try:
                data = json.loads(line[6:])
                if 'node' in data and isinstance(data.get('node'), str):
                    if data['node'] not in ('', 'n8n'):
                        sys.stdout.write('[' + data['node'] + ']\n')
                        sys.stdout.flush()
                elif 'report' in data:
                    report = data['report']
            except:
                pass

    if report:
        sys.stdout.write('\nREPORT OK: ' + str(len(report)) + ' chars\n')
        sys.stdout.write(report[:1500] + '\n')
    else:
        sys.stdout.write('\nERROR: No report in response\n')
    sys.stdout.flush()
except Exception as e:
    sys.stdout.write('ERROR: ' + str(e) + '\n')
    sys.stdout.flush()
