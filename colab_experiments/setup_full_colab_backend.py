# Deep Research Agent - Non-Blocking Fast Colab Setup
# ====================================================================
# INSTRUCTIONS:
# 1. Click STOP (Interrupt execution) on your running Colab cell if it is stuck.
# 2. Replace the cell code with this updated script and click RUN.
# 3. This script will finish in under 2 minutes!

import subprocess
import time
import os
import sys
import re
import shutil

print("🚀 Step 1/4: Installing zstd, Ollama, & Cloudflare...")
!apt-get update -qq && apt-get install -y -qq zstd curl pciutils > /dev/null 2>&1
!curl -fsSL https://ollama.com/install.sh | sh > /dev/null 2>&1
!wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
!dpkg -i cloudflared-linux-amd64.deb > /dev/null 2>&1

ollama_bin = shutil.which("ollama") or "/usr/local/bin/ollama"
print(f"Ollama binary location: {ollama_bin}")

print("\n📦 Step 2/4: Preparing Backend Codebase & Packages...")
os.makedirs("/content/deep_research_agent/backend", exist_ok=True)
%cd /content/deep_research_agent/backend

# Create minimal FastAPI backend if main.py does not exist
if not os.path.exists("main.py"):
    with open("main.py", "w") as f:
        f.write('''import os, requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Deep Research Agent API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class ResearchRequest(BaseModel):
    query: str

@app.get("/")
def read_root():
    return {"status": "ok", "service": "Deep Research Agent Backend"}

@app.get("/api/health")
def health():
    return {"status": "healthy", "gpu": "T4"}

@app.post("/api/research")
def research(req: ResearchRequest):
    ollama_url = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    prompt = f"Perform deep research on: {req.query}. Provide a structured report."
    try:
        r = requests.post(f"{ollama_url}/api/generate", json={"model": "qwen2.5:7b", "prompt": prompt, "stream": False}, timeout=120)
        resp = r.json().get("response", "")
        return {"query": req.query, "report": resp, "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
''')

!pip install -q "fastapi==0.109.2" uvicorn langgraph langchain langchain-community langchain-ollama langchain-core beautifulsoup4 langchain-text-splitters numpy pydantic python-dotenv duckduckgo-search "requests==2.32.4" urllib3

print("\n🤖 Step 3/4: Starting Ollama GPU & Downloading Qwen 2.5 (7B)...")
!nohup ollama serve > /tmp/ollama.log 2>&1 &
time.sleep(4)

# Download Qwen 2.5 7B model onto Colab GPU
!ollama pull qwen2.5:7b

print("\n⚡ Step 4/4: Exposing Backend via Cloudflare Tunnel...")
!nohup uvicorn main:app --host 0.0.0.0 --port 8000 > /tmp/uvicorn.log 2>&1 &
time.sleep(3)

# Log tunnel output directly to a file to prevent subprocess deadlock
!nohup cloudflared tunnel --url http://localhost:8000 > /tmp/tunnel.log 2>&1 &
time.sleep(6)

# Read log file cleanly without blocking
urls = []
if os.path.exists("/tmp/tunnel.log"):
    with open("/tmp/tunnel.log", "r") as f:
        urls = re.findall(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', f.read())

if urls:
    live_api_url = urls[0]
    print("\n" + "="*70)
    print("🎉 SUCCESS! YOUR FULL BACKEND IS LIVE ON COLAB T4 GPU!")
    print("="*70)
    print("Copy and paste this line into your local frontend/.env.local file:\n")
    print(f"NEXT_PUBLIC_API_URL={live_api_url}")
    print("\n" + "="*70)
    print("Now run 'npm run dev' inside your local frontend directory!")
else:
    time.sleep(4)
    if os.path.exists("/tmp/tunnel.log"):
        with open("/tmp/tunnel.log", "r") as f:
            urls = re.findall(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', f.read())
    if urls:
        print(f"\nNEXT_PUBLIC_API_URL={urls[0]}")
    else:
        print("\nTunnel is starting. Run: !cat /tmp/tunnel.log to see your URL.")
