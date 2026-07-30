"""Check what real services are available."""
import requests, os, shutil, sys

print("=== Environment Check ===", flush=True)

# Ollama
try:
    r = requests.get("http://127.0.0.1:11434/api/tags", timeout=3)
    models = [m["name"] for m in r.json().get("models", [])]
    print(f"OLLAMA: running - models: {models}", flush=True)
except Exception as e:
    print(f"OLLAMA: {e}", flush=True)

ollama_bin = shutil.which("ollama")
print(f"ollama binary: {ollama_bin}", flush=True)

# API keys
for key in ["TAVILY_API_KEY", "SERPAPI_API_KEY", "API_LLM_API_KEY", "API_LLM_BASE_URL", "REPORT_MODEL"]:
    val = os.getenv(key, "")
    if val:
        print(f"{key}: SET (len={len(val)})", flush=True)
    else:
        print(f"{key}: NOT SET", flush=True)

print(f"PREFER_LLM: {os.getenv('PREFER_LLM', 'NOT SET')}", flush=True)

# Check network to Wikipedia
try:
    r = requests.get(
        "https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch=greenhouse+effect&format=json",
        headers={"User-Agent": "DeepResearchAgent/1.0"},
        timeout=5
    )
    print(f"WIKIPEDIA: reachable (status={r.status_code})", flush=True)
except Exception as e:
    print(f"WIKIPEDIA: {e}", flush=True)

# Check if external LLM endpoint reachable
api_base = os.getenv("API_LLM_BASE_URL", "")
if api_base:
    try:
        r = requests.get(api_base.rstrip("/") + "/models", timeout=5)
        print(f"EXTERNAL LLM: reachable (status={r.status_code})", flush=True)
    except Exception as e:
        print(f"EXTERNAL LLM: {e}", flush=True)

print("=== Done ===", flush=True)
