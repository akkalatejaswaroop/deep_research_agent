"""Test ChatOllama directly to see if it hangs or respects timeout."""
import sys, time, os
sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None
sys.path.insert(0, r"D:\deep_research_agent\backend")

t0 = time.perf_counter()
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

llm = ChatOllama(model="phi3:mini", temperature=0.2, timeout=120)
chain = ChatPromptTemplate.from_messages([("human", "What is 2+2? Answer briefly.")]) | llm

t1 = time.perf_counter()
print(f"Setup: {t1-t0:.1f}s", flush=True)

try:
    response = chain.invoke({})
    t2 = time.perf_counter()
    print(f"Response time: {t2-t1:.1f}s", flush=True)
    print(f"Content: {response.content[:200]}", flush=True)
except Exception as e:
    t2 = time.perf_counter()
    print(f"Error after {t2-t1:.1f}s: {e}", flush=True)
