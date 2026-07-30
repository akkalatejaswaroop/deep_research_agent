import os

with open("agents/graph.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Add RunnableConfig and emit_thought
if "from langchain_core.runnables import RunnableConfig" not in code:
    code = code.replace("from langchain_core.prompts import ChatPromptTemplate", "from langchain_core.prompts import ChatPromptTemplate\nfrom langchain_core.runnables import RunnableConfig\nimport redis")
    
    emit_thought_code = """
redis_client = None
try:
    redis_client = redis.Redis.from_url(os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"))
except:
    pass

def emit_thought(config: RunnableConfig, message: str):
    if not redis_client: return
    if config and "configurable" in config and "thread_id" in config["configurable"]:
        session_id = config["configurable"]["thread_id"]
        try:
            redis_client.publish(f"research_stream_{session_id}", json.dumps({"type": "thought", "message": message}))
        except:
            pass
"""
    code = code.replace("# ---------------------------------------------------------------------------", emit_thought_code + "\n# ---------------------------------------------------------------------------", 1)

# 2. Update search_and_scrape
code = code.replace("def search_and_scrape(query: str, max_results: int = 5, max_scrape: int = 3) -> Dict[str, str]:", "def search_and_scrape(query: str, config: RunnableConfig, max_results: int = 5, max_scrape: int = 3) -> Dict[str, str]:\n    emit_thought(config, f\"Searching web for: {query}\")")
scrape_block_old = """                page = requests.get(url, timeout=8, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                })
                soup = BeautifulSoup(page.content, "html.parser")
                for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "form", "iframe"]):
                    tag.decompose()
                texts = []
                for tag in soup.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote", "td", "th", "pre", "code"]):
                    t = tag.get_text(strip=True)
                    if len(t) > 20:
                        texts.append(t)
                content = "\\n".join(texts[:150])
                if len(content) > 500:
                    results[url] = content[:8000]"""

scrape_block_new = """                emit_thought(config, f"Reading: {url}")
                page = requests.get(f"https://r.jina.ai/{url}", timeout=15)
                content = page.text
                if len(content) > 500:
                    results[url] = content[:8000]"""
code = code.replace(scrape_block_old, scrape_block_new)

# 3. Update nodes signatures and add emit_thought
code = code.replace("def planner_node(state: AgentState) -> Dict:", "def planner_node(state: AgentState, config: RunnableConfig) -> Dict:\n    emit_thought(config, \"Analyzing query and planning sub-questions...\")")
code = code.replace("def searcher_node(state: AgentState) -> Dict:", "def searcher_node(state: AgentState, config: RunnableConfig) -> Dict:\n    emit_thought(config, \"Running parallel web searches...\")")
code = code.replace("executor.submit(search_and_scrape, q): q", "executor.submit(search_and_scrape, q, config): q")
code = code.replace("def filter_node(state: AgentState) -> Dict:", "def filter_node(state: AgentState, config: RunnableConfig) -> Dict:\n    emit_thought(config, \"Filtering and ranking scraped content...\")")
code = code.replace("def synthesis_node(state: AgentState) -> Dict:", "def synthesis_node(state: AgentState, config: RunnableConfig) -> Dict:\n    emit_thought(config, \"Synthesizing findings from relevant sources...\")")
code = code.replace("def gap_detector_node(state: AgentState) -> Dict:", "def gap_detector_node(state: AgentState, config: RunnableConfig) -> Dict:\n    emit_thought(config, \"Detecting knowledge gaps...\")")
code = code.replace("def citation_mapper_node(state: AgentState) -> Dict:", "def citation_mapper_node(state: AgentState, config: RunnableConfig) -> Dict:\n    emit_thought(config, \"Mapping and formatting citations...\")")
code = code.replace("def report_node(state: AgentState) -> Dict:", "def report_node(state: AgentState, config: RunnableConfig) -> Dict:\n    emit_thought(config, \"Generating final comprehensive report...\")")
code = code.replace("def evaluator_node(state: AgentState) -> Dict:", "def evaluator_node(state: AgentState, config: RunnableConfig) -> Dict:\n    emit_thought(config, \"Extracting lessons learned...\")")

# 4. Update citation syntax
code = code.replace("Cite every fact with [N] notation", "Cite every fact with [^N] notation")
code = code.replace("correct [N] citation marker", "correct [^N] citation marker")
code = code.replace("inline [N] citations", "inline [^N] citations")

# Update references formatting in citation_mapper
ref_old = """    ref_lines = ["## References"]
    for i, url in enumerate(source_urls):
        ref_lines.append(f"[{i+1}] {url}")"""
ref_new = """    ref_lines = ["\\n---\\n## References"]
    for i, url in enumerate(source_urls):
        ref_lines.append(f"[^{i+1}]: {url}")"""
code = code.replace(ref_old, ref_new)

# Update references formatting in report_node
ref_old2 = """        ref_lines = ["## References"]
        for i, url in enumerate(source_urls):
            ref_lines.append(f"[{i+1}] {url}")"""
ref_new2 = """        ref_lines = ["\\n---\\n## References"]
        for i, url in enumerate(source_urls):
            ref_lines.append(f"[^{i+1}]: {url}")"""
code = code.replace(ref_old2, ref_new2)

with open("agents/graph.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Patch applied successfully.")
