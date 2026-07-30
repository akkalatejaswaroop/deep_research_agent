import time
from langchain_ollama import OllamaEmbeddings
embeddings = OllamaEmbeddings(model="nomic-embed-text")
print("Embedding query...")
start = time.time()
q_vec = embeddings.embed_query("What is AI?")
print(f"Finished embedding in {time.time() - start} seconds")
print(f"Vector size: {len(q_vec)}")
