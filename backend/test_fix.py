"""Quick test to verify ChatPromptTemplate escaping fix."""
from langchain_core.prompts import ChatPromptTemplate

# Simulate the fixed generate_sub_questions prompt
prompt = (
    'Given the research query: "test query"\n\n'
    "Generate exactly 5 specific, distinct sub-questions that together comprehensively answer the main query.\n\n"
    "Return ONLY valid JSON:\n"
    '{{"sub_questions": ["Q1", "Q2", ...]}}'
)

system = "You are a research planning agent."

chain = ChatPromptTemplate.from_messages([
    ("system", system),
    ("human", prompt),
])
result = chain.invoke({})
print("Template formatting OK")
print(result.messages[1].content[:200])
