import requests
import json

url = 'http://localhost:8001/api/v1/research/'
payload = {'query': 'Quantum Computing advances in 2024', 'depth': 1, 'complexity': 1}

print('Starting research...')
try:
    with requests.post(url, json=payload, stream=True) as r:
        for line in r.iter_lines():
            if line:
                data = line.decode('utf-8')
                if data.startswith('data: '):
                    content = data[6:]
                    try:
                        js = json.loads(content)
                        if 'node' in js and js['node'] == 'end':
                            print('\n\n--- FINAL REPORT ---\n')
                            print(js.get('report', 'No report found.'))
                            with open('test_report.md', 'w', encoding='utf-8') as f:
                                f.write(js.get('report', ''))
                        elif 'type' in js and js['type'] == 'thought':
                            print(f"[THOUGHT] {js.get('message')}")
                        else:
                            print(f"[STATE UPDATE] {js.get('node', js)}")
                    except Exception as e:
                        print(f'Error parsing JSON: {content}')
except Exception as e:
    print(f'Request failed: {e}')
