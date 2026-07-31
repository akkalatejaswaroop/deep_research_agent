import requests, json, time, sys

t0 = time.time()
resp = requests.post('http://127.0.0.1:11434/api/generate',
    json={'model':'qwen2.5:3b','prompt':'Write one sentence about AI.','stream':False,'options':{'num_predict':50}},
    timeout=30)
t1 = time.time()
data = resp.json()
sys.stdout.write(f'Ollama response time: {(t1-t0)*1000:.0f}ms\n')
sys.stdout.write(f'Response: ' + data.get('response','')[:200] + '\n')
