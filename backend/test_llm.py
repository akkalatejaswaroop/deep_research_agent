import os
os.environ["SIMULATED_MODE"] = "false"
from main import generate_section, search_all_sources

sources = search_all_sources("transformer architecture AI", 3)
print(f"Found {len(sources)} sources")

result = generate_section(
    query="What is transformer architecture in AI?",
    sub_question="How does the self-attention mechanism work in transformers?",
    sources=sources,
    para_count=1,
    section_idx=0,
    total_sections=1
)
print(f"Result ({len(result)} chars):")
print(result[:500])
