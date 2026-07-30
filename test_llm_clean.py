import time
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

llm = ChatOllama(model="phi3:mini", temperature=0.1)
prompt = ChatPromptTemplate.from_messages([
    ("system", "Break this question into 2 sub-questions. Output JSON: {{\"sub_questions\":[\"q1\",\"q2\"],\"search_queries\":[[\"sq1\"],[\"sq2\"]]}}"),
    ("human", "{query}")
])

chain = prompt | llm
print("Invoking chain...")
start = time.time()
res = chain.invoke({"query": "What is AI?"})
print("Result:", res.content)
print("Time taken:", time.time() - start)
