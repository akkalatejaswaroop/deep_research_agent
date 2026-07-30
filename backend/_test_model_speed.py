"""Test which Ollama model is fastest on this machine."""
import sys, time, subprocess, json

for model in ["phi3:mini", "deepseek-coder:1.3b", "qwen2.5:3b"]:
    # Short prompt
    body = json.dumps({"model": model, "prompt": "What is 2+2?", "stream": False})
    t0 = time.perf_counter()
    r = subprocess.run(["curl.exe", "-s", "--max-time", "120", "-d", body,
        f"http://127.0.0.1:11434/api/generate"], capture_output=True, text=True, timeout=125)
    t = time.perf_counter() - t0
    rc = r.returncode
    print(f"{model:25s} short={t:.1f}s rc={rc}", flush=True)

    # Long prompt (simulate synthesis with 5000 chars)
    long_prompt = "What is climate change? " * 200  # ~5000 chars
    body = json.dumps({"model": model, "prompt": long_prompt, "stream": False})
    t0 = time.perf_counter()
    r = subprocess.run(["curl.exe", "-s", "--max-time", "120", "-d", body,
        f"http://127.0.0.1:11434/api/generate"], capture_output=True, text=True, timeout=125)
    t = time.perf_counter() - t0
    rc = r.returncode
    resp = json.loads(r.stdout).get("response","")[:100] if rc == 0 else "N/A"
    print(f"{model:25s} long ={t:.1f}s rc={rc} resp={resp}", flush=True)
