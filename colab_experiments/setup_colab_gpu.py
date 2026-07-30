# Deep Research Agent - Colab T4 GPU Acceleration Server
# -------------------------------------------------------------
# Instructions:
# 1. Open Google Colab (https://colab.research.google.com)
# 2. Set Runtime -> Change runtime type -> Hardware accelerator -> T4 GPU
# 3. Paste and run this script in a code cell
# 4. Copy the output HTTPS tunnel URL into your local backend/.env file

import subprocess
import time
import re

print("Installing Ollama and Cloudflare Tunnel on Colab GPU...")
!curl -fsSL https://ollama.com/install.sh | sh
!wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
!dpkg -i cloudflared-linux-amd64.deb

print("Starting Ollama GPU service...")
subprocess.Popen(["ollama", "serve"])
time.sleep(5)

print("Pulling Qwen 2.5 (7B) to Colab T4 GPU VRAM...")
!ollama pull qwen2.5:7b

print("Establishing Cloudflare Tunnel to expose Colab GPU endpoint...")
tunnel = subprocess.Popen(
    ["cloudflared", "tunnel", "--url", "http://localhost:11434"],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
)

time.sleep(8)
log_output = tunnel.stderr.read() + tunnel.stdout.read()
urls = re.findall(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', log_output)

if urls:
    api_url = f"{urls[0]}/v1"
    print("\n" + "="*65)
    print("🚀 COLAB T4 GPU SERVER IS READY!")
    print("Add these lines to your d:\\deep_research_agent\\backend\\.env file:")
    print("="*65)
    print(f"API_LLM_BASE_URL={api_url}")
    print("API_LLM_API_KEY=colab-gpu-secret")
    print("PLANNER_MODEL=qwen2.5:7b")
    print("SYNTHESIS_MODEL=qwen2.5:7b")
    print("REPORT_MODEL=qwen2.5:7b")
    print("FILTER_MODEL=qwen2.5:7b")
    print("GAP_MODEL=qwen2.5:7b")
    print("EVALUATOR_MODEL=qwen2.5:7b")
    print("="*65)
else:
    print("Tunnel generation delayed. Please re-run this cell.")
