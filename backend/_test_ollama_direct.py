"""Test Ollama directly to diagnose delays."""
import sys, os, time
os.environ["PREFER_LLM"] = "true"
sys.path.insert(0, r"D:\deep_research_agent\backend")

t0 = time.perf_counter()
from langchain_ollama import ChatOllama
t1 = time.perf_counter()
print(f"Import ChatOllama: {t1-t0:.2f}s", flush=True)

import requests
r = requests.get("http://127.0.0.1:11434/api/tags", timeout=5)
models = [m["name"] for m in r.json().get("models", [])]
print(f"Ollama models ({len(models)}): {models}", flush=True)

for model in ["qwen2.5:3b", "phi3:mini", "llama3.2:latest"]:
    if model not in models and model.split(":")[0] not in [m.split(":")[0] for m in models]:
        print(f"  {model}: not found, skipping", flush=True)
        continue
    t2 = time.perf_counter()
    try:
        llm = ChatOllama(model=model, temperature=0.2, timeout=30)
        from langchain_core.prompts import ChatPromptTemplate
        chain = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant. Answer in one sentence."),
            ("human", "What is the greenhouse effect?")
        ]) | llm
        response = chain.invoke({})
        t3 = time.perf_counter()
        print(f"  {model}: {t3-t2:.1f}s -> {response.content[:100]}", flush=True)
    except Exception as e:
        print(f"  {model}: ERROR - {e}", flush=True)
