import sys
import traceback

with open("debug_import_steps.log", "w") as f:
    def log(msg):
        f.write(msg + "\n")
        f.flush()
        print(msg)

    log("Starting step-by-step import debug...")
    
    try:
        log("Importing json...")
        import json
        log("Importing re...")
        import re
        log("Importing hashlib...")
        import hashlib
        log("Importing sys...")
        import sys
        log("Importing os...")
        import os
        log("Importing contextvars...")
        import contextvars
        log("Importing ThreadPoolExecutor...")
        from concurrent.futures import ThreadPoolExecutor, as_completed
        log("Importing typing...")
        from typing import Dict, List, Any
        log("Importing langgraph...")
        from langgraph.graph import StateGraph, END
        log("Importing langgraph.types...")
        from langgraph.types import interrupt
        log("Importing ChatOllama...")
        from langchain_ollama import ChatOllama
        log("Importing ChatPromptTemplate...")
        from langchain_core.prompts import ChatPromptTemplate
        log("Importing RunnableConfig...")
        from langchain_core.runnables import RunnableConfig
        log("Importing redis...")
        import redis
        log("Importing OllamaEmbeddings...")
        from langchain_ollama import OllamaEmbeddings
        log("Importing RecursiveCharacterTextSplitter...")
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        log("Importing BeautifulSoup...")
        from bs4 import BeautifulSoup
        log("Importing requests...")
        import requests
        log("Importing urllib3...")
        import urllib3
        
        log("All packages imported successfully. Now running graph.py module-level instantiations...")
        
        log("embeddings = OllamaEmbeddings(model='nomic-embed-text')")
        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        
        log("All instantiations done successfully!")
    except Exception as e:
        log("EXCEPTION: " + str(e))
        traceback.print_exc(file=f)
    log("Debug script finished.")
