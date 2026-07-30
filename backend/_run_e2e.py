import sys, time, os, subprocess
sys.path.insert(0, __file__.replace("\\_run_e2e.py", ""))
sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

t0 = time.perf_counter()

os.environ["SIMULATED_MODE"] = "false"
os.environ["PREFER_LLM"] = "true"
os.environ["REPORT_MODEL"] = "deepseek-coder:1.3b"

# Pre-load model by sending a warmup request via curl
import json
body = json.dumps({"model": "deepseek-coder:1.3b", "prompt": "warmup", "stream": False})
subprocess.run(["curl.exe", "-s", "--max-time", "60", "-d", body,
    "http://127.0.0.1:11434/api/generate"], capture_output=True, timeout=65)

import main as m
print(f"Import: {time.perf_counter()-t0:.1f}s", flush=True)

m.PREFER_LLM = "true"
m.REPORT_MODEL = "phi3:mini"

query = "Explain the greenhouse effect and its impact on global warming"
t_start = time.perf_counter()

import threading

def on_track_status(tid, text, status):
    print(f"  [TRACK {tid}] {text}: {status}", flush=True)

result = m.build_report_autonomously(
    query, depth=2, complexity=1, target_paragraphs=3, target_sub_questions=3,
    on_thought=lambda msg: print(f"  [T] {msg}", flush=True),
    on_track_status=on_track_status,
)
t_elapsed = time.perf_counter() - t_start
report_text = result.get("report", "")
scores = result.get("scores", {})
print(f"\n{'='*60}", flush=True)
print(f"Total time: {t_elapsed:.1f}s", flush=True)
print(f"Report length: {len(report_text)} chars", flush=True)
print(f"Scores: {scores}", flush=True)
print(f"{'='*60}", flush=True)
print(report_text[:2000], flush=True)
