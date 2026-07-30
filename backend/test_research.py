import requests, json, sys

def main():
    resp = requests.post(
        'http://localhost:8001/api/v1/research/',
        json={'query': 'What is the speed of light?', 'depth': 1, 'complexity': 1},
        stream=True,
        timeout=600
    )

    session_id = resp.headers.get('X-Session-Id', '')
    print(f'Session ID: {session_id}')

    report = ''
    sources = []
    metrics = None

    for line in resp.iter_lines(decode_unicode=True):
        if line and line.startswith('data: '):
            data_str = line[6:]
            try:
                data = json.loads(data_str)
                msg_type = data.get('type', '')
                node = data.get('node', '')
                if msg_type == 'thought':
                    print(f'[Thought] {data.get("message", "")[:120]}')
                elif node == 'end':
                    report = data.get('report', '')
                    print(f'[Report received] {len(report)} chars')
                elif node == 'metrics':
                    metrics = data.get('data')
                    print(f'[Metrics received]')
                elif node:
                    print(f'[Node] {node}')
            except json.JSONDecodeError:
                pass

    print()
    print('=== REPORT ===')
    print(report[:3000] if report else 'No report generated')
    print()

    if metrics:
        print('=== METRICS ===')
        metrics_out = json.dumps(metrics, indent=2)
        print(metrics_out[:1500])

    with open('research_output.json', 'w') as f:
        json.dump({
            'session_id': session_id,
            'report': report,
            'metrics': metrics
        }, f, indent=2)

    print('\nSaved to research_output.json')

if __name__ == '__main__':
    main()
